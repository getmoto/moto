import boto3
import json

from moto import mock_s3, mock_sqs, mock_sns
from moto.s3.responses import DEFAULT_REGION_NAME


@mock_s3
@mock_sns
@mock_sqs
def test_put_bucket_notification_sns_sqs():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="bucket")

    sqs_client = boto3.client("sqs", region_name=DEFAULT_REGION_NAME)
    sqs_queue = sqs_client.create_queue(QueueName="queue")
    sqs_queue_arn = sqs_client.get_queue_attributes(
        QueueUrl=sqs_queue["QueueUrl"], AttributeNames=["QueueArn"]
    )

    sns_client = boto3.client("sns", region_name=DEFAULT_REGION_NAME)
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


@mock_s3
def test_put_bucket_notification_sns_error():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
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
