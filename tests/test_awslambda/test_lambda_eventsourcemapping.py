import json
import sys
import time
import uuid
from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.utilities.distutils_version import LooseVersion

from ..markers import requires_docker
from .utilities import (
    get_role_name,
    get_test_zip_file3,
    get_test_zip_file_error,
    wait_for_log_msg,
)

PYTHON_VERSION = "python3.11"
_lambda_region = "us-west-2"
botocore_version = sys.modules["botocore"].__version__


@mock_aws
def test_create_event_source_mapping():
    if LooseVersion(botocore_version) < LooseVersion("1.23.12"):
        raise SkipTest("Parameter FilterCriteria is not available in older versions")

    function_name = str(uuid.uuid4())[0:6]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    destination_config = {
        "OnSuccess": {"Destination": "s3"},
        "OnFailure": {"Destination": "s4"},
    }
    doc_db_config = {
        "DatabaseName": "db",
        "CollectionName": "cn",
        "FullDocument": "UpdateLookup",
    }
    response = conn.create_event_source_mapping(
        EventSourceArn=queue.attributes["QueueArn"],
        FunctionName=func["FunctionArn"],
        BatchSize=1,
        FilterCriteria={
            "Filters": [{"Pattern": r"asdf"}],
        },
        MaximumBatchingWindowInSeconds=5,
        ParallelizationFactor=4,
        StartingPosition="AT_TIMESTAMP",
        DestinationConfig=destination_config,
        MaximumRecordAgeInSeconds=59,
        BisectBatchOnFunctionError=True,
        MaximumRetryAttempts=9000,
        Tags={"k1": "v1"},
        TumblingWindowInSeconds=100,
        Topics=["t1", "T2"],
        Queues=["q1", "q2"],
        SourceAccessConfigurations=[
            {"Type": "BASIC_AUTH", "URI": "http://auth.endpoint"},
        ],
        SelfManagedEventSource={
            "Endpoints": {
                "key": ["v1"],
            },
        },
        FunctionResponseTypes=["ReportBatchItemFailures"],
        AmazonManagedKafkaEventSourceConfig={"ConsumerGroupId": "cgid"},
        SelfManagedKafkaEventSourceConfig={"ConsumerGroupId": "cgid2"},
        ScalingConfig={"MaximumConcurrency": 100},
        DocumentDBEventSourceConfig=doc_db_config,
        KMSKeyArn="arn:kms:key",
        MetricsConfig={"Metrics": ["EventCount"]},
        ProvisionedPollerConfig={"MinimumPollers": 12, "MaximumPollers": 13},
    )

    assert response["EventSourceArn"] == queue.attributes["QueueArn"]
    assert response["FunctionArn"] == func["FunctionArn"]
    assert response["State"] == "Enabled"
    assert response["BatchSize"] == 1
    assert response["StartingPosition"] == "AT_TIMESTAMP"
    assert response["MaximumBatchingWindowInSeconds"] == 5
    assert response["ParallelizationFactor"] == 4
    assert response["FilterCriteria"] == {"Filters": [{"Pattern": "asdf"}]}
    assert response["DestinationConfig"] == destination_config
    assert response["Topics"] == ["t1", "T2"]
    assert response["Queues"] == ["q1", "q2"]
    assert response["SourceAccessConfigurations"] == [
        {"Type": "BASIC_AUTH", "URI": "http://auth.endpoint"}
    ]
    assert response["SelfManagedEventSource"] == {"Endpoints": {"key": ["v1"]}}
    assert response["MaximumRecordAgeInSeconds"] == 59
    assert response["BisectBatchOnFunctionError"] is True
    assert response["MaximumRetryAttempts"] == 9000
    assert response["TumblingWindowInSeconds"] == 100
    assert response["FunctionResponseTypes"] == ["ReportBatchItemFailures"]
    assert response["AmazonManagedKafkaEventSourceConfig"] == {
        "ConsumerGroupId": "cgid"
    }
    assert response["SelfManagedKafkaEventSourceConfig"] == {"ConsumerGroupId": "cgid2"}
    assert response["ScalingConfig"] == {"MaximumConcurrency": 100}
    assert response["DocumentDBEventSourceConfig"] == doc_db_config
    assert response["KMSKeyArn"] == "arn:kms:key"
    assert response["MetricsConfig"] == {"Metrics": ["EventCount"]}
    assert response["ProvisionedPollerConfig"] == {
        "MinimumPollers": 12,
        "MaximumPollers": 13,
    }
    expected_esm_arn = (
        f"arn:aws:lambda:us-east-1:{ACCOUNT_ID}:event-source-mapping:{response['UUID']}"
    )
    assert response["EventSourceMappingArn"] == expected_esm_arn


@pytest.mark.network
@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_aws
@requires_docker
def test_invoke_function_from_sqs(key):
    function_name = str(uuid.uuid4())[0:6]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
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
@mock_aws
@requires_docker
def test_invoke_function_from_dynamodb_put():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    table_name = str(uuid.uuid4())[0:6] + "_table"
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
    function_name = str(uuid.uuid4())[0:6]
    func = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
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

    item_to_create = {"id": {"S": "item 1"}, "data": {"M": {"nested": {"S": "stuff"}}}}
    dynamodb.put_item(TableName=table_name, Item=item_to_create)

    expected_msg = "get_test_zip_file3 success"
    log_group = f"/aws/lambda/{function_name}"
    msg_showed_up, all_logs = wait_for_log_msg(expected_msg, log_group)

    assert msg_showed_up, (
        expected_msg + " was not found after a DDB insert. All logs: " + str(all_logs)
    )
    assert any(
        [json.dumps(item_to_create, separators=(",", ":")) in msg for msg in all_logs]
    )


@pytest.mark.network
@mock_aws
@requires_docker
def test_invoke_function_from_dynamodb_update():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    table_name = str(uuid.uuid4())[0:6] + "_table"
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
    function_name = str(uuid.uuid4())[0:6]
    func = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
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
    assert "Nr_of_records(2)" not in all_logs, (
        "The inserted item should not show up again"
    )


@pytest.mark.network
@mock_aws
@requires_docker
def test_invoke_function_from_sqs_exception():
    function_name = str(uuid.uuid4())[0:6]
    logs_conn = boto3.client("logs", region_name="us-east-1")
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
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
    for i in range(2):
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
                assert len(messages) == 2
                return
        time.sleep(1)

    assert False, "Test Failed"


@pytest.mark.network
@mock_aws
@requires_docker
def test_invoke_function_from_sns():
    logs_conn = boto3.client("logs", region_name=_lambda_region)
    sns_conn = boto3.client("sns", region_name=_lambda_region)
    sns_conn.create_topic(Name="some-topic")
    topics_json = sns_conn.list_topics()
    topics = topics_json["Topics"]
    topic_arn = topics[0]["TopicArn"]

    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid.uuid4())[0:6]
    result = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
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

    sns_conn.publish(TopicArn=topic_arn, Message=json.dumps({}))

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


@pytest.mark.network
@mock_aws
@requires_docker
def test_invoke_function_from_kinesis():
    logs_conn = boto3.client("logs", region_name=_lambda_region)
    kinesis = boto3.client("kinesis", region_name=_lambda_region)
    stream_name = "my_stream"

    kinesis.create_stream(StreamName=stream_name, ShardCount=2)
    resp = kinesis.describe_stream(StreamName=stream_name)
    kinesis_arn = resp["StreamDescription"]["StreamARN"]

    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid.uuid4())[0:6]
    func = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file3()},
    )

    conn.create_event_source_mapping(
        EventSourceArn=kinesis_arn,
        FunctionName=func["FunctionArn"],
    )

    # Send Data
    kinesis.put_record(StreamName=stream_name, Data="data", PartitionKey="1")

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

        time.sleep(0.5)

    assert False, "Expected message not found in logs:" + str(events)


@mock_aws
def test_list_event_source_mappings():
    function_name = str(uuid.uuid4())[0:6]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
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
    assert len(mappings["EventSourceMappings"]) >= 1
    assert mappings["EventSourceMappings"][0]["UUID"] == response["UUID"]
    assert mappings["EventSourceMappings"][0]["FunctionArn"] == func["FunctionArn"]


@mock_aws
def test_get_event_source_mapping():
    function_name = str(uuid.uuid4())[0:6]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
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

    with pytest.raises(ClientError) as exc:
        conn.get_event_source_mapping(UUID="1")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "The resource you requested does not exist."


@mock_aws
def test_update_event_source_mapping():
    if LooseVersion(botocore_version) < LooseVersion("1.23.12"):
        raise SkipTest("Parameter FilterCriteria is not available in older versions")

    function_name = str(uuid.uuid4())[0:6]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func1 = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
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
        Runtime=PYTHON_VERSION,
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

    destination_config = {
        "OnSuccess": {"Destination": "s3"},
        "OnFailure": {"Destination": "s4"},
    }
    doc_db_config = {
        "DatabaseName": "db",
        "CollectionName": "cn",
        "FullDocument": "UpdateLookup",
    }

    mapping = conn.update_event_source_mapping(
        UUID=response["UUID"],
        Enabled=False,
        BatchSize=2,
        FunctionName="testFunction2",
        FilterCriteria={
            "Filters": [{"Pattern": r"asdf"}],
        },
        MaximumBatchingWindowInSeconds=5,
        ParallelizationFactor=4,
        DestinationConfig=destination_config,
        MaximumRecordAgeInSeconds=59,
        BisectBatchOnFunctionError=True,
        MaximumRetryAttempts=9000,
        TumblingWindowInSeconds=100,
        SourceAccessConfigurations=[
            {"Type": "BASIC_AUTH", "URI": "http://auth.endpoint"},
        ],
        FunctionResponseTypes=["ReportBatchItemFailures"],
        ScalingConfig={"MaximumConcurrency": 100},
        DocumentDBEventSourceConfig=doc_db_config,
        KMSKeyArn="arn:kms:key",
        MetricsConfig={"Metrics": ["EventCount"]},
        ProvisionedPollerConfig={"MinimumPollers": 12, "MaximumPollers": 13},
    )
    assert mapping["UUID"] == response["UUID"]
    assert mapping["FunctionArn"] == func2["FunctionArn"]
    assert mapping["State"] == "Disabled"
    assert mapping["BatchSize"] == 2

    assert mapping["MaximumBatchingWindowInSeconds"] == 5
    assert mapping["ParallelizationFactor"] == 4
    assert mapping["FilterCriteria"] == {"Filters": [{"Pattern": "asdf"}]}
    assert mapping["DestinationConfig"] == destination_config
    assert mapping["SourceAccessConfigurations"] == [
        {"Type": "BASIC_AUTH", "URI": "http://auth.endpoint"}
    ]
    assert mapping["MaximumRecordAgeInSeconds"] == 59
    assert mapping["BisectBatchOnFunctionError"] is True
    assert mapping["MaximumRetryAttempts"] == 9000
    assert mapping["TumblingWindowInSeconds"] == 100
    assert mapping["FunctionResponseTypes"] == ["ReportBatchItemFailures"]
    assert mapping["ScalingConfig"] == {"MaximumConcurrency": 100}
    assert mapping["DocumentDBEventSourceConfig"] == doc_db_config
    assert mapping["KMSKeyArn"] == "arn:kms:key"
    assert mapping["MetricsConfig"] == {"Metrics": ["EventCount"]}
    assert mapping["ProvisionedPollerConfig"] == {
        "MinimumPollers": 12,
        "MaximumPollers": 13,
    }


@mock_aws
def test_delete_event_source_mapping():
    function_name = str(uuid.uuid4())[0:6]
    sqs = boto3.resource("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName=f"{function_name}_queue")

    conn = boto3.client("lambda", region_name="us-east-1")
    func1 = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
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
    with pytest.raises(ClientError) as exc:
        conn.get_event_source_mapping(UUID=response["UUID"])
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "The resource you requested does not exist."


@mock_aws
def test_event_source_mapping_tagging_lifecycle():
    if LooseVersion(botocore_version) < LooseVersion("1.35.23"):
        raise SkipTest(
            "Tagging support for Lambda event source mapping is not available in older Botocore versions"
        )

    iam = boto3.client("iam", region_name="us-east-1")
    iam_role = iam.create_role(RoleName="role", AssumeRolePolicyDocument="{}")
    client = boto3.client("lambda", region_name="us-east-1")
    client.create_function(
        FunctionName="any-function-name",
        Runtime="python3.6",
        Role=iam_role["Role"]["Arn"],
        Handler="any-handler",
        Code={
            "ZipFile": b"any zip file",
        },
    )
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_url = sqs.create_queue(QueueName="any-queue-name")
    queue_arn = sqs.get_queue_attributes(
        QueueUrl=queue_url["QueueUrl"], AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]
    event_source_mapping = client.create_event_source_mapping(
        FunctionName="any-function-name",
        EventSourceArn=queue_arn,
    )
    esm_arn = event_source_mapping["EventSourceMappingArn"]
    tags = {"foo": "bar", "baz": "qux"}
    client.tag_resource(Resource=esm_arn, Tags=tags)
    resp = client.list_tags(Resource=esm_arn)
    for key, value in tags.items():
        assert resp["Tags"][key] == value
    client.untag_resource(Resource=esm_arn, TagKeys=["foo"])
    resp = client.list_tags(Resource=esm_arn)
    assert resp["Tags"] == {"baz": "qux"}
