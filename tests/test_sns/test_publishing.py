from __future__ import unicode_literals
from six.moves.urllib.parse import parse_qs

import boto
from freezegun import freeze_time
import httpretty
import sure  # noqa

from moto import mock_sns, mock_sqs


@mock_sqs
@mock_sns
def test_publish_to_sqs():
    conn = boto.connect_sns()
    conn.create_topic("some-topic")
    topics_json = conn.get_all_topics()
    topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0]['TopicArn']

    sqs_conn = boto.connect_sqs()
    sqs_conn.create_queue("test-queue")

    conn.subscribe(topic_arn, "sqs", "arn:aws:sqs:us-east-1:123456789012:test-queue")

    conn.publish(topic=topic_arn, message="my message")

    queue = sqs_conn.get_queue("test-queue")
    message = queue.read(1)
    message.get_body().should.equal('my message')


@mock_sqs
@mock_sns
def test_publish_to_sqs_in_different_region():
    conn = boto.sns.connect_to_region("us-west-1")
    conn.create_topic("some-topic")
    topics_json = conn.get_all_topics()
    topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0]['TopicArn']

    sqs_conn = boto.sqs.connect_to_region("us-west-2")
    sqs_conn.create_queue("test-queue")

    conn.subscribe(topic_arn, "sqs", "arn:aws:sqs:us-west-2:123456789012:test-queue")

    conn.publish(topic=topic_arn, message="my message")

    queue = sqs_conn.get_queue("test-queue")
    message = queue.read(1)
    message.get_body().should.equal('my message')


@freeze_time("2013-01-01")
@mock_sns
def test_publish_to_http():
    httpretty.HTTPretty.register_uri(
        method="POST",
        uri="http://example.com/foobar",
    )

    conn = boto.connect_sns()
    conn.create_topic("some-topic")
    topics_json = conn.get_all_topics()
    topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0]['TopicArn']

    conn.subscribe(topic_arn, "http", "http://example.com/foobar")

    response = conn.publish(topic=topic_arn, message="my message", subject="my subject")
    message_id = response['PublishResponse']['PublishResult']['MessageId']

    last_request = httpretty.last_request()
    last_request.method.should.equal("POST")
    parse_qs(last_request.body.decode('utf-8')).should.equal({
        "Type": ["Notification"],
        "MessageId": [message_id],
        "TopicArn": ["arn:aws:sns:{0}:123456789012:some-topic".format(conn.region.name)],
        "Subject": ["my subject"],
        "Message": ["my message"],
        "Timestamp": ["2013-01-01T00:00:00.000Z"],
        "SignatureVersion": ["1"],
        "Signature": ["EXAMPLElDMXvB8r9R83tGoNn0ecwd5UjllzsvSvbItzfaMpN2nk5HVSw7XnOn/49IkxDKz8YrlH2qJXj2iZB0Zo2O71c4qQk1fMUDi3LGpij7RCW7AW9vYYsSqIKRnFS94ilu7NFhUzLiieYr4BKHpdTmdD6c0esKEYBpabxDSc="],
        "SigningCertURL": ["https://sns.us-east-1.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem"],
        "UnsubscribeURL": ["https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123456789012:some-topic:2bcfbf39-05c3-41de-beaa-fcfcc21c8f55"],
    })
