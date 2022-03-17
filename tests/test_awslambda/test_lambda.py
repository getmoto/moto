import base64
import botocore.client
import boto3
import hashlib
import sure  # noqa # pylint: disable=unused-import
import pytest

from botocore.exceptions import ClientError
from freezegun import freeze_time
from moto import mock_lambda, mock_s3
from moto.core.models import ACCOUNT_ID
from uuid import uuid4
from .utilities import (
    get_role_name,
    get_test_zip_file1,
    get_test_zip_file2,
    create_invalid_lambda,
)

_lambda_region = "us-west-2"
boto3.setup_default_session(region_name=_lambda_region)


@pytest.mark.parametrize("region", ["us-west-2", "cn-northwest-1"])
@mock_lambda
def test_lambda_regions(region):
    client = boto3.client("lambda", region_name=region)
    resp = client.list_functions()
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_lambda
def test_list_functions():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    initial_list = conn.list_functions()["Functions"]
    initial_names = [f["FunctionName"] for f in initial_list]
    initial_names.shouldnt.contain(function_name)

    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )
    names = [f["FunctionName"] for f in conn.list_functions()["Functions"]]
    names.should.contain(function_name)

    conn.publish_version(FunctionName=function_name, Description="v2")
    func_list = conn.list_functions()["Functions"]
    our_functions = [f for f in func_list if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(1)

    # FunctionVersion=ALL means we should get a list of all versions
    full_list = conn.list_functions(FunctionVersion="ALL")["Functions"]
    our_functions = [f for f in full_list if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(2)

    v1 = [f for f in our_functions if f["Version"] == "1"][0]
    v1["Description"].should.equal("v2")
    v1["FunctionArn"].should.equal(
        "arn:aws:lambda:{}:{}:function:{}:1".format(
            _lambda_region, ACCOUNT_ID, function_name
        )
    )

    latest = [f for f in our_functions if f["Version"] == "$LATEST"][0]
    latest["Description"].should.equal("")
    latest["FunctionArn"].should.equal(
        "arn:aws:lambda:{}:{}:function:{}:$LATEST".format(
            _lambda_region, ACCOUNT_ID, function_name
        )
    )


@mock_lambda
def test_create_based_on_s3_with_missing_bucket():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function.when.called_with(
        FunctionName=function_name,
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
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )
    zip_content = get_test_zip_file2()

    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    result = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        PackageType="ZIP",
        Publish=True,
        VpcConfig={"SecurityGroupIds": ["sg-123abc"], "SubnetIds": ["subnet-123abc"]},
    )

    result.should.have.key("FunctionName").equals(function_name)
    result.should.have.key("FunctionArn").equals(
        "arn:aws:lambda:{}:{}:function:{}".format(
            _lambda_region, ACCOUNT_ID, function_name
        )
    )
    result.should.have.key("Runtime").equals("python2.7")
    result.should.have.key("Handler").equals("lambda_function.lambda_handler")
    result.should.have.key("CodeSha256").equals(
        base64.b64encode(hashlib.sha256(zip_content).digest()).decode("utf-8")
    )
    result.should.have.key("State").equals("Active")


@mock_lambda
@freeze_time("2015-01-01 00:00:00")
def test_create_function_from_zipfile():
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    result = conn.create_function(
        FunctionName=function_name,
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
            "FunctionName": function_name,
            "FunctionArn": "arn:aws:lambda:{}:{}:function:{}".format(
                _lambda_region, ACCOUNT_ID, function_name
            ),
            "Runtime": "python2.7",
            "Role": result["Role"],
            "Handler": "lambda_function.lambda_handler",
            "CodeSize": len(zip_content),
            "Description": "test lambda function",
            "Timeout": 3,
            "MemorySize": 128,
            "CodeSha256": base64.b64encode(hashlib.sha256(zip_content).digest()).decode(
                "utf-8"
            ),
            "Version": "1",
            "VpcConfig": {"SecurityGroupIds": [], "SubnetIds": []},
            "ResponseMetadata": {"HTTPStatusCode": 201},
            "State": "Active",
            "Layers": [],
            "TracingConfig": {"Mode": "PassThrough"},
        }
    )


@mock_lambda
@pytest.mark.parametrize(
    "tracing_mode",
    [(None, "PassThrough"), ("PassThrough", "PassThrough"), ("Active", "Active")],
)
def test_create_function__with_tracingmode(tracing_mode):
    conn = boto3.client("lambda", _lambda_region)
    source, output = tracing_mode
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    kwargs = dict(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    if source:
        kwargs["TracingConfig"] = {"Mode": source}
    result = conn.create_function(**kwargs)
    result.should.have.key("TracingConfig").should.equal({"Mode": output})


@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_get_function():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Environment={"Variables": {"test_variable": "test_value"}},
    )

    result = conn.get_function(FunctionName=function_name)
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
        base64.b64encode(hashlib.sha256(zip_content).digest()).decode("utf-8")
    )
    result["Configuration"]["CodeSize"].should.equal(len(zip_content))
    result["Configuration"]["Description"].should.equal("test lambda function")
    result["Configuration"].should.contain("FunctionArn")
    result["Configuration"]["FunctionName"].should.equal(function_name)
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
    result = conn.get_function(FunctionName=function_name, Qualifier="$LATEST")
    result["Configuration"]["Version"].should.equal("$LATEST")
    result["Configuration"]["FunctionArn"].should.equal(
        "arn:aws:lambda:us-west-2:{}:function:{}:$LATEST".format(
            ACCOUNT_ID, function_name
        )
    )

    # Test get function when can't find function name
    with pytest.raises(conn.exceptions.ResourceNotFoundException):
        conn.get_function(FunctionName="junk", Qualifier="$LATEST")


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_get_function_configuration(key):
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    fxn = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Environment={"Variables": {"test_variable": "test_value"}},
    )
    name_or_arn = fxn[key]

    result = conn.get_function_configuration(FunctionName=name_or_arn)

    result["CodeSha256"].should.equal(
        base64.b64encode(hashlib.sha256(zip_content).digest()).decode("utf-8")
    )
    result["CodeSize"].should.equal(len(zip_content))
    result["Description"].should.equal("test lambda function")
    result.should.contain("FunctionArn")
    result["FunctionName"].should.equal(function_name)
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
        FunctionName=name_or_arn, Qualifier="$LATEST"
    )
    result["Version"].should.equal("$LATEST")
    result["FunctionArn"].should.equal(
        "arn:aws:lambda:{}:{}:function:{}:$LATEST".format(
            _lambda_region, ACCOUNT_ID, function_name
        )
    )

    # Test get function when can't find function name
    with pytest.raises(conn.exceptions.ResourceNotFoundException):
        conn.get_function_configuration(FunctionName="junk", Qualifier="$LATEST")


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
@mock_s3
def test_get_function_code_signing_config(key):
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    fxn = conn.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        CodeSigningConfigArn="csc:arn",
    )
    name_or_arn = fxn[key]

    result = conn.get_function_code_signing_config(FunctionName=name_or_arn)

    result["FunctionName"].should.equal(function_name)
    result["CodeSigningConfigArn"].should.equal("csc:arn")


@mock_lambda
@mock_s3
def test_get_function_by_arn():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", "us-east-1")
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", "us-east-1")
    function_name = str(uuid4())[0:6]

    fnc = conn.create_function(
        FunctionName=function_name,
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
    result["Configuration"]["FunctionName"].should.equal(function_name)


@mock_lambda
@mock_s3
def test_delete_function():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    success_result = conn.delete_function(FunctionName=function_name)
    # this is hard to match against, so remove it
    success_result["ResponseMetadata"].pop("HTTPHeaders", None)
    # Botocore inserts retry attempts not seen in Python27
    success_result["ResponseMetadata"].pop("RetryAttempts", None)

    success_result.should.equal({"ResponseMetadata": {"HTTPStatusCode": 204}})

    func_list = conn.list_functions()["Functions"]
    our_functions = [f for f in func_list if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(0)


@mock_lambda
@mock_s3
def test_delete_function_by_arn():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", "us-east-1")
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", "us-east-1")
    function_name = str(uuid4())[0:6]

    fnc = conn.create_function(
        FunctionName=function_name,
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

    func_list = conn.list_functions()["Functions"]
    our_functions = [f for f in func_list if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(0)


@mock_lambda
def test_delete_unknown_function():
    conn = boto3.client("lambda", _lambda_region)
    conn.delete_function.when.called_with(
        FunctionName="testFunctionThatDoesntExist"
    ).should.throw(botocore.client.ClientError)


@mock_lambda
@pytest.mark.parametrize(
    "name",
    [
        "bad_function_name",
        f"arn:aws:lambda:eu-west-1:{ACCOUNT_ID}:function:bad_function_name",
    ],
)
def test_publish_version_unknown_function(name):
    client = boto3.client("lambda", "eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.publish_version(FunctionName=name, Description="v2")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(
        f"Function not found: arn:aws:lambda:eu-west-1:{ACCOUNT_ID}:function:bad_function_name"
    )


@mock_lambda
@mock_s3
def test_publish():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=False,
    )

    function_list = conn.list_functions(FunctionVersion="ALL")["Functions"]
    our_functions = [f for f in function_list if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(1)
    latest_arn = our_functions[0]["FunctionArn"]

    res = conn.publish_version(FunctionName=function_name)
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 201

    function_list = conn.list_functions(FunctionVersion="ALL")["Functions"]
    our_functions = [f for f in function_list if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(2)

    # #SetComprehension ;-)
    published_arn = list({f["FunctionArn"] for f in our_functions} - {latest_arn})[0]
    published_arn.should.contain("{}:1".format(function_name))

    conn.delete_function(FunctionName=function_name, Qualifier="1")

    function_list = conn.list_functions()["Functions"]
    our_functions = [f for f in function_list if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(1)
    our_functions[0]["FunctionArn"].should.contain(function_name)


@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_list_create_list_get_delete_list():
    """
    test `list -> create -> list -> get -> delete -> list` integration

    """
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    initial_list = conn.list_functions()["Functions"]
    initial_names = [f["FunctionName"] for f in initial_list]
    initial_names.shouldnt.contain(function_name)

    function_name = function_name
    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
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
            "CodeSha256": base64.b64encode(hashlib.sha256(zip_content).digest()).decode(
                "utf-8"
            ),
            "CodeSize": len(zip_content),
            "Description": "test lambda function",
            "FunctionName": function_name,
            "Handler": "lambda_function.lambda_handler",
            "MemorySize": 128,
            "Role": get_role_name(),
            "Runtime": "python2.7",
            "Timeout": 3,
            "Version": "$LATEST",
            "VpcConfig": {"SecurityGroupIds": [], "SubnetIds": []},
            "State": "Active",
            "Layers": [],
            "LastUpdateStatus": "Successful",
            "TracingConfig": {"Mode": "PassThrough"},
        },
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }
    functions = conn.list_functions()["Functions"]
    func_names = [f["FunctionName"] for f in functions]
    func_names.should.contain(function_name)

    func_arn = [
        f["FunctionArn"] for f in functions if f["FunctionName"] == function_name
    ][0]
    func_arn.should.equal(
        "arn:aws:lambda:{}:{}:function:{}".format(
            _lambda_region, ACCOUNT_ID, function_name
        )
    )
    functions = conn.list_functions(FunctionVersion="ALL")["Functions"]
    our_functions = [f for f in functions if f["FunctionName"] == function_name]
    our_functions.should.have.length_of(2)

    latest = [f for f in our_functions if f["Version"] == "$LATEST"][0]
    latest["FunctionArn"].should.equal(
        "arn:aws:lambda:{}:{}:function:{}:$LATEST".format(
            _lambda_region, ACCOUNT_ID, function_name
        )
    )
    latest.pop("FunctionArn")
    latest.pop("LastModified")
    latest.should.equal(expected_function_result["Configuration"])

    published = [f for f in our_functions if f["Version"] != "$LATEST"][0]
    published["Version"].should.equal("1")
    published["FunctionArn"].should.equal(
        "arn:aws:lambda:{}:{}:function:{}:1".format(
            _lambda_region, ACCOUNT_ID, function_name
        )
    )

    func = conn.get_function(FunctionName=function_name)

    func["Configuration"]["FunctionArn"].should.equal(
        "arn:aws:lambda:{}:{}:function:{}".format(
            _lambda_region, ACCOUNT_ID, function_name
        )
    )

    # this is hard to match against, so remove it
    func["ResponseMetadata"].pop("HTTPHeaders", None)
    # Botocore inserts retry attempts not seen in Python27
    func["ResponseMetadata"].pop("RetryAttempts", None)
    func["Configuration"].pop("LastModified")
    func["Configuration"].pop("FunctionArn")

    func.should.equal(expected_function_result)
    conn.delete_function(FunctionName=function_name)

    functions = conn.list_functions()["Functions"]
    func_names = [f["FunctionName"] for f in functions]
    func_names.shouldnt.contain(function_name)


@mock_lambda
@freeze_time("2015-01-01 00:00:00")
def test_get_function_created_with_zipfile():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    zip_content = get_test_zip_file1()
    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.get_function(FunctionName=function_name)

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    assert len(response["Code"]) == 2
    assert response["Code"]["RepositoryType"] == "S3"
    assert response["Code"]["Location"].startswith(
        "s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com".format(_lambda_region)
    )
    response.should.have.key("Configuration")
    config = response["Configuration"]
    config.should.have.key("CodeSha256").equals(
        base64.b64encode(hashlib.sha256(zip_content).digest()).decode("utf-8")
    )
    config.should.have.key("CodeSize").equals(len(zip_content))
    config.should.have.key("Description").equals("test lambda function")
    config.should.have.key("FunctionArn").equals(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}"
    )
    config.should.have.key("FunctionName").equals(function_name)
    config.should.have.key("Handler").equals("lambda_function.handler")
    config.should.have.key("MemorySize").equals(128)
    config.should.have.key("Role").equals(get_role_name())
    config.should.have.key("Runtime").equals("python2.7")
    config.should.have.key("Timeout").equals(3)
    config.should.have.key("Version").equals("$LATEST")
    config.should.have.key("State").equals("Active")
    config.should.have.key("Layers").equals([])
    config.should.have.key("LastUpdateStatus").equals("Successful")


@mock_lambda
@mock_s3
def test_list_versions_by_function():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    res = conn.publish_version(FunctionName=function_name)
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 201
    versions = conn.list_versions_by_function(FunctionName=function_name)
    assert len(versions["Versions"]) == 3
    assert versions["Versions"][0][
        "FunctionArn"
    ] == "arn:aws:lambda:us-west-2:{}:function:{}:$LATEST".format(
        ACCOUNT_ID, function_name
    )
    assert versions["Versions"][1][
        "FunctionArn"
    ] == "arn:aws:lambda:us-west-2:{}:function:{}:1".format(ACCOUNT_ID, function_name)
    assert versions["Versions"][2][
        "FunctionArn"
    ] == "arn:aws:lambda:us-west-2:{}:function:{}:2".format(ACCOUNT_ID, function_name)

    conn.create_function(
        FunctionName="testFunction_2",
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
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
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    response = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    assert response["FunctionName"] == function_name


@mock_lambda
@mock_s3
def test_list_versions_by_function_for_nonexistent_function():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    versions = conn.list_versions_by_function(FunctionName=function_name)

    assert len(versions["Versions"]) == 0


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
@mock_s3
def test_update_configuration(key):
    bucket_name = str(uuid4())
    function_name = str(uuid4())[0:6]
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)

    fxn = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Environment={"Variables": {"test_old_environment": "test_old_value"}},
    )
    name_or_arn = fxn[key]

    assert fxn["Description"] == "test lambda function"
    assert fxn["Handler"] == "lambda_function.lambda_handler"
    assert fxn["MemorySize"] == 128
    assert fxn["Runtime"] == "python2.7"
    assert fxn["Timeout"] == 3

    updated_config = conn.update_function_configuration(
        FunctionName=name_or_arn,
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


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
def test_update_function_zip(key):
    conn = boto3.client("lambda", _lambda_region)

    zip_content_one = get_test_zip_file1()
    function_name = str(uuid4())[0:6]

    fxn = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zip_content_one},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    name_or_arn = fxn[key]

    zip_content_two = get_test_zip_file2()

    conn.update_function_code(
        FunctionName=name_or_arn, ZipFile=zip_content_two, Publish=True
    )

    response = conn.get_function(FunctionName=function_name, Qualifier="2")

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    assert len(response["Code"]) == 2
    assert response["Code"]["RepositoryType"] == "S3"
    assert response["Code"]["Location"].startswith(
        "s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com".format(_lambda_region)
    )

    config = response["Configuration"]
    config.should.have.key("CodeSize").equals(len(zip_content_two))
    config.should.have.key("Description").equals("test lambda function")
    config.should.have.key("FunctionArn").equals(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:2"
    )
    config.should.have.key("FunctionName").equals(function_name)
    config.should.have.key("Version").equals("2")
    config.should.have.key("LastUpdateStatus").equals("Successful")


@mock_lambda
@mock_s3
def test_update_function_s3():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)

    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    zip_content_two = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test2.zip", Body=zip_content_two)

    conn.update_function_code(
        FunctionName=function_name,
        S3Bucket=bucket_name,
        S3Key="test2.zip",
        Publish=True,
    )

    response = conn.get_function(FunctionName=function_name, Qualifier="2")

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    assert len(response["Code"]) == 2
    assert response["Code"]["RepositoryType"] == "S3"
    assert response["Code"]["Location"].startswith(
        "s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com".format(_lambda_region)
    )

    config = response["Configuration"]
    config.should.have.key("CodeSha256").equals(
        base64.b64encode(hashlib.sha256(zip_content_two).digest()).decode("utf-8")
    )
    config.should.have.key("CodeSize").equals(len(zip_content_two))
    config.should.have.key("Description").equals("test lambda function")
    config.should.have.key("FunctionArn").equals(
        f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:function:{function_name}:2"
    )
    config.should.have.key("FunctionName").equals(function_name)
    config.should.have.key("Version").equals("2")
    config.should.have.key("LastUpdateStatus").equals("Successful")


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
def test_remove_unknown_permission_throws_error():
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    f = conn.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
    )
    arn = f["FunctionArn"]

    with pytest.raises(ClientError) as exc:
        conn.remove_permission(FunctionName=arn, StatementId="1")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("No policy is associated with the given resource.")
