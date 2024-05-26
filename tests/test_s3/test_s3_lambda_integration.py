import json
from uuid import uuid4

import boto3
import pytest

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests.markers import requires_docker
from tests.test_awslambda.utilities import (
    get_role_name,
    get_test_zip_file_print_event,
    wait_for_log_msg,
)

REGION_NAME = "us-east-1"


@mock_aws
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
        Runtime="python3.11",
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

    assert len(records) == 1
    assert records[0]["awsRegion"] == REGION_NAME
    assert records[0]["eventName"] == actual_event
    assert records[0]["eventSource"] == "aws:s3"
    assert "eventTime" in records[0]
    assert "s3" in records[0]
    assert "bucket" in records[0]["s3"]
    assert records[0]["s3"]["bucket"]["arn"] == f"arn:aws:s3:::{bucket_name}"
    assert records[0]["s3"]["bucket"]["name"] == bucket_name
    assert records[0]["s3"]["configurationId"] == "s3eventtriggerslambda"
    assert "object" in records[0]["s3"]
    assert records[0]["s3"]["object"]["eTag"] == "61ea96c3c8d2c76fc5a42bfccb6affd9"
    assert records[0]["s3"]["object"]["key"] == "keyname"
    assert records[0]["s3"]["object"]["size"] == 15


@mock_aws
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
    assert resp["ContentLength"] == 15
    assert resp["Body"].read() == b"bodyofnewobject"


@mock_aws
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
    assert len(messages) == 1
    message = json.loads(messages[0]["Body"])
    assert message["Service"] == "Amazon S3"
    assert message["Event"] == "s3:TestEvent"
    assert "Time" in message
    assert message["Bucket"] == bucket_name

    # Copy an Object
    s3_client.put_object(Bucket=bucket_name, Key="keyname", Body="bodyofnewobject")
    s3_client.copy_object(
        Bucket=bucket_name, CopySource=f"{bucket_name}/keyname", Key="key2"
    )

    # Read SQS messages - we should have the Copy-event here
    resp = sqs_client.receive_message(QueueUrl=queue_url)
    assert len(resp["Messages"]) == 1
    records = json.loads(resp["Messages"][0]["Body"])["Records"]

    assert len(records) == 1
    assert records[0]["awsRegion"] == REGION_NAME
    assert records[0]["eventName"] == "ObjectCreated:Copy"
    assert records[0]["eventSource"] == "aws:s3"
    assert "eventTime" in records[0]
    assert "s3" in records[0]
    assert "bucket" in records[0]["s3"]
    assert records[0]["s3"]["bucket"]["arn"] == f"arn:aws:s3:::{bucket_name}"
    assert records[0]["s3"]["bucket"]["name"] == bucket_name
    assert records[0]["s3"]["configurationId"] == "queue_config"
    assert "object" in records[0]["s3"]
    assert records[0]["s3"]["object"]["eTag"] == "61ea96c3c8d2c76fc5a42bfccb6affd9"
    assert records[0]["s3"]["object"]["key"] == "key2"
    assert records[0]["s3"]["object"]["size"] == 15


@mock_aws
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
    _ = [m.delete() for m in resp]

    # Create an Object that does not meet any filter
    s3_client.put_object(Bucket=bucket_name, Key="bb", Body="sth")
    messages = queue.receive_messages()
    assert not messages
    _ = [m.delete() for m in messages]

    # Create an Object that does meet the filter - using the prefix only
    s3_client.put_object(Bucket=bucket_name, Key="aafilter", Body="sth")
    messages = queue.receive_messages()
    assert len(messages) == 1
    _ = [m.delete() for m in messages]

    # Create an Object that does meet the filter - using the prefix + suffix
    s3_client.put_object(Bucket=bucket_name, Key="image/yes.jpg", Body="img")
    messages = queue.receive_messages()
    assert len(messages) == 1
    _ = [m.delete() for m in messages]

    # Create an Object that does not meet the filter - only the prefix
    s3_client.put_object(Bucket=bucket_name, Key="image/no.gif", Body="img")
    messages = queue.receive_messages()
    assert not messages
    _ = [m.delete() for m in messages]

    # Create an Object that does not meet the filter - only the suffix
    s3_client.put_object(Bucket=bucket_name, Key="nonimages/yes.jpg", Body="img")
    messages = queue.receive_messages()
    assert not messages
    _ = [m.delete() for m in messages]


@mock_aws
@pytest.mark.parametrize(
    "region,partition", [("us-west-2", "aws"), ("cn-north-1", "aws-cn")]
)
def test_put_bucket_notification_sns_sqs(region, partition):
    s3_client = boto3.client("s3", region_name=region)
    s3_client.create_bucket(
        Bucket="bucket", CreateBucketConfiguration={"LocationConstraint": region}
    )

    sqs_client = boto3.client("sqs", region_name=region)
    sqs_queue = sqs_client.create_queue(QueueName="queue")
    sqs_queue_arn = sqs_client.get_queue_attributes(
        QueueUrl=sqs_queue["QueueUrl"], AttributeNames=["QueueArn"]
    )

    sns_client = boto3.client("sns", region_name=region)
    sns_topic = sns_client.create_topic(Name="topic")

    # Subscribe SQS queue to SNS topic
    sns_client.subscribe(
        TopicArn=sns_topic["TopicArn"],
        Protocol="sqs",
        Endpoint=sqs_queue_arn["Attributes"]["QueueArn"],
    )

    # Set S3 to send ObjectCreated to SNS
    s3_client.put_bucket_notification_configuration(
        Bucket="bucket",
        NotificationConfiguration={
            "TopicConfigurations": [
                {
                    "Id": "SomeID",
                    "TopicArn": sns_topic["TopicArn"],
                    "Events": ["s3:ObjectCreated:*"],
                }
            ]
        },
    )

    # We should receive a test message
    messages = sqs_client.receive_message(
        QueueUrl=sqs_queue["QueueUrl"], MaxNumberOfMessages=10
    )
    assert len(messages["Messages"]) == 1

    sqs_client.delete_message(
        QueueUrl=sqs_queue["QueueUrl"],
        ReceiptHandle=messages["Messages"][0]["ReceiptHandle"],
    )

    message_body = messages["Messages"][0]["Body"]
    sns_message = json.loads(message_body)
    assert sns_message["Type"] == "Notification"

    # Get S3 notification from SNS message
    s3_message_body = json.loads(sns_message["Message"])
    assert s3_message_body["Event"] == "s3:TestEvent"

    # Upload file to trigger notification
    s3_client.put_object(Bucket="bucket", Key="myfile", Body=b"asdf1324")

    # Verify queue not empty
    messages = sqs_client.receive_message(
        QueueUrl=sqs_queue["QueueUrl"], MaxNumberOfMessages=10
    )
    assert len(messages["Messages"]) == 1

    # Get SNS message from SQS
    message_body = messages["Messages"][0]["Body"]
    sns_message = json.loads(message_body)
    assert sns_message["Type"] == "Notification"

    # Get S3 notification from SNS message
    s3_message_body = json.loads(sns_message["Message"])
    assert s3_message_body["Records"][0]["eventName"] == "ObjectCreated:Put"
    assert s3_message_body["Records"][0]["awsRegion"] == region
    assert (
        s3_message_body["Records"][0]["s3"]["bucket"]["arn"]
        == f"arn:{partition}:s3:::bucket"
    )


@mock_aws
def test_put_bucket_notification_sns_error():
    s3_client = boto3.client("s3", region_name=REGION_NAME)
    s3_client.create_bucket(Bucket="bucket")

    # Set S3 to send ObjectCreated to SNS
    s3_client.put_bucket_notification_configuration(
        Bucket="bucket",
        NotificationConfiguration={
            "TopicConfigurations": [
                {
                    "Id": "SomeID",
                    "TopicArn": "arn:aws:sns:us-east-1:012345678910:notexistingtopic",
                    "Events": ["s3:ObjectCreated:*"],
                }
            ]
        },
    )

    # This should not throw an exception
    s3_client.put_object(Bucket="bucket", Key="myfile", Body=b"asdf1324")
