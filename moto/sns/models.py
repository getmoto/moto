from __future__ import unicode_literals

import datetime
import uuid

import boto.sns
import requests
import six

from moto.compat import OrderedDict
from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.sqs import sqs_backends
from .utils import make_arn_for_topic, make_arn_for_subscription

DEFAULT_ACCOUNT_ID = 123456789012
DEFAULT_PAGE_SIZE = 100


class Topic(object):
    def __init__(self, name, sns_backend):
        self.name = name
        self.sns_backend = sns_backend
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
        message_id = six.text_type(uuid.uuid4())
        subscriptions, _ = self.sns_backend.list_subscriptions(self.arn)
        for subscription in subscriptions:
            subscription.publish(message, message_id)
        return message_id

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'TopicName':
            return self.name
        raise UnformattedGetAttTemplateException()

    @property
    def physical_resource_id(self):
        return self.arn

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        sns_backend = sns_backends[region_name]
        properties = cloudformation_json['Properties']

        topic = sns_backend.create_topic(
            properties.get("TopicName")
        )
        for subscription in properties.get("Subscription", []):
            sns_backend.subscribe(topic.arn, subscription['Endpoint'], subscription['Protocol'])
        return topic


class Subscription(object):
    def __init__(self, topic, endpoint, protocol):
        self.topic = topic
        self.endpoint = endpoint
        self.protocol = protocol
        self.arn = make_arn_for_subscription(self.topic.arn)

    def publish(self, message, message_id):
        if self.protocol == 'sqs':
            queue_name = self.endpoint.split(":")[-1]
            region = self.endpoint.split(":")[3]
            sqs_backends[region].send_message(queue_name, message)
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
            "Timestamp": iso_8601_datetime_with_milliseconds(datetime.datetime.now()),
            "SignatureVersion": "1",
            "Signature": "EXAMPLElDMXvB8r9R83tGoNn0ecwd5UjllzsvSvbItzfaMpN2nk5HVSw7XnOn/49IkxDKz8YrlH2qJXj2iZB0Zo2O71c4qQk1fMUDi3LGpij7RCW7AW9vYYsSqIKRnFS94ilu7NFhUzLiieYr4BKHpdTmdD6c0esKEYBpabxDSc=",
            "SigningCertURL": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem",
            "UnsubscribeURL": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123456789012:some-topic:2bcfbf39-05c3-41de-beaa-fcfcc21c8f55"
        }


class SNSBackend(BaseBackend):
    def __init__(self):
        self.topics = OrderedDict()
        self.subscriptions = OrderedDict()

    def create_topic(self, name):
        topic = Topic(name, self)
        self.topics[topic.arn] = topic
        return topic

    def _get_values_nexttoken(self, values_map, next_token=None):
        if next_token is None:
            next_token = 0
        next_token = int(next_token)
        values = list(values_map.values())[next_token: next_token + DEFAULT_PAGE_SIZE]
        if len(values) == DEFAULT_PAGE_SIZE:
            next_token = next_token + DEFAULT_PAGE_SIZE
        else:
            next_token = None
        return values, next_token

    def list_topics(self, next_token=None):
        return self._get_values_nexttoken(self.topics, next_token)

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

    def list_subscriptions(self, topic_arn=None, next_token=None):
        if topic_arn:
            topic = self.get_topic(topic_arn)
            filtered = OrderedDict([(k, sub) for k, sub in self.subscriptions.items() if sub.topic == topic])
            return self._get_values_nexttoken(filtered, next_token)
        else:
            return self._get_values_nexttoken(self.subscriptions, next_token)

    def publish(self, topic_arn, message):
        topic = self.get_topic(topic_arn)
        message_id = topic.publish(message)
        return message_id

sns_backends = {}
for region in boto.sns.regions():
    sns_backends[region.name] = SNSBackend()


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
