from __future__ import unicode_literals

import datetime
import uuid
import json

import requests
import six
import re

from boto3 import Session

from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel
from moto.core.utils import (
    iso_8601_datetime_with_milliseconds,
    camelcase_to_underscores,
)
from moto.sqs import sqs_backends
from moto.awslambda import lambda_backends

from .exceptions import (
    SNSNotFoundError,
    DuplicateSnsEndpointError,
    SnsEndpointDisabled,
    SNSInvalidParameter,
    InvalidParameterValue,
    InternalError,
    ResourceNotFoundError,
    TagLimitExceededError,
)
from .utils import make_arn_for_topic, make_arn_for_subscription, is_e164

from moto.core import ACCOUNT_ID as DEFAULT_ACCOUNT_ID

DEFAULT_PAGE_SIZE = 100
MAXIMUM_MESSAGE_LENGTH = 262144  # 256 KiB


class Topic(BaseModel):
    def __init__(self, name, sns_backend):
        self.name = name
        self.sns_backend = sns_backend
        self.account_id = DEFAULT_ACCOUNT_ID
        self.display_name = ""
        self.delivery_policy = ""
        self.effective_delivery_policy = json.dumps(DEFAULT_EFFECTIVE_DELIVERY_POLICY)
        self.arn = make_arn_for_topic(self.account_id, name, sns_backend.region_name)

        self.subscriptions_pending = 0
        self.subscriptions_confimed = 0
        self.subscriptions_deleted = 0

        self._policy_json = self._create_default_topic_policy(
            sns_backend.region_name, self.account_id, name
        )
        self._tags = {}

    def publish(self, message, subject=None, message_attributes=None):
        message_id = six.text_type(uuid.uuid4())
        subscriptions, _ = self.sns_backend.list_subscriptions(self.arn)
        for subscription in subscriptions:
            subscription.publish(
                message,
                message_id,
                subject=subject,
                message_attributes=message_attributes,
            )
        return message_id

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "TopicName":
            return self.name
        raise UnformattedGetAttTemplateException()

    @property
    def physical_resource_id(self):
        return self.arn

    @property
    def policy(self):
        return json.dumps(self._policy_json)

    @policy.setter
    def policy(self, policy):
        self._policy_json = json.loads(policy)

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        sns_backend = sns_backends[region_name]
        properties = cloudformation_json["Properties"]

        topic = sns_backend.create_topic(properties.get("TopicName"))
        for subscription in properties.get("Subscription", []):
            sns_backend.subscribe(
                topic.arn, subscription["Endpoint"], subscription["Protocol"]
            )
        return topic

    def _create_default_topic_policy(self, region_name, account_id, name):
        return {
            "Version": "2008-10-17",
            "Id": "__default_policy_ID",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Sid": "__default_statement_ID",
                    "Principal": {"AWS": "*"},
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
                    "Resource": make_arn_for_topic(self.account_id, name, region_name),
                    "Condition": {"StringEquals": {"AWS:SourceOwner": str(account_id)}},
                }
            ],
        }


class Subscription(BaseModel):
    def __init__(self, topic, endpoint, protocol):
        self.topic = topic
        self.endpoint = endpoint
        self.protocol = protocol
        self.arn = make_arn_for_subscription(self.topic.arn)
        self.attributes = {}
        self._filter_policy = None  # filter policy as a dict, not json.
        self.confirmed = False

    def publish(self, message, message_id, subject=None, message_attributes=None):
        if not self._matches_filter_policy(message_attributes):
            return

        if self.protocol == "sqs":
            queue_name = self.endpoint.split(":")[-1]
            region = self.endpoint.split(":")[3]
            if self.attributes.get("RawMessageDelivery") != "true":
                sqs_backends[region].send_message(
                    queue_name,
                    json.dumps(
                        self.get_post_data(
                            message,
                            message_id,
                            subject,
                            message_attributes=message_attributes,
                        ),
                        sort_keys=True,
                        indent=2,
                        separators=(",", ": "),
                    ),
                )
            else:
                raw_message_attributes = {}
                for key, value in message_attributes.items():
                    type = "string_value"
                    type_value = value["Value"]
                    if value["Type"].startswith("Binary"):
                        type = "binary_value"
                    elif value["Type"].startswith("Number"):
                        type_value = "{0:g}".format(value["Value"])

                    raw_message_attributes[key] = {
                        "data_type": value["Type"],
                        type: type_value,
                    }

                sqs_backends[region].send_message(
                    queue_name, message, message_attributes=raw_message_attributes
                )
        elif self.protocol in ["http", "https"]:
            post_data = self.get_post_data(message, message_id, subject)
            requests.post(
                self.endpoint,
                json=post_data,
                headers={"Content-Type": "text/plain; charset=UTF-8"},
            )
        elif self.protocol == "lambda":
            # TODO: support bad function name
            # http://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html
            arr = self.endpoint.split(":")
            region = arr[3]
            qualifier = None
            if len(arr) == 7:
                assert arr[5] == "function"
                function_name = arr[-1]
            elif len(arr) == 8:
                assert arr[5] == "function"
                qualifier = arr[-1]
                function_name = arr[-2]
            else:
                assert False

            lambda_backends[region].send_sns_message(
                function_name, message, subject=subject, qualifier=qualifier
            )

    def _matches_filter_policy(self, message_attributes):
        # TODO: support Anything-but matching, prefix matching and
        #       numeric value matching.
        if not self._filter_policy:
            return True

        if message_attributes is None:
            message_attributes = {}

        def _field_match(field, rules, message_attributes):
            for rule in rules:
                #  TODO: boolean value matching is not supported, SNS behavior unknown
                if isinstance(rule, six.string_types):
                    if field not in message_attributes:
                        return False
                    if message_attributes[field]["Value"] == rule:
                        return True
                    try:
                        json_data = json.loads(message_attributes[field]["Value"])
                        if rule in json_data:
                            return True
                    except (ValueError, TypeError):
                        pass
                if isinstance(rule, (six.integer_types, float)):
                    if field not in message_attributes:
                        return False
                    if message_attributes[field]["Type"] == "Number":
                        attribute_values = [message_attributes[field]["Value"]]
                    elif message_attributes[field]["Type"] == "String.Array":
                        try:
                            attribute_values = json.loads(
                                message_attributes[field]["Value"]
                            )
                            if not isinstance(attribute_values, list):
                                attribute_values = [attribute_values]
                        except (ValueError, TypeError):
                            return False
                    else:
                        return False

                    for attribute_values in attribute_values:
                        # Even the official documentation states a 5 digits of accuracy after the decimal point for numerics, in reality it is 6
                        # https://docs.aws.amazon.com/sns/latest/dg/sns-subscription-filter-policies.html#subscription-filter-policy-constraints
                        if int(attribute_values * 1000000) == int(rule * 1000000):
                            return True
                if isinstance(rule, dict):
                    keyword = list(rule.keys())[0]
                    attributes = list(rule.values())[0]
                    if keyword == "exists":
                        if attributes and field in message_attributes:
                            return True
                        elif not attributes and field not in message_attributes:
                            return True
            return False

        return all(
            _field_match(field, rules, message_attributes)
            for field, rules in six.iteritems(self._filter_policy)
        )

    def get_post_data(self, message, message_id, subject, message_attributes=None):
        post_data = {
            "Type": "Notification",
            "MessageId": message_id,
            "TopicArn": self.topic.arn,
            "Subject": subject or "my subject",
            "Message": message,
            "Timestamp": iso_8601_datetime_with_milliseconds(
                datetime.datetime.utcnow()
            ),
            "SignatureVersion": "1",
            "Signature": "EXAMPLElDMXvB8r9R83tGoNn0ecwd5UjllzsvSvbItzfaMpN2nk5HVSw7XnOn/49IkxDKz8YrlH2qJXj2iZB0Zo2O71c4qQk1fMUDi3LGpij7RCW7AW9vYYsSqIKRnFS94ilu7NFhUzLiieYr4BKHpdTmdD6c0esKEYBpabxDSc=",
            "SigningCertURL": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem",
            "UnsubscribeURL": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:{}:some-topic:2bcfbf39-05c3-41de-beaa-fcfcc21c8f55".format(
                DEFAULT_ACCOUNT_ID
            ),
        }
        if message_attributes:
            post_data["MessageAttributes"] = message_attributes
        return post_data


class PlatformApplication(BaseModel):
    def __init__(self, region, name, platform, attributes):
        self.region = region
        self.name = name
        self.platform = platform
        self.attributes = attributes

    @property
    def arn(self):
        return "arn:aws:sns:{region}:{AccountId}:app/{platform}/{name}".format(
            region=self.region,
            platform=self.platform,
            name=self.name,
            AccountId=DEFAULT_ACCOUNT_ID,
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
        if "Token" not in self.attributes:
            self.attributes["Token"] = self.token
        if "Enabled" not in self.attributes:
            self.attributes["Enabled"] = "True"

    @property
    def enabled(self):
        return json.loads(self.attributes.get("Enabled", "true").lower())

    @property
    def arn(self):
        return "arn:aws:sns:{region}:{AccountId}:endpoint/{platform}/{name}/{id}".format(
            region=self.region,
            AccountId=DEFAULT_ACCOUNT_ID,
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
        self.sms_attributes = {}
        self.opt_out_numbers = [
            "+447420500600",
            "+447420505401",
            "+447632960543",
            "+447632960028",
            "+447700900149",
            "+447700900550",
            "+447700900545",
            "+447700900907",
        ]

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def update_sms_attributes(self, attrs):
        self.sms_attributes.update(attrs)

    def create_topic(self, name, attributes=None, tags=None):
        fails_constraints = not re.match(r"^[a-zA-Z0-9_-]{1,256}$", name)
        if fails_constraints:
            raise InvalidParameterValue(
                "Topic names must be made up of only uppercase and lowercase ASCII letters, numbers, underscores, and hyphens, and must be between 1 and 256 characters long."
            )
        candidate_topic = Topic(name, self)
        if attributes:
            for attribute in attributes:
                setattr(
                    candidate_topic,
                    camelcase_to_underscores(attribute),
                    attributes[attribute],
                )
        if tags:
            candidate_topic._tags = tags
        if candidate_topic.arn in self.topics:
            return self.topics[candidate_topic.arn]
        else:
            self.topics[candidate_topic.arn] = candidate_topic
            return candidate_topic

    def _get_values_nexttoken(self, values_map, next_token=None):
        if next_token is None or not next_token:
            next_token = 0
        next_token = int(next_token)
        values = list(values_map.values())[next_token : next_token + DEFAULT_PAGE_SIZE]
        if len(values) == DEFAULT_PAGE_SIZE:
            next_token = next_token + DEFAULT_PAGE_SIZE
        else:
            next_token = None
        return values, next_token

    def _get_topic_subscriptions(self, topic):
        return [sub for sub in self.subscriptions.values() if sub.topic == topic]

    def list_topics(self, next_token=None):
        return self._get_values_nexttoken(self.topics, next_token)

    def delete_topic(self, arn):
        self.topics.pop(arn)

    def get_topic(self, arn):
        try:
            return self.topics[arn]
        except KeyError:
            raise SNSNotFoundError("Topic with arn {0} not found".format(arn))

    def get_topic_from_phone_number(self, number):
        for subscription in self.subscriptions.values():
            if subscription.protocol == "sms" and subscription.endpoint == number:
                return subscription.topic.arn
        raise SNSNotFoundError("Could not find valid subscription")

    def set_topic_attribute(self, topic_arn, attribute_name, attribute_value):
        topic = self.get_topic(topic_arn)
        setattr(topic, attribute_name, attribute_value)

    def subscribe(self, topic_arn, endpoint, protocol):
        if protocol == "sms":
            if re.search(r"[./-]{2,}", endpoint) or re.search(
                r"(^[./-]|[./-]$)", endpoint
            ):
                raise SNSInvalidParameter("Invalid SMS endpoint: {}".format(endpoint))

            reduced_endpoint = re.sub(r"[./-]", "", endpoint)

            if not is_e164(reduced_endpoint):
                raise SNSInvalidParameter("Invalid SMS endpoint: {}".format(endpoint))

        # AWS doesn't create duplicates
        old_subscription = self._find_subscription(topic_arn, endpoint, protocol)
        if old_subscription:
            return old_subscription
        topic = self.get_topic(topic_arn)
        subscription = Subscription(topic, endpoint, protocol)
        attributes = {
            "PendingConfirmation": "false",
            "ConfirmationWasAuthenticated": "true",
            "Endpoint": endpoint,
            "TopicArn": topic_arn,
            "Protocol": protocol,
            "SubscriptionArn": subscription.arn,
            "Owner": DEFAULT_ACCOUNT_ID,
            "RawMessageDelivery": "false",
        }

        if protocol in ["http", "https"]:
            attributes["EffectiveDeliveryPolicy"] = topic.effective_delivery_policy

        subscription.attributes = attributes
        self.subscriptions[subscription.arn] = subscription
        return subscription

    def _find_subscription(self, topic_arn, endpoint, protocol):
        for subscription in self.subscriptions.values():
            if (
                subscription.topic.arn == topic_arn
                and subscription.endpoint == endpoint
                and subscription.protocol == protocol
            ):
                return subscription
        return None

    def unsubscribe(self, subscription_arn):
        self.subscriptions.pop(subscription_arn, None)

    def list_subscriptions(self, topic_arn=None, next_token=None):
        if topic_arn:
            topic = self.get_topic(topic_arn)
            filtered = OrderedDict(
                [(sub.arn, sub) for sub in self._get_topic_subscriptions(topic)]
            )
            return self._get_values_nexttoken(filtered, next_token)
        else:
            return self._get_values_nexttoken(self.subscriptions, next_token)

    def publish(self, arn, message, subject=None, message_attributes=None):
        if subject is not None and len(subject) > 100:
            # Note that the AWS docs around length are wrong: https://github.com/spulec/moto/issues/1503
            raise ValueError("Subject must be less than 100 characters")

        if len(message) > MAXIMUM_MESSAGE_LENGTH:
            raise InvalidParameterValue(
                "An error occurred (InvalidParameter) when calling the Publish operation: Invalid parameter: Message too long"
            )

        try:
            topic = self.get_topic(arn)
            message_id = topic.publish(
                message, subject=subject, message_attributes=message_attributes
            )
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
            raise SNSNotFoundError("Application with arn {0} not found".format(arn))

    def set_application_attributes(self, arn, attributes):
        application = self.get_application(arn)
        application.attributes.update(attributes)
        return application

    def list_platform_applications(self):
        return self.applications.values()

    def delete_platform_application(self, platform_arn):
        self.applications.pop(platform_arn)

    def create_platform_endpoint(
        self, region, application, custom_user_data, token, attributes
    ):
        if any(
            token == endpoint.token for endpoint in self.platform_endpoints.values()
        ):
            raise DuplicateSnsEndpointError("Duplicate endpoint token: %s" % token)
        platform_endpoint = PlatformEndpoint(
            region, application, custom_user_data, token, attributes
        )
        self.platform_endpoints[platform_endpoint.arn] = platform_endpoint
        return platform_endpoint

    def list_endpoints_by_platform_application(self, application_arn):
        return [
            endpoint
            for endpoint in self.platform_endpoints.values()
            if endpoint.application.arn == application_arn
        ]

    def get_endpoint(self, arn):
        try:
            return self.platform_endpoints[arn]
        except KeyError:
            raise SNSNotFoundError("Endpoint with arn {0} not found".format(arn))

    def set_endpoint_attributes(self, arn, attributes):
        endpoint = self.get_endpoint(arn)
        endpoint.attributes.update(attributes)
        return endpoint

    def delete_endpoint(self, arn):
        try:
            del self.platform_endpoints[arn]
        except KeyError:
            raise SNSNotFoundError("Endpoint with arn {0} not found".format(arn))

    def get_subscription_attributes(self, arn):
        _subscription = [_ for _ in self.subscriptions.values() if _.arn == arn]
        if not _subscription:
            raise SNSNotFoundError("Subscription with arn {0} not found".format(arn))
        subscription = _subscription[0]

        return subscription.attributes

    def set_subscription_attributes(self, arn, name, value):
        if name not in ["RawMessageDelivery", "DeliveryPolicy", "FilterPolicy"]:
            raise SNSInvalidParameter("AttributeName")

        # TODO: should do validation
        _subscription = [_ for _ in self.subscriptions.values() if _.arn == arn]
        if not _subscription:
            raise SNSNotFoundError("Subscription with arn {0} not found".format(arn))
        subscription = _subscription[0]

        subscription.attributes[name] = value

        if name == "FilterPolicy":
            filter_policy = json.loads(value)
            self._validate_filter_policy(filter_policy)
            subscription._filter_policy = filter_policy

    def _validate_filter_policy(self, value):
        # TODO: extend validation checks
        combinations = 1
        for rules in six.itervalues(value):
            combinations *= len(rules)
        # Even the official documentation states the total combination of values must not exceed 100, in reality it is 150
        # https://docs.aws.amazon.com/sns/latest/dg/sns-subscription-filter-policies.html#subscription-filter-policy-constraints
        if combinations > 150:
            raise SNSInvalidParameter(
                "Invalid parameter: FilterPolicy: Filter policy is too complex"
            )

        for field, rules in six.iteritems(value):
            for rule in rules:
                if rule is None:
                    continue
                if isinstance(rule, six.string_types):
                    continue
                if isinstance(rule, bool):
                    continue
                if isinstance(rule, (six.integer_types, float)):
                    if rule <= -1000000000 or rule >= 1000000000:
                        raise InternalError("Unknown")
                    continue
                if isinstance(rule, dict):
                    keyword = list(rule.keys())[0]
                    attributes = list(rule.values())[0]
                    if keyword == "anything-but":
                        continue
                    elif keyword == "exists":
                        if not isinstance(attributes, bool):
                            raise SNSInvalidParameter(
                                "Invalid parameter: FilterPolicy: exists match pattern must be either true or false."
                            )
                        continue
                    elif keyword == "numeric":
                        continue
                    elif keyword == "prefix":
                        continue
                    else:
                        raise SNSInvalidParameter(
                            "Invalid parameter: FilterPolicy: Unrecognized match type {type}".format(
                                type=keyword
                            )
                        )

                raise SNSInvalidParameter(
                    "Invalid parameter: FilterPolicy: Match value must be String, number, true, false, or null"
                )

    def add_permission(self, topic_arn, label, aws_account_ids, action_names):
        if topic_arn not in self.topics:
            raise SNSNotFoundError("Topic does not exist")

        policy = self.topics[topic_arn]._policy_json
        statement = next(
            (
                statement
                for statement in policy["Statement"]
                if statement["Sid"] == label
            ),
            None,
        )

        if statement:
            raise SNSInvalidParameter("Statement already exists")

        if any(action_name not in VALID_POLICY_ACTIONS for action_name in action_names):
            raise SNSInvalidParameter("Policy statement action out of service scope!")

        principals = [
            "arn:aws:iam::{}:root".format(account_id) for account_id in aws_account_ids
        ]
        actions = ["SNS:{}".format(action_name) for action_name in action_names]

        statement = {
            "Sid": label,
            "Effect": "Allow",
            "Principal": {"AWS": principals[0] if len(principals) == 1 else principals},
            "Action": actions[0] if len(actions) == 1 else actions,
            "Resource": topic_arn,
        }

        self.topics[topic_arn]._policy_json["Statement"].append(statement)

    def remove_permission(self, topic_arn, label):
        if topic_arn not in self.topics:
            raise SNSNotFoundError("Topic does not exist")

        statements = self.topics[topic_arn]._policy_json["Statement"]
        statements = [
            statement for statement in statements if statement["Sid"] != label
        ]

        self.topics[topic_arn]._policy_json["Statement"] = statements

    def list_tags_for_resource(self, resource_arn):
        if resource_arn not in self.topics:
            raise ResourceNotFoundError

        return self.topics[resource_arn]._tags

    def tag_resource(self, resource_arn, tags):
        if resource_arn not in self.topics:
            raise ResourceNotFoundError

        updated_tags = self.topics[resource_arn]._tags.copy()
        updated_tags.update(tags)

        if len(updated_tags) > 50:
            raise TagLimitExceededError

        self.topics[resource_arn]._tags = updated_tags

    def untag_resource(self, resource_arn, tag_keys):
        if resource_arn not in self.topics:
            raise ResourceNotFoundError

        for key in tag_keys:
            self.topics[resource_arn]._tags.pop(key, None)


sns_backends = {}
for region in Session().get_available_regions("sns"):
    sns_backends[region] = SNSBackend(region)
for region in Session().get_available_regions("sns", partition_name="aws-us-gov"):
    sns_backends[region] = SNSBackend(region)
for region in Session().get_available_regions("sns", partition_name="aws-cn"):
    sns_backends[region] = SNSBackend(region)


DEFAULT_EFFECTIVE_DELIVERY_POLICY = {
    "defaultHealthyRetryPolicy": {
        "numNoDelayRetries": 0,
        "numMinDelayRetries": 0,
        "minDelayTarget": 20,
        "maxDelayTarget": 20,
        "numMaxDelayRetries": 0,
        "numRetries": 3,
        "backoffFunction": "linear",
    },
    "sicklyRetryPolicy": None,
    "throttlePolicy": None,
    "guaranteed": False,
}


VALID_POLICY_ACTIONS = [
    "GetTopicAttributes",
    "SetTopicAttributes",
    "AddPermission",
    "RemovePermission",
    "DeleteTopic",
    "Subscribe",
    "ListSubscriptionsByTopic",
    "Publish",
    "Receive",
]
