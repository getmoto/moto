import base64
from io import BytesIO
import json
import time
from zipfile import ZipFile, ZIP_DEFLATED
import zlib

import boto3
from botocore.exceptions import ClientError
from moto import mock_logs, mock_lambda, mock_iam, mock_firehose, mock_s3
from moto import mock_kinesis
from moto.core.utils import unix_time_millis
import pytest

from tests.markers import requires_docker


@mock_lambda
@mock_logs
def test_put_subscription_filter_update():
    # given
    region_name = "us-east-1"
    client_lambda = boto3.client("lambda", region_name)
    client_logs = boto3.client("logs", region_name)
    log_group_name = "/test"
    log_stream_name = "stream"
    client_logs.create_log_group(logGroupName=log_group_name)
    client_logs.create_log_stream(
        logGroupName=log_group_name, logStreamName=log_stream_name
    )
    function_arn = client_lambda.create_function(
        FunctionName="test",
        Runtime="python3.11",
        Role=_get_role_name(region_name),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": _get_test_zip_file()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )["FunctionArn"]

    # when
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="test",
        filterPattern="",
        destinationArn=function_arn,
    )

    # then
    response = client_logs.describe_subscription_filters(logGroupName=log_group_name)
    assert len(response["subscriptionFilters"]) == 1
    sub_filter = response["subscriptionFilters"][0]
    creation_time = sub_filter["creationTime"]
    assert isinstance(creation_time, int)
    sub_filter["destinationArn"] = "arn:aws:lambda:us-east-1:123456789012:function:test"
    sub_filter["distribution"] = "ByLogStream"
    sub_filter["logGroupName"] = "/test"
    sub_filter["filterName"] = "test"
    sub_filter["filterPattern"] = ""

    # when
    # to update an existing subscription filter the 'filterName' must be identical
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="test",
        filterPattern="[]",
        destinationArn=function_arn,
    )

    # then
    response = client_logs.describe_subscription_filters(logGroupName=log_group_name)
    assert len(response["subscriptionFilters"]) == 1
    sub_filter = response["subscriptionFilters"][0]
    assert sub_filter["creationTime"] == creation_time
    sub_filter["destinationArn"] = "arn:aws:lambda:us-east-1:123456789012:function:test"
    sub_filter["distribution"] = "ByLogStream"
    sub_filter["logGroupName"] = "/test"
    sub_filter["filterName"] = "test"
    sub_filter["filterPattern"] = "[]"

    # when
    # only two subscription filters can be associated with a log group
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="test-2",
        filterPattern="[]",
        destinationArn=function_arn,
    )
    with pytest.raises(ClientError) as e:
        client_logs.put_subscription_filter(
            logGroupName=log_group_name,
            filterName="test-3",
            filterPattern="",
            destinationArn=function_arn,
        )

    # then
    ex = e.value
    assert ex.operation_name == "PutSubscriptionFilter"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "LimitExceededException"
    assert ex.response["Error"]["Message"] == "Resource limit exceeded."


@mock_lambda
@mock_logs
@pytest.mark.network
@requires_docker
def test_put_subscription_filter_with_lambda():
    # given
    region_name = "us-east-1"
    client_lambda = boto3.client("lambda", region_name)
    client_logs = boto3.client("logs", region_name)
    log_group_name = "/test"
    log_stream_name = "stream"
    client_logs.create_log_group(logGroupName=log_group_name)
    client_logs.create_log_stream(
        logGroupName=log_group_name, logStreamName=log_stream_name
    )
    function_arn = client_lambda.create_function(
        FunctionName="test",
        Runtime="python3.11",
        Role=_get_role_name(region_name),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": _get_test_zip_file()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )["FunctionArn"]

    # when
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="test",
        filterPattern="",
        destinationArn=function_arn,
    )

    # then
    response = client_logs.describe_subscription_filters(logGroupName=log_group_name)
    assert len(response["subscriptionFilters"]) == 1
    sub_filter = response["subscriptionFilters"][0]
    assert isinstance(sub_filter["creationTime"], int)
    sub_filter["destinationArn"] = "arn:aws:lambda:us-east-1:123456789012:function:test"
    sub_filter["distribution"] = "ByLogStream"
    sub_filter["logGroupName"] = "/test"
    sub_filter["filterName"] = "test"
    sub_filter["filterPattern"] = ""

    # when
    ts_0 = int(unix_time_millis())
    ts_1 = int(unix_time_millis()) + 10
    client_logs.put_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        logEvents=[
            {"timestamp": ts_0, "message": "test"},
            {"timestamp": ts_1, "message": "test 2"},
        ],
    )

    # then
    msg_showed_up, received_message = _wait_for_log_msg(
        client_logs, "/aws/lambda/test", "awslogs"
    )
    assert (
        msg_showed_up
    ), f"CloudWatch log event was not found. All logs: {received_message}"

    data = json.loads(received_message)["awslogs"]["data"]
    response = json.loads(
        zlib.decompress(base64.b64decode(data), 16 + zlib.MAX_WBITS).decode("utf-8")
    )
    assert response["messageType"] == "DATA_MESSAGE"
    assert response["owner"] == "123456789012"
    assert response["logGroup"] == "/test"
    assert response["logStream"] == "stream"
    assert response["subscriptionFilters"] == ["test"]
    log_events = sorted(response["logEvents"], key=lambda log_event: log_event["id"])
    assert len(log_events) == 2
    assert isinstance(log_events[0]["id"], int)
    assert log_events[0]["message"] == "test"
    assert log_events[0]["timestamp"] == ts_0
    assert isinstance(log_events[1]["id"], int)
    assert log_events[1]["message"] == "test 2"
    assert log_events[1]["timestamp"] == ts_1


@mock_lambda
@mock_logs
@pytest.mark.network
@requires_docker
def test_subscription_filter_applies_to_new_streams():
    # given
    region_name = "us-east-1"
    client_lambda = boto3.client("lambda", region_name)
    client_logs = boto3.client("logs", region_name)
    log_group_name = "/test"
    log_stream_name = "stream"
    client_logs.create_log_group(logGroupName=log_group_name)
    function_arn = client_lambda.create_function(
        FunctionName="test",
        Runtime="python3.11",
        Role=_get_role_name(region_name),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": _get_test_zip_file()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )["FunctionArn"]

    # when
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="test",
        filterPattern="",
        destinationArn=function_arn,
    )
    client_logs.create_log_stream(  # create log stream after subscription filter applied
        logGroupName=log_group_name, logStreamName=log_stream_name
    )
    ts_0 = int(unix_time_millis())
    ts_1 = int(unix_time_millis()) + 10
    client_logs.put_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        logEvents=[
            {"timestamp": ts_0, "message": "test"},
            {"timestamp": ts_1, "message": "test 2"},
        ],
    )

    # then
    msg_showed_up, received_message = _wait_for_log_msg(
        client_logs, "/aws/lambda/test", "awslogs"
    )
    assert (
        msg_showed_up
    ), f"CloudWatch log event was not found. All logs: {received_message}"

    data = json.loads(received_message)["awslogs"]["data"]
    response = json.loads(
        zlib.decompress(base64.b64decode(data), 16 + zlib.MAX_WBITS).decode("utf-8")
    )
    assert response["messageType"] == "DATA_MESSAGE"
    assert response["owner"] == "123456789012"
    assert response["logGroup"] == "/test"
    assert response["logStream"] == "stream"
    assert response["subscriptionFilters"] == ["test"]
    log_events = sorted(response["logEvents"], key=lambda log_event: log_event["id"])
    assert len(log_events) == 2
    assert isinstance(log_events[0]["id"], int)
    assert log_events[0]["message"] == "test"
    assert log_events[0]["timestamp"] == ts_0
    assert isinstance(log_events[1]["id"], int)
    assert log_events[1]["message"] == "test 2"
    assert log_events[1]["timestamp"] == ts_1


@mock_s3
@mock_firehose
@mock_logs
@pytest.mark.network
def test_put_subscription_filter_with_firehose():
    # given
    region_name = "us-east-1"
    client_firehose = boto3.client("firehose", region_name)
    client_logs = boto3.client("logs", region_name)

    log_group_name = "/firehose-test"
    log_stream_name = "delivery-stream"
    client_logs.create_log_group(logGroupName=log_group_name)
    client_logs.create_log_stream(
        logGroupName=log_group_name, logStreamName=log_stream_name
    )

    # Create a S3 bucket.
    bucket_name = "firehosetestbucket"
    s3_client = boto3.client("s3", region_name=region_name)
    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-1"},
    )

    # Create the Firehose delivery stream that uses that S3 bucket as
    # the destination.
    delivery_stream_name = "firehose_log_test"
    firehose_arn = client_firehose.create_delivery_stream(
        DeliveryStreamName=delivery_stream_name,
        ExtendedS3DestinationConfiguration={
            "RoleARN": _get_role_name(region_name),
            "BucketARN": f"arn:aws:s3::{bucket_name}",
        },
    )["DeliveryStreamARN"]

    # when
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="firehose-test",
        filterPattern="",
        destinationArn=firehose_arn,
    )

    # then
    response = client_logs.describe_subscription_filters(logGroupName=log_group_name)
    assert len(response["subscriptionFilters"]) == 1
    _filter = response["subscriptionFilters"][0]
    assert isinstance(_filter["creationTime"], int)
    _filter["destinationArn"] = firehose_arn
    _filter["distribution"] = "ByLogStream"
    _filter["logGroupName"] = "/firehose-test"
    _filter["filterName"] = "firehose-test"
    _filter["filterPattern"] = ""

    # when
    ts_0 = int(unix_time_millis())
    ts_1 = int(unix_time_millis())
    client_logs.put_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        logEvents=[
            {"timestamp": ts_0, "message": "test"},
            {"timestamp": ts_1, "message": "test 2"},
        ],
    )

    # then
    bucket_objects = s3_client.list_objects_v2(Bucket=bucket_name)
    message = s3_client.get_object(
        Bucket=bucket_name, Key=bucket_objects["Contents"][0]["Key"]
    )
    response = json.loads(
        zlib.decompress(message["Body"].read(), 16 + zlib.MAX_WBITS).decode("utf-8")
    )

    assert response["messageType"] == "DATA_MESSAGE"
    assert response["owner"] == "123456789012"
    assert response["logGroup"] == "/firehose-test"
    assert response["logStream"] == "delivery-stream"
    assert response["subscriptionFilters"] == ["firehose-test"]
    log_events = sorted(response["logEvents"], key=lambda log_event: log_event["id"])
    assert len(log_events) == 2
    assert isinstance(log_events[0]["id"], int)
    assert log_events[0]["message"] == "test"
    assert log_events[0]["timestamp"] == ts_0
    assert isinstance(log_events[1]["id"], int)
    assert log_events[1]["message"] == "test 2"
    assert log_events[1]["timestamp"] == ts_1


@mock_iam
@mock_logs
@mock_kinesis
def test_put_subscription_filter_with_kinesis():
    logs = boto3.client("logs", "ap-southeast-2")
    logs.create_log_group(logGroupName="lg1")
    logs.create_log_stream(logGroupName="lg1", logStreamName="ls1")

    # Create a DataStream
    kinesis = boto3.client("kinesis", "ap-southeast-2")
    kinesis.create_stream(
        StreamName="test-stream",
        ShardCount=1,
        StreamModeDetails={"StreamMode": "ON_DEMAND"},
    )
    kinesis_datastream = kinesis.describe_stream(StreamName="test-stream")[
        "StreamDescription"
    ]
    kinesis_datastream_arn = kinesis_datastream["StreamARN"]

    # Subscribe to new log events
    logs.put_subscription_filter(
        logGroupName="lg1",
        filterName="kinesis_erica_core_components_v2",
        filterPattern='- "cwlogs.push.publisher"',
        destinationArn=kinesis_datastream_arn,
        distribution="ByLogStream",
    )

    # Create new log events
    ts_0 = int(unix_time_millis())
    ts_1 = int(unix_time_millis())
    logs.put_log_events(
        logGroupName="lg1",
        logStreamName="ls1",
        logEvents=[
            {"timestamp": ts_0, "message": "test"},
            {"timestamp": ts_1, "message": "test 2"},
        ],
    )

    # Verify that Kinesis Stream has this data
    nr_of_records = 0
    # We don't know to which shard it was send, so check all of them
    for shard in kinesis_datastream["Shards"]:
        shard_id = shard["ShardId"]

        shard_iterator = kinesis.get_shard_iterator(
            StreamName="test-stream", ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
        )["ShardIterator"]

        resp = kinesis.get_records(ShardIterator=shard_iterator)
        nr_of_records = nr_of_records + len(resp["Records"])
    assert nr_of_records == 1


@mock_lambda
@mock_logs
def test_delete_subscription_filter():
    # given
    region_name = "us-east-1"
    client_lambda = boto3.client("lambda", region_name)
    client_logs = boto3.client("logs", region_name)
    log_group_name = "/test"
    client_logs.create_log_group(logGroupName=log_group_name)
    function_arn = client_lambda.create_function(
        FunctionName="test",
        Runtime="python3.11",
        Role=_get_role_name(region_name),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": _get_test_zip_file()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )["FunctionArn"]
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="test",
        filterPattern="",
        destinationArn=function_arn,
    )

    # when
    client_logs.delete_subscription_filter(logGroupName="/test", filterName="test")

    # then
    response = client_logs.describe_subscription_filters(logGroupName=log_group_name)
    assert len(response["subscriptionFilters"]) == 0


@mock_lambda
@mock_logs
def test_delete_subscription_filter_errors():
    # given
    region_name = "us-east-1"
    client_lambda = boto3.client("lambda", region_name)
    client_logs = boto3.client("logs", region_name)
    log_group_name = "/test"
    client_logs.create_log_group(logGroupName=log_group_name)
    function_arn = client_lambda.create_function(
        FunctionName="test",
        Runtime="python3.11",
        Role=_get_role_name(region_name),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": _get_test_zip_file()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )["FunctionArn"]
    client_logs.put_subscription_filter(
        logGroupName=log_group_name,
        filterName="test",
        filterPattern="",
        destinationArn=function_arn,
    )

    # when
    with pytest.raises(ClientError) as e:
        client_logs.delete_subscription_filter(
            logGroupName="not-existing-log-group", filterName="test"
        )

    # then
    ex = e.value
    assert ex.operation_name == "DeleteSubscriptionFilter"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ResourceNotFoundException"
    assert ex.response["Error"]["Message"] == "The specified log group does not exist"

    # when
    with pytest.raises(ClientError) as e:
        client_logs.delete_subscription_filter(
            logGroupName="/test", filterName="wrong-filter-name"
        )

    # then
    ex = e.value
    assert ex.operation_name == "DeleteSubscriptionFilter"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == "The specified subscription filter does not exist."
    )


@mock_lambda
@mock_logs
def test_put_subscription_filter_errors():
    # given
    client_lambda = boto3.client("lambda", "us-east-1")
    function_arn = client_lambda.create_function(
        FunctionName="test",
        Runtime="python3.11",
        Role=_get_role_name("us-east-1"),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": _get_test_zip_file()},
    )["FunctionArn"]
    client = boto3.client("logs", "us-east-1")
    log_group_name = "/test"
    client.create_log_group(logGroupName=log_group_name)

    # when
    with pytest.raises(ClientError) as e:
        client.put_subscription_filter(
            logGroupName="not-existing-log-group",
            filterName="test",
            filterPattern="",
            destinationArn=function_arn,
        )

    # then
    ex = e.value
    assert ex.operation_name == "PutSubscriptionFilter"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ResourceNotFoundException"
    assert ex.response["Error"]["Message"] == "The specified log group does not exist"

    # when
    with pytest.raises(ClientError) as e:
        client.put_subscription_filter(
            logGroupName="/test",
            filterName="test",
            filterPattern="",
            destinationArn="arn:aws:lambda:us-east-1:123456789012:function:not-existing",
        )

    # then
    ex = e.value
    assert ex.operation_name == "PutSubscriptionFilter"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.response["Error"]["Message"]
        == "Could not execute the lambda function. Make sure you have given CloudWatch Logs permission to execute your function."
    )

    # when
    with pytest.raises(ClientError) as e:
        client.put_subscription_filter(
            logGroupName="/test",
            filterName="test",
            filterPattern="",
            destinationArn="arn:aws:lambda:us-east-1:123456789012:function:not-existing",
        )

    # then
    ex = e.value
    assert ex.operation_name == "PutSubscriptionFilter"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.response["Error"]["Message"]
        == "Could not execute the lambda function. Make sure you have given CloudWatch Logs permission to execute your function."
    )

    # when we pass an unknown kinesis ARN
    with pytest.raises(ClientError) as e:
        client.put_subscription_filter(
            logGroupName="/test",
            filterName="test",
            filterPattern="",
            destinationArn="arn:aws:kinesis:us-east-1:123456789012:stream/unknown-stream",
        )

    # then
    err = e.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"


def _get_role_name(region_name):
    with mock_iam():
        iam = boto3.client("iam", region_name=region_name)
        try:
            return iam.get_role(RoleName="test-role")["Role"]["Arn"]
        except ClientError:
            return iam.create_role(
                RoleName="test-role", AssumeRolePolicyDocument="test policy", Path="/"
            )["Role"]["Arn"]


def _get_test_zip_file():
    func_str = """
def lambda_handler(event, context):
    return event
"""

    zip_output = BytesIO()
    zip_file = ZipFile(zip_output, "w", ZIP_DEFLATED)
    zip_file.writestr("lambda_function.py", func_str)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


def _wait_for_log_msg(client, log_group_name, expected_msg_part):
    received_messages = []
    start = time.time()
    while (time.time() - start) < 10:
        result = client.describe_log_streams(logGroupName=log_group_name)
        log_streams = result.get("logStreams")
        if not log_streams:
            time.sleep(1)
            continue

        for log_stream in log_streams:
            result = client.get_log_events(
                logGroupName=log_group_name, logStreamName=log_stream["logStreamName"]
            )
            received_messages.extend(
                [event["message"] for event in result.get("events")]
            )
        for message in received_messages:
            if expected_msg_part in message:
                return True, message
        time.sleep(1)
    return False, received_messages
