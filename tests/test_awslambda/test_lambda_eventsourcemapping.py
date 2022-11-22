import botocore.client
import boto3
import json
import pytest
import time
import sure  # noqa # pylint: disable=unused-import
import uuid

from moto import mock_dynamodb, mock_lambda, mock_logs, mock_sns, mock_sqs
from uuid import uuid4
from .utilities import (
    get_role_name,
    get_test_zip_file3,
    wait_for_log_msg,
    get_test_zip_file_error,
)

_lambda_region = "us-west-2"
boto3.setup_default_session(region_name=_lambda_region)


@mock_logs
@mock_lambda
@mock_sqs
def test_create_event_source_mapping():
    function_name = str(uuid4())[0:6]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=function_name,
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
@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_logs
@mock_lambda
@mock_sqs
def test_invoke_function_from_sqs(key):
    function_name = str(uuid4())[0:6]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    name_or_arn = func[key]

    response = conn.create_event_source_mapping(
        EventSourceArn=queue.attributes["QueueArn"], FunctionName=name_or_arn
    )

    assert response["EventSourceArn"] == queue.attributes["QueueArn"]
    assert response["State"] == "Enabled"

    sqs_client = boto3.client("sqs", region_name="us-east-1")
    sqs_client.send_message(QueueUrl=queue.url, MessageBody="test")

    expected_msg = "get_test_zip_file3 success"
    log_group = f"/aws/lambda/{function_name}"
    msg_showed_up, all_logs = wait_for_log_msg(expected_msg, log_group)

    assert msg_showed_up, (
        expected_msg
        + " was not found after sending an SQS message. All logs: "
        + str(all_logs)
    )


@pytest.mark.network
@mock_logs
@mock_lambda
@mock_dynamodb
def test_invoke_function_from_dynamodb_put():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    table_name = str(uuid4())[0:6] + "_table"
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
    )

    conn = boto3.client("lambda", region_name="us-east-1")
    function_name = str(uuid4())[0:6]
    func = conn.create_function(
        FunctionName=function_name,
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
    log_group = f"/aws/lambda/{function_name}"
    msg_showed_up, all_logs = wait_for_log_msg(expected_msg, log_group)

    assert msg_showed_up, (
        expected_msg + " was not found after a DDB insert. All logs: " + str(all_logs)
    )


@pytest.mark.network
@mock_logs
@mock_lambda
@mock_dynamodb
def test_invoke_function_from_dynamodb_update():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    table_name = str(uuid4())[0:6] + "_table"
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
    )

    conn = boto3.client("lambda", region_name="us-east-1")
    function_name = str(uuid4())[0:6]
    func = conn.create_function(
        FunctionName=function_name,
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
    log_group = f"/aws/lambda/{function_name}"
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


@pytest.mark.network
@mock_logs
@mock_lambda
@mock_sqs
def test_invoke_function_from_sqs_exception():
    function_name = str(uuid4())[0:6]
    logs_conn = boto3.client("logs", region_name="us-east-1")
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file_error()},
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
        body = {"uuid": str(uuid.uuid4()), "test": f"test_{i}"}
        entry = {"Id": str(i), "MessageBody": json.dumps(body)}
        entries.append(entry)

    queue.send_messages(Entries=entries)

    start = time.time()
    while (time.time() - start) < 30:
        result = logs_conn.describe_log_streams(
            logGroupName=f"/aws/lambda/{function_name}"
        )
        log_streams = result.get("logStreams")
        if not log_streams:
            time.sleep(1)
            continue
        assert len(log_streams) >= 1

        result = logs_conn.get_log_events(
            logGroupName=f"/aws/lambda/{function_name}",
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


@pytest.mark.network
@mock_logs
@mock_sns
@mock_lambda
def test_invoke_function_from_sns():
    logs_conn = boto3.client("logs", region_name=_lambda_region)
    sns_conn = boto3.client("sns", region_name=_lambda_region)
    sns_conn.create_topic(Name="some-topic")
    topics_json = sns_conn.list_topics()
    topics = topics_json["Topics"]
    topic_arn = topics[0]["TopicArn"]

    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    result = conn.create_function(
        FunctionName=function_name,
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
    events = []
    while (time.time() - start) < 10:
        result = logs_conn.describe_log_streams(
            logGroupName=f"/aws/lambda/{function_name}"
        )
        log_streams = result.get("logStreams")
        if not log_streams:
            time.sleep(1)
            continue

        assert len(log_streams) == 1
        result = logs_conn.get_log_events(
            logGroupName=f"/aws/lambda/{function_name}",
            logStreamName=log_streams[0]["logStreamName"],
        )
        events = result.get("events")
        for event in events:
            if event["message"] == "get_test_zip_file3 success":
                return

        time.sleep(1)

    assert False, "Expected message not found in logs:" + str(events)


@mock_logs
@mock_lambda
@mock_sqs
def test_list_event_source_mappings():
    function_name = str(uuid4())[0:6]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=function_name,
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
    mappings["EventSourceMappings"].should.have.length_of(0)

    mappings = conn.list_event_source_mappings(
        EventSourceArn=queue.attributes["QueueArn"]
    )
    assert len(mappings["EventSourceMappings"]) >= 1
    assert mappings["EventSourceMappings"][0]["UUID"] == response["UUID"]
    assert mappings["EventSourceMappings"][0]["FunctionArn"] == func["FunctionArn"]


@mock_lambda
@mock_sqs
def test_get_event_source_mapping():
    function_name = str(uuid4())[0:6]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=function_name,
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
    function_name = str(uuid4())[0:6]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func1 = conn.create_function(
        FunctionName=function_name,
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
    function_name = str(uuid4())[0:6]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func1 = conn.create_function(
        FunctionName=function_name,
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
