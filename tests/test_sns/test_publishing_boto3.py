from __future__ import unicode_literals
from six.moves.urllib.parse import parse_qs

import boto3
from freezegun import freeze_time
import sure  # noqa

from moto.packages.responses import responses
from moto import mock_sns, mock_sqs


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

    conn.publish(TopicArn=topic_arn, Message="my message")

    queue = sqs_conn.get_queue_by_name(QueueName="test-queue")
    messages = queue.receive_messages(MaxNumberOfMessages=1)
    messages[0].body.should.equal('my message')


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

    conn.publish(TopicArn=topic_arn, Message="my message")

    queue = sqs_conn.get_queue_by_name(QueueName="test-queue")
    messages = queue.receive_messages(MaxNumberOfMessages=1)
    messages[0].body.should.equal('my message')


@freeze_time("2013-01-01")
@mock_sns
def test_publish_to_http():
    responses.add(
        method="POST",
        url="http://example.com/foobar",
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
