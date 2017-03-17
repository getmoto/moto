from __future__ import unicode_literals

import datetime
import uuid
import json

import boto.sns
import requests
import six

from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.sqs import sqs_backends
from .exceptions import (
    SNSNotFoundError, DuplicateSnsEndpointError, SnsEndpointDisabled
)
from .utils import make_arn_for_topic, make_arn_for_subscription

DEFAULT_ACCOUNT_ID = 123456789012
DEFAULT_PAGE_SIZE = 100


class Topic(BaseModel):

    def __init__(self, name, sns_backend):
        self.name = name
        self.sns_backend = sns_backend
        self.account_id = DEFAULT_ACCOUNT_ID
        self.display_name = ""
        self.policy = json.dumps(DEFAULT_TOPIC_POLICY)
        self.delivery_policy = ""
        self.effective_delivery_policy = json.dumps(DEFAULT_EFFECTIVE_DELIVERY_POLICY)
        self.arn = make_arn_for_topic(
            self.account_id, name, sns_backend.region_name)

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
            sns_backend.subscribe(topic.arn, subscription[
                                  'Endpoint'], subscription['Protocol'])
        return topic


class Subscription(BaseModel):

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
            "Timestamp": iso_8601_datetime_with_milliseconds(datetime.datetime.utcnow()),
            "SignatureVersion": "1",
            "Signature": "EXAMPLElDMXvB8r9R83tGoNn0ecwd5UjllzsvSvbItzfaMpN2nk5HVSw7XnOn/49IkxDKz8YrlH2qJXj2iZB0Zo2O71c4qQk1fMUDi3LGpij7RCW7AW9vYYsSqIKRnFS94ilu7NFhUzLiieYr4BKHpdTmdD6c0esKEYBpabxDSc=",
            "SigningCertURL": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem",
            "UnsubscribeURL": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123456789012:some-topic:2bcfbf39-05c3-41de-beaa-fcfcc21c8f55"
        }


class PlatformApplication(BaseModel):

    def __init__(self, region, name, platform, attributes):
        self.region = region
        self.name = name
        self.platform = platform
        self.attributes = attributes

    @property
    def arn(self):
        return "arn:aws:sns:{region}:123456789012:app/{platform}/{name}".format(
            region=self.region,
            platform=self.platform,
            name=self.name,
        )


class PlatformEndpoint(BaseModel):

    def __init__(self, region, application, custom_user_data, token, attributes):
        self.region = region
        self.application = application
        self.custom_user_data = custom_user_data
        self.token = token
        self.attributes = attributes
        self.id = uuid.uuid4()
        self.messages = OrderedDict()
        self.__fixup_attributes()

    def __fixup_attributes(self):
        # When AWS returns the attributes dict, it always contains these two elements, so we need to
        # automatically ensure they exist as well.
        if 'Token' not in self.attributes:
            self.attributes['Token'] = self.token
        if 'Enabled' not in self.attributes:
            self.attributes['Enabled'] = True

    @property
    def enabled(self):
        return json.loads(self.attributes.get('Enabled', 'true').lower())

    @property
    def arn(self):
        return "arn:aws:sns:{region}:123456789012:endpoint/{platform}/{name}/{id}".format(
            region=self.region,
            platform=self.application.platform,
            name=self.application.name,
            id=self.id,
        )

    def publish(self, message):
        if not self.enabled:
            raise SnsEndpointDisabled("Endpoint %s disabled" % self.id)

        # This is where we would actually send a message
        message_id = six.text_type(uuid.uuid4())
        self.messages[message_id] = message
        return message_id


class SNSBackend(BaseBackend):

    def __init__(self, region_name):
        super(SNSBackend, self).__init__()
        self.topics = OrderedDict()
        self.subscriptions = OrderedDict()
        self.applications = {}
        self.platform_endpoints = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_topic(self, name):
        topic = Topic(name, self)
        self.topics[topic.arn] = topic
        return topic

    def _get_values_nexttoken(self, values_map, next_token=None):
        if next_token is None:
            next_token = 0
        next_token = int(next_token)
        values = list(values_map.values())[
            next_token: next_token + DEFAULT_PAGE_SIZE]
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
        try:
            return self.topics[arn]
        except KeyError:
            raise SNSNotFoundError("Topic with arn {0} not found".format(arn))

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
            filtered = OrderedDict(
                [(k, sub) for k, sub in self.subscriptions.items() if sub.topic == topic])
            return self._get_values_nexttoken(filtered, next_token)
        else:
            return self._get_values_nexttoken(self.subscriptions, next_token)

    def publish(self, arn, message):
        try:
            topic = self.get_topic(arn)
            message_id = topic.publish(message)
        except SNSNotFoundError:
            endpoint = self.get_endpoint(arn)
            message_id = endpoint.publish(message)
        return message_id

    def create_platform_application(self, region, name, platform, attributes):
        application = PlatformApplication(region, name, platform, attributes)
        self.applications[application.arn] = application
        return application

    def get_application(self, arn):
        try:
            return self.applications[arn]
        except KeyError:
            raise SNSNotFoundError(
                "Application with arn {0} not found".format(arn))

    def set_application_attributes(self, arn, attributes):
        application = self.get_application(arn)
        application.attributes.update(attributes)
        return application

    def list_platform_applications(self):
        return self.applications.values()

    def delete_platform_application(self, platform_arn):
        self.applications.pop(platform_arn)

    def create_platform_endpoint(self, region, application, custom_user_data, token, attributes):
        if any(token == endpoint.token for endpoint in self.platform_endpoints.values()):
            raise DuplicateSnsEndpointError("Duplicate endpoint token: %s" % token)
        platform_endpoint = PlatformEndpoint(
            region, application, custom_user_data, token, attributes)
        self.platform_endpoints[platform_endpoint.arn] = platform_endpoint
        return platform_endpoint

    def list_endpoints_by_platform_application(self, application_arn):
        return [
            endpoint for endpoint
            in self.platform_endpoints.values()
            if endpoint.application.arn == application_arn
        ]

    def get_endpoint(self, arn):
        try:
            return self.platform_endpoints[arn]
        except KeyError:
            raise SNSNotFoundError(
                "Endpoint with arn {0} not found".format(arn))

    def set_endpoint_attributes(self, arn, attributes):
        endpoint = self.get_endpoint(arn)
        endpoint.attributes.update(attributes)
        return endpoint

    def delete_endpoint(self, arn):
        try:
            del self.platform_endpoints[arn]
        except KeyError:
            raise SNSNotFoundError(
                "Endpoint with arn {0} not found".format(arn))


sns_backends = {}
for region in boto.sns.regions():
    sns_backends[region.name] = SNSBackend(region.name)


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
