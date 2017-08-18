from __future__ import unicode_literals
from six.moves.urllib.parse import parse_qs

import boto
from freezegun import freeze_time
import sure  # noqa

from moto.packages.responses import responses
from moto import mock_sns_deprecated, mock_sqs_deprecated


MESSAGE_FROM_SQS_TEMPLATE = '{\n  "Message": "%s",\n  "MessageId": "%s",\n  "Signature": "EXAMPLElDMXvB8r9R83tGoNn0ecwd5UjllzsvSvbItzfaMpN2nk5HVSw7XnOn/49IkxDKz8YrlH2qJXj2iZB0Zo2O71c4qQk1fMUDi3LGpij7RCW7AW9vYYsSqIKRnFS94ilu7NFhUzLiieYr4BKHpdTmdD6c0esKEYBpabxDSc=",\n  "SignatureVersion": "1",\n  "SigningCertURL": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem",\n  "Subject": "my subject",\n  "Timestamp": "2015-01-01T12:00:00.000Z",\n  "TopicArn": "arn:aws:sns:%s:123456789012:some-topic",\n  "Type": "Notification",\n  "UnsubscribeURL": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123456789012:some-topic:2bcfbf39-05c3-41de-beaa-fcfcc21c8f55"\n}'


@mock_sqs_deprecated
@mock_sns_deprecated
def test_publish_to_sqs():
    conn = boto.connect_sns()
    conn.create_topic("some-topic")
    topics_json = conn.get_all_topics()
    topic_arn = topics_json["ListTopicsResponse"][
        "ListTopicsResult"]["Topics"][0]['TopicArn']

    sqs_conn = boto.connect_sqs()
    sqs_conn.create_queue("test-queue")

    conn.subscribe(topic_arn, "sqs",
                   "arn:aws:sqs:us-east-1:123456789012:test-queue")

    message_to_publish = 'my message'
    with freeze_time("2015-01-01 12:00:00"):
        published_message = conn.publish(topic=topic_arn, message=message_to_publish)
    published_message_id = published_message['PublishResponse']['PublishResult']['MessageId']

    queue = sqs_conn.get_queue("test-queue")
    message = queue.read(1)
    expected = MESSAGE_FROM_SQS_TEMPLATE  % (message_to_publish, published_message_id, 'us-east-1')
    message.get_body().should.equal(expected)


@mock_sqs_deprecated
@mock_sns_deprecated
def test_publish_to_sqs_in_different_region():
    conn = boto.sns.connect_to_region("us-west-1")
    conn.create_topic("some-topic")
    topics_json = conn.get_all_topics()
    topic_arn = topics_json["ListTopicsResponse"][
        "ListTopicsResult"]["Topics"][0]['TopicArn']

    sqs_conn = boto.sqs.connect_to_region("us-west-2")
    sqs_conn.create_queue("test-queue")

    conn.subscribe(topic_arn, "sqs",
                   "arn:aws:sqs:us-west-2:123456789012:test-queue")

    message_to_publish = 'my message'
    with freeze_time("2015-01-01 12:00:00"):
        published_message = conn.publish(topic=topic_arn, message=message_to_publish)
    published_message_id = published_message['PublishResponse']['PublishResult']['MessageId']

    queue = sqs_conn.get_queue("test-queue")
    message = queue.read(1)
    expected = MESSAGE_FROM_SQS_TEMPLATE  % (message_to_publish, published_message_id, 'us-west-1')
    message.get_body().should.equal(expected)
