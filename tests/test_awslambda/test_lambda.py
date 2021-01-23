from __future__ import unicode_literals

import base64
import uuid
import botocore.client
import boto3
import hashlib
import io
import json
import time
import zipfile
import sure  # noqa

from freezegun import freeze_time
from moto import (
    mock_dynamodb2,
    mock_lambda,
    mock_iam,
    mock_s3,
    mock_ec2,
    mock_sns,
    mock_logs,
    settings,
    mock_sqs,
)
from moto.sts.models import ACCOUNT_ID
from moto.core.exceptions import RESTError
import pytest
from botocore.exceptions import ClientError

_lambda_region = "us-west-2"
boto3.setup_default_session(region_name=_lambda_region)


def _process_lambda(func_str):
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
    zip_file.writestr("lambda_function.py", func_str)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


def get_test_zip_file1():
    pfunc = """
def lambda_handler(event, context):
    print("custom log event")
    return event
"""
    return _process_lambda(pfunc)


def get_test_zip_file2():
    func_str = """
import boto3

def lambda_handler(event, context):
    ec2 = boto3.resource('ec2', region_name='us-west-2', endpoint_url='http://{base_url}')

    volume_id = event.get('volume_id')
    vol = ec2.Volume(volume_id)

    return {{'id': vol.id, 'state': vol.state, 'size': vol.size}}
""".format(
        base_url="motoserver:5000"
        if settings.TEST_SERVER_MODE
        else "ec2.us-west-2.amazonaws.com"
    )
    return _process_lambda(func_str)


def get_test_zip_file3():
    pfunc = """
def lambda_handler(event, context):
    print("Nr_of_records("+str(len(event['Records']))+")")
    print("get_test_zip_file3 success")
    return event
"""
    return _process_lambda(pfunc)


def get_test_zip_file4():
    pfunc = """
def lambda_handler(event, context):
    raise Exception('I failed!')
"""
    return _process_lambda(pfunc)


@pytest.mark.parametrize("region", ["us-west-2", "cn-northwest-1"])
@mock_lambda
def test_lambda_regions(region):
    client = boto3.client("lambda", region_name=region)
    resp = client.list_functions()
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_lambda
def test_list_functions():
    conn = boto3.client("lambda", _lambda_region)
    result = conn.list_functions()
    result["Functions"].should.have.length_of(0)


@pytest.mark.network
@mock_lambda
def test_invoke_requestresponse_function():
    conn = boto3.client("lambda", _lambda_region)
    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    in_data = {"msg": "So long and thanks for all the fish"}
    success_result = conn.invoke(
        FunctionName="testFunction",
        InvocationType="RequestResponse",
        Payload=json.dumps(in_data),
        LogType="Tail",
    )

    if "FunctionError" in success_result:
        assert False, success_result["Payload"].read().decode("utf-8")

    success_result["StatusCode"].should.equal(200)
    logs = base64.b64decode(success_result["LogResult"]).decode("utf-8")

    logs.should.contain("START RequestId:")
    logs.should.contain("custom log event")
    logs.should.contain("END RequestId:")

    payload = success_result["Payload"].read().decode("utf-8")
    json.loads(payload).should.equal(in_data)

    # Logs should not be returned by default, only when the LogType-param is supplied
    success_result = conn.invoke(
        FunctionName="testFunction",
        InvocationType="RequestResponse",
        Payload=json.dumps(in_data),
    )

    success_result["StatusCode"].should.equal(200)
    assert "LogResult" not in success_result


@pytest.mark.network
@mock_lambda
def test_invoke_requestresponse_function_with_arn():
    from moto.awslambda.models import ACCOUNT_ID

    conn = boto3.client("lambda", "us-west-2")
    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    in_data = {"msg": "So long and thanks for all the fish"}
    success_result = conn.invoke(
        FunctionName="arn:aws:lambda:us-west-2:{}:function:testFunction".format(
            ACCOUNT_ID
        ),
        InvocationType="RequestResponse",
        Payload=json.dumps(in_data),
    )

    success_result["StatusCode"].should.equal(200)

    payload = success_result["Payload"].read().decode("utf-8")
    json.loads(payload).should.equal(in_data)


@pytest.mark.network
@mock_lambda
def test_invoke_event_function():
    conn = boto3.client("lambda", _lambda_region)
    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    conn.invoke.when.called_with(
        FunctionName="notAFunction", InvocationType="Event", Payload="{}"
    ).should.throw(botocore.client.ClientError)

    in_data = {"msg": "So long and thanks for all the fish"}
    success_result = conn.invoke(
        FunctionName="testFunction", InvocationType="Event", Payload=json.dumps(in_data)
    )
    success_result["StatusCode"].should.equal(202)
    json.loads(success_result["Payload"].read().decode("utf-8")).should.equal(in_data)


@pytest.mark.network
@mock_lambda
def test_invoke_dryrun_function():
    conn = boto3.client("lambda", _lambda_region)
    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1(),},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    conn.invoke.when.called_with(
        FunctionName="notAFunction", InvocationType="Event", Payload="{}"
    ).should.throw(botocore.client.ClientError)

    in_data = {"msg": "So long and thanks for all the fish"}
    success_result = conn.invoke(
        FunctionName="testFunction",
        InvocationType="DryRun",
        Payload=json.dumps(in_data),
    )
    success_result["StatusCode"].should.equal(204)


if settings.TEST_SERVER_MODE:

    @mock_ec2
    @mock_lambda
    def test_invoke_function_get_ec2_volume():
        conn = boto3.resource("ec2", _lambda_region)
        vol = conn.create_volume(Size=99, AvailabilityZone=_lambda_region)
        vol = conn.Volume(vol.id)

        conn = boto3.client("lambda", _lambda_region)
        conn.create_function(
            FunctionName="testFunction",
            Runtime="python3.7",
            Role=get_role_name(),
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": get_test_zip_file2()},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
        )

        in_data = {"volume_id": vol.id}
        result = conn.invoke(
            FunctionName="testFunction",
            InvocationType="RequestResponse",
            Payload=json.dumps(in_data),
        )
        result["StatusCode"].should.equal(200)
        actual_payload = json.loads(result["Payload"].read().decode("utf-8"))
        expected_payload = {"id": vol.id, "state": vol.state, "size": vol.size}
        actual_payload.should.equal(expected_payload)


@pytest.mark.network
@mock_logs
@mock_sns
@mock_ec2
@mock_lambda
def test_invoke_function_from_sns():
    logs_conn = boto3.client("logs", region_name=_lambda_region)
    sns_conn = boto3.client("sns", region_name=_lambda_region)
    sns_conn.create_topic(Name="some-topic")
    topics_json = sns_conn.list_topics()
    topics = topics_json["Topics"]
    topic_arn = topics[0]["TopicArn"]

    conn = boto3.client("lambda", _lambda_region)
    result = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    sns_conn.subscribe(
        TopicArn=topic_arn, Protocol="lambda", Endpoint=result["FunctionArn"]
    )

    result = sns_conn.publish(TopicArn=topic_arn, Message=json.dumps({}))

    start = time.time()
    while (time.time() - start) < 30:
        result = logs_conn.describe_log_streams(logGroupName="/aws/lambda/testFunction")
        log_streams = result.get("logStreams")
        if not log_streams:
            time.sleep(1)
            continue

        assert len(log_streams) == 1
        result = logs_conn.get_log_events(
            logGroupName="/aws/lambda/testFunction",
            logStreamName=log_streams[0]["logStreamName"],
        )
        for event in result.get("events"):
            if event["message"] == "get_test_zip_file3 success":
                return

        time.sleep(1)

    assert False, "Test Failed"


@mock_lambda
def test_create_based_on_s3_with_missing_bucket():
    conn = boto3.client("lambda", _lambda_region)

    conn.create_function.when.called_with(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "this-bucket-does-not-exist", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        VpcConfig={"SecurityGroupIds": ["sg-123abc"], "SubnetIds": ["subnet-123abc"]},
    ).should.throw(botocore.client.ClientError)


@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_create_function_from_aws_bucket():
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )
    zip_content = get_test_zip_file2()

    s3_conn.put_object(Bucket="test-bucket", Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    result = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        VpcConfig={"SecurityGroupIds": ["sg-123abc"], "SubnetIds": ["subnet-123abc"]},
    )
    # this is hard to match against, so remove it
    result["ResponseMetadata"].pop("HTTPHeaders", None)
    # Botocore inserts retry attempts not seen in Python27
    result["ResponseMetadata"].pop("RetryAttempts", None)
    result.pop("LastModified")
    result.should.equal(
        {
            "FunctionName": "testFunction",
            "FunctionArn": "arn:aws:lambda:{}:{}:function:testFunction".format(
                _lambda_region, ACCOUNT_ID
            ),
            "Runtime": "python2.7",
            "Role": result["Role"],
            "Handler": "lambda_function.lambda_handler",
            "CodeSha256": hashlib.sha256(zip_content).hexdigest(),
            "CodeSize": len(zip_content),
            "Description": "test lambda function",
            "Timeout": 3,
            "MemorySize": 128,
            "Version": "1",
            "VpcConfig": {
                "SecurityGroupIds": ["sg-123abc"],
                "SubnetIds": ["subnet-123abc"],
                "VpcId": "vpc-123abc",
            },
            "ResponseMetadata": {"HTTPStatusCode": 201},
            "State": "Active",
            "Layers": [],
        }
    )


@mock_lambda
@freeze_time("2015-01-01 00:00:00")
def test_create_function_from_zipfile():
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    result = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    # this is hard to match against, so remove it
    result["ResponseMetadata"].pop("HTTPHeaders", None)
    # Botocore inserts retry attempts not seen in Python27
    result["ResponseMetadata"].pop("RetryAttempts", None)
    result.pop("LastModified")

    result.should.equal(
        {
            "FunctionName": "testFunction",
            "FunctionArn": "arn:aws:lambda:{}:{}:function:testFunction".format(
                _lambda_region, ACCOUNT_ID
            ),
            "Runtime": "python2.7",
            "Role": result["Role"],
            "Handler": "lambda_function.lambda_handler",
            "CodeSize": len(zip_content),
            "Description": "test lambda function",
            "Timeout": 3,
            "MemorySize": 128,
            "CodeSha256": hashlib.sha256(zip_content).hexdigest(),
            "Version": "1",
            "VpcConfig": {"SecurityGroupIds": [], "SubnetIds": []},
            "ResponseMetadata": {"HTTPStatusCode": 201},
            "State": "Active",
            "Layers": [],
        }
    )


@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_get_function():
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket="test-bucket", Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Environment={"Variables": {"test_variable": "test_value"}},
    )

    result = conn.get_function(FunctionName="testFunction")
    # this is hard to match against, so remove it
    result["ResponseMetadata"].pop("HTTPHeaders", None)
    # Botocore inserts retry attempts not seen in Python27
    result["ResponseMetadata"].pop("RetryAttempts", None)
    result["Configuration"].pop("LastModified")

    result["Code"]["Location"].should.equal(
        "s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com/test.zip".format(_lambda_region)
    )
    result["Code"]["RepositoryType"].should.equal("S3")

    result["Configuration"]["CodeSha256"].should.equal(
        hashlib.sha256(zip_content).hexdigest()
    )
    result["Configuration"]["CodeSize"].should.equal(len(zip_content))
    result["Configuration"]["Description"].should.equal("test lambda function")
    result["Configuration"].should.contain("FunctionArn")
    result["Configuration"]["FunctionName"].should.equal("testFunction")
    result["Configuration"]["Handler"].should.equal("lambda_function.lambda_handler")
    result["Configuration"]["MemorySize"].should.equal(128)
    result["Configuration"]["Role"].should.equal(get_role_name())
    result["Configuration"]["Runtime"].should.equal("python2.7")
    result["Configuration"]["Timeout"].should.equal(3)
    result["Configuration"]["Version"].should.equal("$LATEST")
    result["Configuration"].should.contain("VpcConfig")
    result["Configuration"].should.contain("Environment")
    result["Configuration"]["Environment"].should.contain("Variables")
    result["Configuration"]["Environment"]["Variables"].should.equal(
        {"test_variable": "test_value"}
    )

    # Test get function with qualifier
    result = conn.get_function(FunctionName="testFunction", Qualifier="$LATEST")
    result["Configuration"]["Version"].should.equal("$LATEST")
    result["Configuration"]["FunctionArn"].should.equal(
        "arn:aws:lambda:us-west-2:{}:function:testFunction:$LATEST".format(ACCOUNT_ID)
    )

    # Test get function when can't find function name
    with pytest.raises(conn.exceptions.ResourceNotFoundException):
        conn.get_function(FunctionName="junk", Qualifier="$LATEST")


@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_get_function_configuration():
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket="test-bucket", Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Environment={"Variables": {"test_variable": "test_value"}},
    )

    result = conn.get_function_configuration(FunctionName="testFunction")

    result["CodeSha256"].should.equal(hashlib.sha256(zip_content).hexdigest())
    result["CodeSize"].should.equal(len(zip_content))
    result["Description"].should.equal("test lambda function")
    result.should.contain("FunctionArn")
    result["FunctionName"].should.equal("testFunction")
    result["Handler"].should.equal("lambda_function.lambda_handler")
    result["MemorySize"].should.equal(128)
    result["Role"].should.equal(get_role_name())
    result["Runtime"].should.equal("python2.7")
    result["Timeout"].should.equal(3)
    result["Version"].should.equal("$LATEST")
    result.should.contain("VpcConfig")
    result.should.contain("Environment")
    result["Environment"].should.contain("Variables")
    result["Environment"]["Variables"].should.equal({"test_variable": "test_value"})

    # Test get function with qualifier
    result = conn.get_function_configuration(
        FunctionName="testFunction", Qualifier="$LATEST"
    )
    result["Version"].should.equal("$LATEST")
    result["FunctionArn"].should.equal(
        "arn:aws:lambda:{}:{}:function:testFunction:$LATEST".format(
            _lambda_region, ACCOUNT_ID
        )
    )

    # Test get function when can't find function name
    with pytest.raises(conn.exceptions.ResourceNotFoundException):
        conn.get_function_configuration(FunctionName="junk", Qualifier="$LATEST")


@mock_lambda
@mock_s3
def test_get_function_by_arn():
    bucket_name = "test-bucket"
    s3_conn = boto3.client("s3", "us-east-1")
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", "us-east-1")

    fnc = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    result = conn.get_function(FunctionName=fnc["FunctionArn"])
    result["Configuration"]["FunctionName"].should.equal("testFunction")


@mock_lambda
@mock_s3
def test_delete_function():
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket="test-bucket", Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    success_result = conn.delete_function(FunctionName="testFunction")
    # this is hard to match against, so remove it
    success_result["ResponseMetadata"].pop("HTTPHeaders", None)
    # Botocore inserts retry attempts not seen in Python27
    success_result["ResponseMetadata"].pop("RetryAttempts", None)

    success_result.should.equal({"ResponseMetadata": {"HTTPStatusCode": 204}})

    function_list = conn.list_functions()
    function_list["Functions"].should.have.length_of(0)


@mock_lambda
@mock_s3
def test_delete_function_by_arn():
    bucket_name = "test-bucket"
    s3_conn = boto3.client("s3", "us-east-1")
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", "us-east-1")

    fnc = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    conn.delete_function(FunctionName=fnc["FunctionArn"])
    function_list = conn.list_functions()
    function_list["Functions"].should.have.length_of(0)


@mock_lambda
def test_delete_unknown_function():
    conn = boto3.client("lambda", _lambda_region)
    conn.delete_function.when.called_with(
        FunctionName="testFunctionThatDoesntExist"
    ).should.throw(botocore.client.ClientError)


@mock_lambda
@mock_s3
def test_publish():
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket="test-bucket", Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=False,
    )

    function_list = conn.list_functions()
    function_list["Functions"].should.have.length_of(1)
    latest_arn = function_list["Functions"][0]["FunctionArn"]

    res = conn.publish_version(FunctionName="testFunction")
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 201

    function_list = conn.list_functions()
    function_list["Functions"].should.have.length_of(2)

    # #SetComprehension ;-)
    published_arn = list(
        {f["FunctionArn"] for f in function_list["Functions"]} - {latest_arn}
    )[0]
    published_arn.should.contain("testFunction:1")

    conn.delete_function(FunctionName="testFunction", Qualifier="1")

    function_list = conn.list_functions()
    function_list["Functions"].should.have.length_of(1)
    function_list["Functions"][0]["FunctionArn"].should.contain("testFunction")


@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_list_create_list_get_delete_list():
    """
    test `list -> create -> list -> get -> delete -> list` integration

    """
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket="test-bucket", Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    conn.list_functions()["Functions"].should.have.length_of(0)

    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    expected_function_result = {
        "Code": {
            "Location": "s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com/test.zip".format(
                _lambda_region
            ),
            "RepositoryType": "S3",
        },
        "Configuration": {
            "CodeSha256": hashlib.sha256(zip_content).hexdigest(),
            "CodeSize": len(zip_content),
            "Description": "test lambda function",
            "FunctionArn": "arn:aws:lambda:{}:{}:function:testFunction".format(
                _lambda_region, ACCOUNT_ID
            ),
            "FunctionName": "testFunction",
            "Handler": "lambda_function.lambda_handler",
            "MemorySize": 128,
            "Role": get_role_name(),
            "Runtime": "python2.7",
            "Timeout": 3,
            "Version": "$LATEST",
            "VpcConfig": {"SecurityGroupIds": [], "SubnetIds": []},
            "State": "Active",
            "Layers": [],
        },
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }
    func = conn.list_functions()["Functions"][0]
    func.pop("LastModified")
    func.should.equal(expected_function_result["Configuration"])

    func = conn.get_function(FunctionName="testFunction")
    # this is hard to match against, so remove it
    func["ResponseMetadata"].pop("HTTPHeaders", None)
    # Botocore inserts retry attempts not seen in Python27
    func["ResponseMetadata"].pop("RetryAttempts", None)
    func["Configuration"].pop("LastModified")

    func.should.equal(expected_function_result)
    conn.delete_function(FunctionName="testFunction")

    conn.list_functions()["Functions"].should.have.length_of(0)


@pytest.mark.network
@mock_lambda
def test_invoke_lambda_error():
    lambda_fx = """
def lambda_handler(event, context):
    raise Exception('failsauce')
    """
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
    zip_file.writestr("lambda_function.py", lambda_fx)
    zip_file.close()
    zip_output.seek(0)

    client = boto3.client("lambda", region_name="us-east-1")
    client.create_function(
        FunctionName="test-lambda-fx",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Code={"ZipFile": zip_output.read()},
    )

    result = client.invoke(
        FunctionName="test-lambda-fx", InvocationType="RequestResponse", LogType="Tail"
    )

    assert "FunctionError" in result
    assert result["FunctionError"] == "Handled"


@mock_lambda
@mock_s3
def test_tags():
    """
    test list_tags -> tag_resource -> list_tags -> tag_resource -> list_tags -> untag_resource -> list_tags integration
    """
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket="test-bucket", Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    function = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    # List tags when there are none
    conn.list_tags(Resource=function["FunctionArn"])["Tags"].should.equal(dict())

    # List tags when there is one
    conn.tag_resource(Resource=function["FunctionArn"], Tags=dict(spam="eggs"))[
        "ResponseMetadata"
    ]["HTTPStatusCode"].should.equal(200)
    conn.list_tags(Resource=function["FunctionArn"])["Tags"].should.equal(
        dict(spam="eggs")
    )

    # List tags when another has been added
    conn.tag_resource(Resource=function["FunctionArn"], Tags=dict(foo="bar"))[
        "ResponseMetadata"
    ]["HTTPStatusCode"].should.equal(200)
    conn.list_tags(Resource=function["FunctionArn"])["Tags"].should.equal(
        dict(spam="eggs", foo="bar")
    )

    # Untag resource
    conn.untag_resource(Resource=function["FunctionArn"], TagKeys=["spam", "trolls"])[
        "ResponseMetadata"
    ]["HTTPStatusCode"].should.equal(204)
    conn.list_tags(Resource=function["FunctionArn"])["Tags"].should.equal(
        dict(foo="bar")
    )

    # Untag a tag that does not exist (no error and no change)
    conn.untag_resource(Resource=function["FunctionArn"], TagKeys=["spam"])[
        "ResponseMetadata"
    ]["HTTPStatusCode"].should.equal(204)


@mock_lambda
def test_tags_not_found():
    """
    Test list_tags and tag_resource when the lambda with the given arn does not exist
    """
    conn = boto3.client("lambda", _lambda_region)
    conn.list_tags.when.called_with(
        Resource="arn:aws:lambda:{}:function:not-found".format(ACCOUNT_ID)
    ).should.throw(botocore.client.ClientError)

    conn.tag_resource.when.called_with(
        Resource="arn:aws:lambda:{}:function:not-found".format(ACCOUNT_ID),
        Tags=dict(spam="eggs"),
    ).should.throw(botocore.client.ClientError)

    conn.untag_resource.when.called_with(
        Resource="arn:aws:lambda:{}:function:not-found".format(ACCOUNT_ID),
        TagKeys=["spam"],
    ).should.throw(botocore.client.ClientError)


@pytest.mark.network
@mock_lambda
def test_invoke_async_function():
    conn = boto3.client("lambda", _lambda_region)
    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    success_result = conn.invoke_async(
        FunctionName="testFunction", InvokeArgs=json.dumps({"test": "event"})
    )

    success_result["Status"].should.equal(202)


@mock_lambda
@freeze_time("2015-01-01 00:00:00")
def test_get_function_created_with_zipfile():
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    result = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.get_function(FunctionName="testFunction")
    response["Configuration"].pop("LastModified")

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    assert len(response["Code"]) == 2
    assert response["Code"]["RepositoryType"] == "S3"
    assert response["Code"]["Location"].startswith(
        "s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com".format(_lambda_region)
    )
    response["Configuration"].should.equal(
        {
            "CodeSha256": hashlib.sha256(zip_content).hexdigest(),
            "CodeSize": len(zip_content),
            "Description": "test lambda function",
            "FunctionArn": "arn:aws:lambda:{}:{}:function:testFunction".format(
                _lambda_region, ACCOUNT_ID
            ),
            "FunctionName": "testFunction",
            "Handler": "lambda_function.handler",
            "MemorySize": 128,
            "Role": get_role_name(),
            "Runtime": "python2.7",
            "Timeout": 3,
            "Version": "$LATEST",
            "VpcConfig": {"SecurityGroupIds": [], "SubnetIds": []},
            "State": "Active",
            "Layers": [],
        }
    )


@mock_lambda
def test_add_function_permission():
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.add_permission(
        FunctionName="testFunction",
        StatementId="1",
        Action="lambda:InvokeFunction",
        Principal="432143214321",
        SourceArn="arn:aws:lambda:us-west-2:account-id:function:helloworld",
        SourceAccount="123412341234",
        EventSourceToken="blah",
        Qualifier="2",
    )
    assert "Statement" in response
    res = json.loads(response["Statement"])
    assert res["Action"] == "lambda:InvokeFunction"


@mock_lambda
def test_get_function_policy():
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.add_permission(
        FunctionName="testFunction",
        StatementId="1",
        Action="lambda:InvokeFunction",
        Principal="432143214321",
        SourceArn="arn:aws:lambda:us-west-2:account-id:function:helloworld",
        SourceAccount="123412341234",
        EventSourceToken="blah",
        Qualifier="2",
    )

    response = conn.get_policy(FunctionName="testFunction")

    assert "Policy" in response
    res = json.loads(response["Policy"])
    assert res["Statement"][0]["Action"] == "lambda:InvokeFunction"


@mock_lambda
@mock_s3
def test_list_versions_by_function():
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket="test-bucket", Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    res = conn.publish_version(FunctionName="testFunction")
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 201
    versions = conn.list_versions_by_function(FunctionName="testFunction")
    assert len(versions["Versions"]) == 3
    assert versions["Versions"][0][
        "FunctionArn"
    ] == "arn:aws:lambda:us-west-2:{}:function:testFunction:$LATEST".format(ACCOUNT_ID)
    assert versions["Versions"][1][
        "FunctionArn"
    ] == "arn:aws:lambda:us-west-2:{}:function:testFunction:1".format(ACCOUNT_ID)
    assert versions["Versions"][2][
        "FunctionArn"
    ] == "arn:aws:lambda:us-west-2:{}:function:testFunction:2".format(ACCOUNT_ID)

    conn.create_function(
        FunctionName="testFunction_2",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=False,
    )
    versions = conn.list_versions_by_function(FunctionName="testFunction_2")
    assert len(versions["Versions"]) == 1
    assert versions["Versions"][0][
        "FunctionArn"
    ] == "arn:aws:lambda:us-west-2:{}:function:testFunction_2:$LATEST".format(
        ACCOUNT_ID
    )


@mock_lambda
@mock_s3
def test_create_function_with_already_exists():
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket="test-bucket", Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    assert response["FunctionName"] == "testFunction"


@mock_lambda
@mock_s3
def test_list_versions_by_function_for_nonexistent_function():
    conn = boto3.client("lambda", _lambda_region)
    versions = conn.list_versions_by_function(FunctionName="testFunction")

    assert len(versions["Versions"]) == 0


@mock_logs
@mock_lambda
@mock_sqs
def test_create_event_source_mapping():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-sqs-queue1")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.create_event_source_mapping(
        EventSourceArn=queue.attributes["QueueArn"], FunctionName=func["FunctionArn"]
    )

    assert response["EventSourceArn"] == queue.attributes["QueueArn"]
    assert response["FunctionArn"] == func["FunctionArn"]
    assert response["State"] == "Enabled"


@pytest.mark.network
@mock_logs
@mock_lambda
@mock_sqs
def test_invoke_function_from_sqs():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-sqs-queue1")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.create_event_source_mapping(
        EventSourceArn=queue.attributes["QueueArn"], FunctionName=func["FunctionArn"]
    )

    assert response["EventSourceArn"] == queue.attributes["QueueArn"]
    assert response["State"] == "Enabled"

    sqs_client = boto3.client("sqs", region_name="us-east-1")
    sqs_client.send_message(QueueUrl=queue.url, MessageBody="test")

    expected_msg = "get_test_zip_file3 success"
    log_group = "/aws/lambda/testFunction"
    msg_showed_up, all_logs = wait_for_log_msg(expected_msg, log_group)

    assert msg_showed_up, (
        expected_msg
        + " was not found after sending an SQS message. All logs: "
        + all_logs
    )


@pytest.mark.network
@mock_logs
@mock_lambda
@mock_dynamodb2
def test_invoke_function_from_dynamodb_put():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    table_name = "table_with_stream"
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
        Description="test lambda function executed after a DynamoDB table is updated",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.create_event_source_mapping(
        EventSourceArn=table["TableDescription"]["LatestStreamArn"],
        FunctionName=func["FunctionArn"],
    )

    assert response["EventSourceArn"] == table["TableDescription"]["LatestStreamArn"]
    assert response["State"] == "Enabled"

    dynamodb.put_item(TableName=table_name, Item={"id": {"S": "item 1"}})

    expected_msg = "get_test_zip_file3 success"
    log_group = "/aws/lambda/testFunction"
    msg_showed_up, all_logs = wait_for_log_msg(expected_msg, log_group)

    assert msg_showed_up, (
        expected_msg + " was not found after a DDB insert. All logs: " + all_logs
    )


@pytest.mark.network
@mock_logs
@mock_lambda
@mock_dynamodb2
def test_invoke_function_from_dynamodb_update():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    table_name = "table_with_stream"
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
        Description="test lambda function executed after a DynamoDB table is updated",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    conn.create_event_source_mapping(
        EventSourceArn=table["TableDescription"]["LatestStreamArn"],
        FunctionName=func["FunctionArn"],
    )

    dynamodb.put_item(TableName=table_name, Item={"id": {"S": "item 1"}})
    log_group = "/aws/lambda/testFunction"
    expected_msg = "get_test_zip_file3 success"
    msg_showed_up, all_logs = wait_for_log_msg(expected_msg, log_group)
    assert "Nr_of_records(1)" in all_logs, "Only one item should be inserted"

    dynamodb.update_item(
        TableName=table_name,
        Key={"id": {"S": "item 1"}},
        UpdateExpression="set #attr = :val",
        ExpressionAttributeNames={"#attr": "new_attr"},
        ExpressionAttributeValues={":val": {"S": "new_val"}},
    )
    msg_showed_up, all_logs = wait_for_log_msg(expected_msg, log_group)

    assert msg_showed_up, (
        expected_msg + " was not found after updating DDB. All logs: " + str(all_logs)
    )
    assert "Nr_of_records(1)" in all_logs, "Only one item should be updated"
    assert (
        "Nr_of_records(2)" not in all_logs
    ), "The inserted item should not show up again"


def wait_for_log_msg(expected_msg, log_group):
    logs_conn = boto3.client("logs", region_name="us-east-1")
    received_messages = []
    start = time.time()
    while (time.time() - start) < 10:
        result = logs_conn.describe_log_streams(logGroupName=log_group)
        log_streams = result.get("logStreams")
        if not log_streams:
            time.sleep(1)
            continue

        for log_stream in log_streams:
            result = logs_conn.get_log_events(
                logGroupName=log_group, logStreamName=log_stream["logStreamName"],
            )
            received_messages.extend(
                [event["message"] for event in result.get("events")]
            )
        if expected_msg in received_messages:
            return True, received_messages
        time.sleep(1)
    return False, received_messages


@pytest.mark.network
@mock_logs
@mock_lambda
@mock_sqs
def test_invoke_function_from_sqs_exception():
    logs_conn = boto3.client("logs", region_name="us-east-1")
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-sqs-queue1")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file4()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.create_event_source_mapping(
        EventSourceArn=queue.attributes["QueueArn"], FunctionName=func["FunctionArn"]
    )

    assert response["EventSourceArn"] == queue.attributes["QueueArn"]
    assert response["State"] == "Enabled"

    entries = []
    for i in range(3):
        body = {"uuid": str(uuid.uuid4()), "test": "test_{}".format(i)}
        entry = {"Id": str(i), "MessageBody": json.dumps(body)}
        entries.append(entry)

    queue.send_messages(Entries=entries)

    start = time.time()
    while (time.time() - start) < 30:
        result = logs_conn.describe_log_streams(logGroupName="/aws/lambda/testFunction")
        log_streams = result.get("logStreams")
        if not log_streams:
            time.sleep(1)
            continue
        assert len(log_streams) >= 1

        result = logs_conn.get_log_events(
            logGroupName="/aws/lambda/testFunction",
            logStreamName=log_streams[0]["logStreamName"],
        )
        for event in result.get("events"):
            if "I failed!" in event["message"]:
                messages = queue.receive_messages(MaxNumberOfMessages=10)
                # Verify messages are still visible and unprocessed
                assert len(messages) == 3
                return
        time.sleep(1)

    assert False, "Test Failed"


@mock_logs
@mock_lambda
@mock_sqs
def test_list_event_source_mappings():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-sqs-queue1")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    response = conn.create_event_source_mapping(
        EventSourceArn=queue.attributes["QueueArn"], FunctionName=func["FunctionArn"]
    )
    mappings = conn.list_event_source_mappings(EventSourceArn="123")
    assert len(mappings["EventSourceMappings"]) == 0

    mappings = conn.list_event_source_mappings(
        EventSourceArn=queue.attributes["QueueArn"]
    )
    assert len(mappings["EventSourceMappings"]) == 1
    assert mappings["EventSourceMappings"][0]["UUID"] == response["UUID"]
    assert mappings["EventSourceMappings"][0]["FunctionArn"] == func["FunctionArn"]


@mock_lambda
@mock_sqs
def test_get_event_source_mapping():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-sqs-queue1")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    response = conn.create_event_source_mapping(
        EventSourceArn=queue.attributes["QueueArn"], FunctionName=func["FunctionArn"]
    )
    mapping = conn.get_event_source_mapping(UUID=response["UUID"])
    assert mapping["UUID"] == response["UUID"]
    assert mapping["FunctionArn"] == func["FunctionArn"]

    conn.get_event_source_mapping.when.called_with(UUID="1").should.throw(
        botocore.client.ClientError
    )


@mock_lambda
@mock_sqs
def test_update_event_source_mapping():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-sqs-queue1")

    conn = boto3.client("lambda", region_name="us-east-1")
    func1 = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    func2 = conn.create_function(
        FunctionName="testFunction2",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    response = conn.create_event_source_mapping(
        EventSourceArn=queue.attributes["QueueArn"], FunctionName=func1["FunctionArn"]
    )
    assert response["FunctionArn"] == func1["FunctionArn"]
    assert response["BatchSize"] == 10
    assert response["State"] == "Enabled"

    mapping = conn.update_event_source_mapping(
        UUID=response["UUID"], Enabled=False, BatchSize=2, FunctionName="testFunction2"
    )
    assert mapping["UUID"] == response["UUID"]
    assert mapping["FunctionArn"] == func2["FunctionArn"]
    assert mapping["State"] == "Disabled"
    assert mapping["BatchSize"] == 2


@mock_lambda
@mock_sqs
def test_delete_event_source_mapping():
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-sqs-queue1")

    conn = boto3.client("lambda", region_name="us-east-1")
    func1 = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    response = conn.create_event_source_mapping(
        EventSourceArn=queue.attributes["QueueArn"], FunctionName=func1["FunctionArn"]
    )
    assert response["FunctionArn"] == func1["FunctionArn"]
    assert response["BatchSize"] == 10
    assert response["State"] == "Enabled"

    response = conn.delete_event_source_mapping(UUID=response["UUID"])

    assert response["State"] == "Deleting"
    conn.get_event_source_mapping.when.called_with(UUID=response["UUID"]).should.throw(
        botocore.client.ClientError
    )


@mock_lambda
@mock_s3
def test_update_configuration():
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket="test-bucket", Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    fxn = conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Environment={"Variables": {"test_old_environment": "test_old_value"}},
    )

    assert fxn["Description"] == "test lambda function"
    assert fxn["Handler"] == "lambda_function.lambda_handler"
    assert fxn["MemorySize"] == 128
    assert fxn["Runtime"] == "python2.7"
    assert fxn["Timeout"] == 3

    updated_config = conn.update_function_configuration(
        FunctionName="testFunction",
        Description="updated test lambda function",
        Handler="lambda_function.new_lambda_handler",
        Runtime="python3.6",
        Timeout=7,
        VpcConfig={"SecurityGroupIds": ["sg-123abc"], "SubnetIds": ["subnet-123abc"]},
        Environment={"Variables": {"test_environment": "test_value"}},
    )

    assert updated_config["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert updated_config["Description"] == "updated test lambda function"
    assert updated_config["Handler"] == "lambda_function.new_lambda_handler"
    assert updated_config["MemorySize"] == 128
    assert updated_config["Runtime"] == "python3.6"
    assert updated_config["Timeout"] == 7
    assert updated_config["Environment"]["Variables"] == {
        "test_environment": "test_value"
    }
    assert updated_config["VpcConfig"] == {
        "SecurityGroupIds": ["sg-123abc"],
        "SubnetIds": ["subnet-123abc"],
        "VpcId": "vpc-123abc",
    }


@mock_lambda
def test_update_function_zip():
    conn = boto3.client("lambda", _lambda_region)

    zip_content_one = get_test_zip_file1()

    fxn = conn.create_function(
        FunctionName="testFunctionZip",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zip_content_one},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    zip_content_two = get_test_zip_file2()

    fxn_updated = conn.update_function_code(
        FunctionName="testFunctionZip", ZipFile=zip_content_two, Publish=True
    )

    response = conn.get_function(FunctionName="testFunctionZip", Qualifier="2")
    response["Configuration"].pop("LastModified")

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    assert len(response["Code"]) == 2
    assert response["Code"]["RepositoryType"] == "S3"
    assert response["Code"]["Location"].startswith(
        "s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com".format(_lambda_region)
    )
    response["Configuration"].should.equal(
        {
            "CodeSha256": hashlib.sha256(zip_content_two).hexdigest(),
            "CodeSize": len(zip_content_two),
            "Description": "test lambda function",
            "FunctionArn": "arn:aws:lambda:{}:{}:function:testFunctionZip:2".format(
                _lambda_region, ACCOUNT_ID
            ),
            "FunctionName": "testFunctionZip",
            "Handler": "lambda_function.lambda_handler",
            "MemorySize": 128,
            "Role": fxn["Role"],
            "Runtime": "python2.7",
            "Timeout": 3,
            "Version": "2",
            "VpcConfig": {"SecurityGroupIds": [], "SubnetIds": []},
            "State": "Active",
            "Layers": [],
        }
    )


@mock_lambda
@mock_s3
def test_update_function_s3():
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket="test-bucket", Key="test.zip", Body=zip_content)

    conn = boto3.client("lambda", _lambda_region)

    fxn = conn.create_function(
        FunctionName="testFunctionS3",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    zip_content_two = get_test_zip_file2()
    s3_conn.put_object(Bucket="test-bucket", Key="test2.zip", Body=zip_content_two)

    fxn_updated = conn.update_function_code(
        FunctionName="testFunctionS3",
        S3Bucket="test-bucket",
        S3Key="test2.zip",
        Publish=True,
    )

    response = conn.get_function(FunctionName="testFunctionS3", Qualifier="2")
    response["Configuration"].pop("LastModified")

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    assert len(response["Code"]) == 2
    assert response["Code"]["RepositoryType"] == "S3"
    assert response["Code"]["Location"].startswith(
        "s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com".format(_lambda_region)
    )
    response["Configuration"].should.equal(
        {
            "CodeSha256": hashlib.sha256(zip_content_two).hexdigest(),
            "CodeSize": len(zip_content_two),
            "Description": "test lambda function",
            "FunctionArn": "arn:aws:lambda:{}:{}:function:testFunctionS3:2".format(
                _lambda_region, ACCOUNT_ID
            ),
            "FunctionName": "testFunctionS3",
            "Handler": "lambda_function.lambda_handler",
            "MemorySize": 128,
            "Role": fxn["Role"],
            "Runtime": "python2.7",
            "Timeout": 3,
            "Version": "2",
            "VpcConfig": {"SecurityGroupIds": [], "SubnetIds": []},
            "State": "Active",
            "Layers": [],
        }
    )


@mock_lambda
def test_create_function_with_invalid_arn():
    err = create_invalid_lambda("test-iam-role")
    err.value.response["Error"]["Message"].should.equal(
        r"1 validation error detected: Value 'test-iam-role' at 'role' failed to satisfy constraint: Member must satisfy regular expression pattern: arn:(aws[a-zA-Z-]*)?:iam::(\d{12}):role/?[a-zA-Z_0-9+=,.@\-_/]+"
    )


@mock_lambda
def test_create_function_with_arn_from_different_account():
    err = create_invalid_lambda("arn:aws:iam::000000000000:role/example_role")
    err.value.response["Error"]["Message"].should.equal(
        "Cross-account pass role is not allowed."
    )


@mock_lambda
def test_create_function_with_unknown_arn():
    err = create_invalid_lambda(
        "arn:aws:iam::" + str(ACCOUNT_ID) + ":role/service-role/unknown_role"
    )
    err.value.response["Error"]["Message"].should.equal(
        "The role defined for the function cannot be assumed by Lambda."
    )


@mock_lambda
def test_remove_function_permission():
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    conn.add_permission(
        FunctionName="testFunction",
        StatementId="1",
        Action="lambda:InvokeFunction",
        Principal="432143214321",
        SourceArn="arn:aws:lambda:us-west-2:account-id:function:helloworld",
        SourceAccount="123412341234",
        EventSourceToken="blah",
        Qualifier="2",
    )

    remove = conn.remove_permission(
        FunctionName="testFunction", StatementId="1", Qualifier="2",
    )
    remove["ResponseMetadata"]["HTTPStatusCode"].should.equal(204)
    policy = conn.get_policy(FunctionName="testFunction", Qualifier="2")["Policy"]
    policy = json.loads(policy)
    policy["Statement"].should.equal([])


@mock_lambda
def test_put_function_concurrency():
    expected_concurrency = 15
    function_name = "test"

    conn = boto3.client("lambda", _lambda_region)
    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.8",
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    result = conn.put_function_concurrency(
        FunctionName=function_name, ReservedConcurrentExecutions=expected_concurrency
    )

    result["ReservedConcurrentExecutions"].should.equal(expected_concurrency)


@mock_lambda
def test_delete_function_concurrency():
    function_name = "test"

    conn = boto3.client("lambda", _lambda_region)
    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.8",
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    conn.put_function_concurrency(
        FunctionName=function_name, ReservedConcurrentExecutions=15
    )

    conn.delete_function_concurrency(FunctionName=function_name)
    result = conn.get_function(FunctionName=function_name)

    result.doesnt.have.key("Concurrency")


@mock_lambda
def test_get_function_concurrency():
    expected_concurrency = 15
    function_name = "test"

    conn = boto3.client("lambda", _lambda_region)
    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.8",
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    conn.put_function_concurrency(
        FunctionName=function_name, ReservedConcurrentExecutions=expected_concurrency
    )

    result = conn.get_function_concurrency(FunctionName=function_name)

    result["ReservedConcurrentExecutions"].should.equal(expected_concurrency)


@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_get_lambda_layers():
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket="test-bucket", Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    with pytest.raises((RESTError, ClientError)):
        conn.publish_layer_version(
            LayerName="testLayer",
            Content={},
            CompatibleRuntimes=["python3.6"],
            LicenseInfo="MIT",
        )
    conn.publish_layer_version(
        LayerName="testLayer",
        Content={"ZipFile": get_test_zip_file1()},
        CompatibleRuntimes=["python3.6"],
        LicenseInfo="MIT",
    )
    conn.publish_layer_version(
        LayerName="testLayer",
        Content={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        CompatibleRuntimes=["python3.6"],
        LicenseInfo="MIT",
    )

    result = conn.list_layer_versions(LayerName="testLayer")

    for version in result["LayerVersions"]:
        version.pop("CreatedDate")
    result["LayerVersions"].sort(key=lambda x: x["Version"])
    expected_arn = "arn:aws:lambda:{0}:{1}:layer:testLayer:".format(
        _lambda_region, ACCOUNT_ID
    )
    result["LayerVersions"].should.equal(
        [
            {
                "Version": 1,
                "LayerVersionArn": expected_arn + "1",
                "CompatibleRuntimes": ["python3.6"],
                "Description": "",
                "LicenseInfo": "MIT",
            },
            {
                "Version": 2,
                "LayerVersionArn": expected_arn + "2",
                "CompatibleRuntimes": ["python3.6"],
                "Description": "",
                "LicenseInfo": "MIT",
            },
        ]
    )

    conn.create_function(
        FunctionName="testFunction",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Environment={"Variables": {"test_variable": "test_value"}},
        Layers=[(expected_arn + "1")],
    )

    result = conn.get_function_configuration(FunctionName="testFunction")
    result["Layers"].should.equal(
        [{"Arn": (expected_arn + "1"), "CodeSize": len(zip_content)}]
    )
    result = conn.update_function_configuration(
        FunctionName="testFunction", Layers=[(expected_arn + "2")]
    )
    result["Layers"].should.equal(
        [{"Arn": (expected_arn + "2"), "CodeSize": len(zip_content)}]
    )

    # Test get layer versions for non existant layer
    result = conn.list_layer_versions(LayerName="testLayer2")
    result["LayerVersions"].should.equal([])

    # Test create function with non existant layer version
    with pytest.raises((ValueError, ClientError)):
        conn.create_function(
            FunctionName="testFunction",
            Runtime="python2.7",
            Role=get_role_name(),
            Handler="lambda_function.lambda_handler",
            Code={"S3Bucket": "test-bucket", "S3Key": "test.zip"},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
            Environment={"Variables": {"test_variable": "test_value"}},
            Layers=[(expected_arn + "3")],
        )


def create_invalid_lambda(role):
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    with pytest.raises(ClientError) as err:
        conn.create_function(
            FunctionName="testFunction",
            Runtime="python2.7",
            Role=role,
            Handler="lambda_function.handler",
            Code={"ZipFile": zip_content},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
        )
    return err


def get_role_name():
    with mock_iam():
        iam = boto3.client("iam", region_name=_lambda_region)
        try:
            return iam.get_role(RoleName="my-role")["Role"]["Arn"]
        except ClientError:
            return iam.create_role(
                RoleName="my-role",
                AssumeRolePolicyDocument="some policy",
                Path="/my-path/",
            )["Role"]["Arn"]
