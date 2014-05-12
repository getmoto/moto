import datetime
import requests
import uuid

from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime
from moto.sqs.models import sqs_backend
from .utils import make_arn_for_topic, make_arn_for_subscription

DEFAULT_ACCOUNT_ID = 123456789012


class Topic(object):
    def __init__(self, name):
        self.name = name
        self.account_id = DEFAULT_ACCOUNT_ID
        self.display_name = ""
        self.policy = DEFAULT_TOPIC_POLICY
        self.delivery_policy = ""
        self.effective_delivery_policy = DEFAULT_EFFECTIVE_DELIVERY_POLICY
        self.arn = make_arn_for_topic(self.account_id, name)

        self.subscriptions_pending = 0
        self.subscriptions_confimed = 0
        self.subscriptions_deleted = 0

    def publish(self, message):
        message_id = unicode(uuid.uuid4())
        subscriptions = sns_backend.list_subscriptions(self.arn)
        for subscription in subscriptions:
            subscription.publish(message, message_id)
        return message_id


class Subscription(object):
    def __init__(self, topic, endpoint, protocol):
        self.topic = topic
        self.endpoint = endpoint
        self.protocol = protocol
        self.arn = make_arn_for_subscription(self.topic.arn)

    def publish(self, message, message_id):
        if self.protocol == 'sqs':
            queue_name = self.endpoint.split(":")[-1]
            sqs_backend.send_message(queue_name, message)
        elif self.protocol in ['http', 'https']:
            post_data = self.get_post_data(message, message_id)
            requests.post(self.endpoint, data=post_data)

    def get_post_data(self, message, message_id):
        return {
            "Type": "Notification",
            "MessageId": message_id,
            "TopicArn": self.topic.arn,
            "Subject": "my subject",
            "Message": message,
            "Timestamp": iso_8601_datetime(datetime.datetime.now()),
            "SignatureVersion": "1",
            "Signature": "EXAMPLElDMXvB8r9R83tGoNn0ecwd5UjllzsvSvbItzfaMpN2nk5HVSw7XnOn/49IkxDKz8YrlH2qJXj2iZB0Zo2O71c4qQk1fMUDi3LGpij7RCW7AW9vYYsSqIKRnFS94ilu7NFhUzLiieYr4BKHpdTmdD6c0esKEYBpabxDSc=",
            "SigningCertURL": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem",
            "UnsubscribeURL": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123456789012:some-topic:2bcfbf39-05c3-41de-beaa-fcfcc21c8f55"
        }


class SNSBackend(BaseBackend):
    def __init__(self):
        self.topics = {}
        self.subscriptions = {}

    def create_topic(self, name):
        topic = Topic(name)
        self.topics[topic.arn] = topic
        return topic

    def list_topics(self):
        return self.topics.values()

    def delete_topic(self, arn):
        self.topics.pop(arn)

    def get_topic(self, arn):
        return self.topics[arn]

    def set_topic_attribute(self, topic_arn, attribute_name, attribute_value):
        topic = self.get_topic(topic_arn)
        setattr(topic, attribute_name, attribute_value)

    def subscribe(self, topic_arn, endpoint, protocol):
        topic = self.get_topic(topic_arn)
        subscription = Subscription(topic, endpoint, protocol)
        self.subscriptions[subscription.arn] = subscription
        return subscription

    def unsubscribe(self, subscription_arn):
        self.subscriptions.pop(subscription_arn)

    def list_subscriptions(self, topic_arn=None):
        if topic_arn:
            topic = self.get_topic(topic_arn)
            return [sub for sub in self.subscriptions.values() if sub.topic == topic]
        else:
            return self.subscriptions.values()

    def publish(self, topic_arn, message):
        topic = self.get_topic(topic_arn)
        message_id = topic.publish(message)
        return message_id


sns_backend = SNSBackend()


DEFAULT_TOPIC_POLICY = {
    "Version": "2008-10-17",
    "Id": "us-east-1/698519295917/test__default_policy_ID",
    "Statement": [{
        "Effect": "Allow",
        "Sid": "us-east-1/698519295917/test__default_statement_ID",
        "Principal": {
            "AWS": "*"
        },
        "Action": [
            "SNS:GetTopicAttributes",
            "SNS:SetTopicAttributes",
            "SNS:AddPermission",
            "SNS:RemovePermission",
            "SNS:DeleteTopic",
            "SNS:Subscribe",
            "SNS:ListSubscriptionsByTopic",
            "SNS:Publish",
            "SNS:Receive",
        ],
        "Resource": "arn:aws:sns:us-east-1:698519295917:test",
        "Condition": {
            "StringLike": {
                "AWS:SourceArn": "arn:aws:*:*:698519295917:*"
            }
        }
    }]
}

DEFAULT_EFFECTIVE_DELIVERY_POLICY = {
    'http': {
        'disableSubscriptionOverrides': False,
        'defaultHealthyRetryPolicy': {
            'numNoDelayRetries': 0,
            'numMinDelayRetries': 0,
            'minDelayTarget': 20,
            'maxDelayTarget': 20,
            'numMaxDelayRetries': 0,
            'numRetries': 3,
            'backoffFunction': 'linear'
        }
    }
}
