from __future__ import unicode_literals

import json

from six.moves.urllib.parse import parse_qs

import boto3
import re
from freezegun import freeze_time
import sure  # noqa

from moto.packages.responses import responses
from moto import mock_sns, mock_sqs
from freezegun import freeze_time


MESSAGE_FROM_SQS_TEMPLATE = '{\n  "Message": "%s",\n  "MessageId": "%s",\n  "Signature": "EXAMPLElDMXvB8r9R83tGoNn0ecwd5UjllzsvSvbItzfaMpN2nk5HVSw7XnOn/49IkxDKz8YrlH2qJXj2iZB0Zo2O71c4qQk1fMUDi3LGpij7RCW7AW9vYYsSqIKRnFS94ilu7NFhUzLiieYr4BKHpdTmdD6c0esKEYBpabxDSc=",\n  "SignatureVersion": "1",\n  "SigningCertURL": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem",\n  "Subject": "my subject",\n  "Timestamp": "2015-01-01T12:00:00.000Z",\n  "TopicArn": "arn:aws:sns:%s:123456789012:some-topic",\n  "Type": "Notification",\n  "UnsubscribeURL": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123456789012:some-topic:2bcfbf39-05c3-41de-beaa-fcfcc21c8f55"\n}'


@mock_sqs
@mock_sns
def test_publish_to_sqs():
    conn = boto3.client('sns', region_name='us-east-1')
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]['TopicArn']

    sqs_conn = boto3.resource('sqs', region_name='us-east-1')
    sqs_conn.create_queue(QueueName="test-queue")

    conn.subscribe(TopicArn=topic_arn,
                   Protocol="sqs",
                   Endpoint="arn:aws:sqs:us-east-1:123456789012:test-queue")
    message = 'my message'
    with freeze_time("2015-01-01 12:00:00"):
        published_message = conn.publish(TopicArn=topic_arn, Message=message)
    published_message_id = published_message['MessageId']

    queue = sqs_conn.get_queue_by_name(QueueName="test-queue")
    messages = queue.receive_messages(MaxNumberOfMessages=1)
    expected = MESSAGE_FROM_SQS_TEMPLATE  % (message, published_message_id, 'us-east-1')
    acquired_message = re.sub("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", u'2015-01-01T12:00:00.000Z', messages[0].body)
    acquired_message.should.equal(expected)


@mock_sqs
@mock_sns
def test_publish_to_sqs_dump_json():
    conn = boto3.client('sns', region_name='us-east-1')
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]['TopicArn']

    sqs_conn = boto3.resource('sqs', region_name='us-east-1')
    sqs_conn.create_queue(QueueName="test-queue")

    conn.subscribe(TopicArn=topic_arn,
                   Protocol="sqs",
                   Endpoint="arn:aws:sqs:us-east-1:123456789012:test-queue")

    message = json.dumps({
        "Records": [{
            "eventVersion": "2.0",
            "eventSource": "aws:s3",
            "s3": {
                "s3SchemaVersion": "1.0"
            }
        }]
    }, sort_keys=True)
    with freeze_time("2015-01-01 12:00:00"):
        published_message = conn.publish(TopicArn=topic_arn, Message=message)
    published_message_id = published_message['MessageId']

    queue = sqs_conn.get_queue_by_name(QueueName="test-queue")
    messages = queue.receive_messages(MaxNumberOfMessages=1)

    escaped = message.replace('"', '\\"')
    expected = MESSAGE_FROM_SQS_TEMPLATE  % (escaped, published_message_id, 'us-east-1')
    acquired_message = re.sub("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", u'2015-01-01T12:00:00.000Z', messages[0].body)
    acquired_message.should.equal(expected)


@mock_sqs
@mock_sns
def test_publish_to_sqs_in_different_region():
    conn = boto3.client('sns', region_name='us-west-1')
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]['TopicArn']

    sqs_conn = boto3.resource('sqs', region_name='us-west-2')
    sqs_conn.create_queue(QueueName="test-queue")

    conn.subscribe(TopicArn=topic_arn,
                   Protocol="sqs",
                   Endpoint="arn:aws:sqs:us-west-2:123456789012:test-queue")

    message = 'my message'
    with freeze_time("2015-01-01 12:00:00"):
        published_message = conn.publish(TopicArn=topic_arn, Message=message)
    published_message_id = published_message['MessageId']

    queue = sqs_conn.get_queue_by_name(QueueName="test-queue")
    messages = queue.receive_messages(MaxNumberOfMessages=1)
    expected = MESSAGE_FROM_SQS_TEMPLATE  % (message, published_message_id, 'us-west-1')
    acquired_message = re.sub("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", u'2015-01-01T12:00:00.000Z', messages[0].body)
    acquired_message.should.equal(expected)


@freeze_time("2013-01-01")
@mock_sns
def test_publish_to_http():
    def callback(request):
        request.headers["Content-Type"].should.equal("application/json")
        json.loads.when.called_with(request.body).should_not.throw(Exception)
        return 200, {}, ""

    responses.add_callback(
        method="POST",
        url="http://example.com/foobar",
        callback=callback,
    )

    conn = boto3.client('sns', region_name='us-east-1')
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]['TopicArn']

    conn.subscribe(TopicArn=topic_arn,
                   Protocol="http",
                   Endpoint="http://example.com/foobar")

    response = conn.publish(
        TopicArn=topic_arn, Message="my message", Subject="my subject")
    message_id = response['MessageId']
