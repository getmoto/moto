import boto3
import json
import pytest
from moto import mock_lambda, mock_logs, mock_s3, mock_sqs
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests.markers import requires_docker
from tests.test_awslambda.utilities import (
    get_test_zip_file_print_event,
    get_role_name,
    wait_for_log_msg,
)
from uuid import uuid4


REGION_NAME = "us-east-1"


@mock_lambda
@mock_logs
@mock_s3
@pytest.mark.parametrize(
    "match_events,actual_event",
    [
        (["s3:ObjectCreated:Put"], "ObjectCreated:Put"),
        (["s3:ObjectCreated:*"], "ObjectCreated:Put"),
        (["s3:ObjectCreated:Post"], None),
        (["s3:ObjectCreated:Post", "s3:ObjectCreated:*"], "ObjectCreated:Put"),
    ],
)
@requires_docker
def test_objectcreated_put__invokes_lambda(match_events, actual_event):
    s3_res = boto3.resource("s3", region_name=REGION_NAME)
    s3_client = boto3.client("s3", region_name=REGION_NAME)
    lambda_client = boto3.client("lambda", REGION_NAME)

    # Create S3 bucket
    bucket_name = str(uuid4())
    s3_res.create_bucket(Bucket=bucket_name)

    # Create AWSLambda function
    function_name = str(uuid4())[0:6]
    fn_arn = lambda_client.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file_print_event()},
    )["FunctionArn"]

    # Put Notification
    s3_client.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration={
            "LambdaFunctionConfigurations": [
                {
                    "Id": "unrelated",
                    "LambdaFunctionArn": f"arn:aws:lambda:us-east-1:{ACCOUNT_ID}:function:n/a",
                    "Events": ["s3:ReducedRedundancyLostObject"],
                },
                {
                    "Id": "s3eventtriggerslambda",
                    "LambdaFunctionArn": fn_arn,
                    "Events": match_events,
                },
            ]
        },
    )

    # Put Object
    s3_client.put_object(Bucket=bucket_name, Key="keyname", Body="bodyofnewobject")

    # Find the output of AWSLambda
    expected_msg = "FINISHED_PRINTING_EVENT"
    log_group = f"/aws/lambda/{function_name}"
    msg_showed_up, all_logs = wait_for_log_msg(expected_msg, log_group, wait_time=10)

    if actual_event is None:
        # The event should not be fired on POST, as we've only PUT an event for now
        assert not msg_showed_up
        return

    # If we do have an actual event, verify the Lambda was invoked with the correct event
    assert msg_showed_up, (
        expected_msg
        + " was not found after sending an SQS message. All logs: "
        + str(all_logs)
    )

    records = [line for line in all_logs if line.startswith("{'Records'")][0]
    records = json.loads(records.replace("'", '"'))["Records"]

    records.should.have.length_of(1)
    records[0].should.have.key("awsRegion").equals(REGION_NAME)
    records[0].should.have.key("eventName").equals(actual_event)
    records[0].should.have.key("eventSource").equals("aws:s3")
    records[0].should.have.key("eventTime")
    records[0].should.have.key("s3")
    records[0]["s3"].should.have.key("bucket")
    records[0]["s3"]["bucket"].should.have.key("arn").equals(
        f"arn:aws:s3:::{bucket_name}"
    )
    records[0]["s3"]["bucket"].should.have.key("name").equals(bucket_name)
    records[0]["s3"].should.have.key("configurationId").equals("s3eventtriggerslambda")
    records[0]["s3"].should.have.key("object")
    records[0]["s3"]["object"].should.have.key("eTag").equals(
        "61ea96c3c8d2c76fc5a42bfccb6affd9"
    )
    records[0]["s3"]["object"].should.have.key("key").equals("keyname")
    records[0]["s3"]["object"].should.have.key("size").equals(15)


@mock_logs
@mock_s3
def test_objectcreated_put__unknown_lambda_is_handled_gracefully():
    s3_res = boto3.resource("s3", region_name=REGION_NAME)
    s3_client = boto3.client("s3", region_name=REGION_NAME)

    # Create S3 bucket
    bucket_name = str(uuid4())
    s3_res.create_bucket(Bucket=bucket_name)

    # Put Notification
    s3_client.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration={
            "LambdaFunctionConfigurations": [
                {
                    "Id": "unrelated",
                    "LambdaFunctionArn": f"arn:aws:lambda:us-east-1:{ACCOUNT_ID}:function:n/a",
                    "Events": ["s3:ObjectCreated:Put"],
                }
            ]
        },
    )

    # Put Object
    s3_client.put_object(Bucket=bucket_name, Key="keyname", Body="bodyofnewobject")

    # The object was persisted successfully
    resp = s3_client.get_object(Bucket=bucket_name, Key="keyname")
    resp.should.have.key("ContentLength").equal(15)
    resp["Body"].read().should.equal(b"bodyofnewobject")


@mock_s3
@mock_sqs
def test_object_copy__sends_to_queue():
    s3_res = boto3.resource("s3", region_name=REGION_NAME)
    s3_client = boto3.client("s3", region_name=REGION_NAME)
    sqs_client = boto3.client("sqs", region_name=REGION_NAME)

    # Create S3 bucket
    bucket_name = str(uuid4())
    s3_res.create_bucket(Bucket=bucket_name)

    # Create SQS queue
    queue_url = sqs_client.create_queue(QueueName=str(uuid4())[0:6])["QueueUrl"]
    queue_arn = sqs_client.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    # Put Notification
    s3_client.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration={
            "QueueConfigurations": [
                {
                    "Id": "queue_config",
                    "QueueArn": queue_arn,
                    "Events": ["s3:ObjectCreated:Copy"],
                }
            ]
        },
    )

    # We should have received a test event now
    messages = sqs_client.receive_message(QueueUrl=queue_url)["Messages"]
    messages.should.have.length_of(1)
    message = json.loads(messages[0]["Body"])
    message.should.have.key("Service").equals("Amazon S3")
    message.should.have.key("Event").equals("s3:TestEvent")
    message.should.have.key("Time")
    message.should.have.key("Bucket").equals(bucket_name)

    # Copy an Object
    s3_client.put_object(Bucket=bucket_name, Key="keyname", Body="bodyofnewobject")
    s3_client.copy_object(
        Bucket=bucket_name, CopySource=f"{bucket_name}/keyname", Key="key2"
    )

    # Read SQS messages - we should have the Copy-event here
    resp = sqs_client.receive_message(QueueUrl=queue_url)
    resp.should.have.key("Messages").length_of(1)
    records = json.loads(resp["Messages"][0]["Body"])["Records"]

    records.should.have.length_of(1)
    records[0].should.have.key("awsRegion").equals(REGION_NAME)
    records[0].should.have.key("eventName").equals("ObjectCreated:Copy")
    records[0].should.have.key("eventSource").equals("aws:s3")
    records[0].should.have.key("eventTime")
    records[0].should.have.key("s3")
    records[0]["s3"].should.have.key("bucket")
    records[0]["s3"]["bucket"].should.have.key("arn").equals(
        f"arn:aws:s3:::{bucket_name}"
    )
    records[0]["s3"]["bucket"].should.have.key("name").equals(bucket_name)
    records[0]["s3"].should.have.key("configurationId").equals("queue_config")
    records[0]["s3"].should.have.key("object")
    records[0]["s3"]["object"].should.have.key("eTag").equals(
        "61ea96c3c8d2c76fc5a42bfccb6affd9"
    )
    records[0]["s3"]["object"].should.have.key("key").equals("key2")
    records[0]["s3"]["object"].should.have.key("size").equals(15)


@mock_s3
@mock_sqs
def test_object_put__sends_to_queue__using_filter():
    s3_res = boto3.resource("s3", region_name=REGION_NAME)
    s3_client = boto3.client("s3", region_name=REGION_NAME)
    sqs = boto3.resource("sqs", region_name=REGION_NAME)

    # Create S3 bucket
    bucket_name = str(uuid4())
    s3_res.create_bucket(Bucket=bucket_name)

    # Create SQS queue
    queue = sqs.create_queue(QueueName=f"{str(uuid4())[0:6]}")
    queue_arn = queue.attributes["QueueArn"]

    # Put Notification
    s3_client.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration={
            "QueueConfigurations": [
                {
                    "Id": "prefixed",
                    "QueueArn": queue_arn,
                    "Events": ["s3:ObjectCreated:Put"],
                    "Filter": {
                        "Key": {"FilterRules": [{"Name": "prefix", "Value": "aa"}]}
                    },
                },
                {
                    "Id": "images_only",
                    "QueueArn": queue_arn,
                    "Events": ["s3:ObjectCreated:Put"],
                    "Filter": {
                        "Key": {
                            "FilterRules": [
                                {"Name": "prefix", "Value": "image/"},
                                {"Name": "suffix", "Value": "jpg"},
                            ]
                        }
                    },
                },
            ]
        },
    )

    # Read the test-event
    resp = queue.receive_messages()
    [m.delete() for m in resp]

    # Create an Object that does not meet any filter
    s3_client.put_object(Bucket=bucket_name, Key="bb", Body="sth")
    messages = queue.receive_messages()
    messages.should.have.length_of(0)
    [m.delete() for m in messages]

    # Create an Object that does meet the filter - using the prefix only
    s3_client.put_object(Bucket=bucket_name, Key="aafilter", Body="sth")
    messages = queue.receive_messages()
    messages.should.have.length_of(1)
    [m.delete() for m in messages]

    # Create an Object that does meet the filter - using the prefix + suffix
    s3_client.put_object(Bucket=bucket_name, Key="image/yes.jpg", Body="img")
    messages = queue.receive_messages()
    messages.should.have.length_of(1)
    [m.delete() for m in messages]

    # Create an Object that does not meet the filter - only the prefix
    s3_client.put_object(Bucket=bucket_name, Key="image/no.gif", Body="img")
    messages = queue.receive_messages()
    messages.should.have.length_of(0)
    [m.delete() for m in messages]

    # Create an Object that does not meet the filter - only the suffix
    s3_client.put_object(Bucket=bucket_name, Key="nonimages/yes.jpg", Body="img")
    messages = queue.receive_messages()
    messages.should.have.length_of(0)
    [m.delete() for m in messages]
