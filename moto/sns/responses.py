from __future__ import unicode_literals
import json

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from .models import sns_backends


class SNSResponse(BaseResponse):

    @property
    def backend(self):
        return sns_backends[self.region]

    def _get_attributes(self):
        attributes = self._get_list_prefix('Attributes.entry')
        return dict(
            (attribute['key'], attribute['value'])
            for attribute
            in attributes
        )

    def create_topic(self):
        name = self._get_param('Name')
        topic = self.backend.create_topic(name)

        return json.dumps({
            'CreateTopicResponse': {
                'CreateTopicResult': {
                    'TopicArn': topic.arn,
                },
                'ResponseMetadata': {
                    'RequestId': 'a8dec8b3-33a4-11df-8963-01868b7c937a',
                }
            }
        })

    def list_topics(self):
        next_token = self._get_param('NextToken')
        topics, next_token = self.backend.list_topics(next_token=next_token)

        return json.dumps({
            'ListTopicsResponse': {
                'ListTopicsResult': {
                    'Topics': [{'TopicArn': topic.arn} for topic in topics],
                    'NextToken': next_token,
                }
            },
            'ResponseMetadata': {
                'RequestId': 'a8dec8b3-33a4-11df-8963-01868b7c937a',
            }
        })

    def delete_topic(self):
        topic_arn = self._get_param('TopicArn')
        self.backend.delete_topic(topic_arn)

        return json.dumps({
            'DeleteTopicResponse': {
                'ResponseMetadata': {
                    'RequestId': 'a8dec8b3-33a4-11df-8963-01868b7c937a',
                }
            }
        })

    def get_topic_attributes(self):
        topic_arn = self._get_param('TopicArn')
        topic = self.backend.get_topic(topic_arn)

        return json.dumps({
            "GetTopicAttributesResponse": {
                "GetTopicAttributesResult": {
                    "Attributes": {
                        "Owner": topic.account_id,
                        "Policy": topic.policy,
                        "TopicArn": topic.arn,
                        "DisplayName": topic.display_name,
                        "SubscriptionsPending": topic.subscriptions_pending,
                        "SubscriptionsConfirmed": topic.subscriptions_confimed,
                        "SubscriptionsDeleted": topic.subscriptions_deleted,
                        "DeliveryPolicy": topic.delivery_policy,
                        "EffectiveDeliveryPolicy": topic.effective_delivery_policy,
                    }
                },
                "ResponseMetadata": {
                    "RequestId": "057f074c-33a7-11df-9540-99d0768312d3"
                }
            }
        })

    def set_topic_attributes(self):
        topic_arn = self._get_param('TopicArn')
        attribute_name = self._get_param('AttributeName')
        attribute_name = camelcase_to_underscores(attribute_name)
        attribute_value = self._get_param('AttributeValue')
        self.backend.set_topic_attribute(topic_arn, attribute_name, attribute_value)

        return json.dumps({
            "SetTopicAttributesResponse": {
                "ResponseMetadata": {
                    "RequestId": "a8763b99-33a7-11df-a9b7-05d48da6f042"
                }
            }
        })

    def subscribe(self):
        topic_arn = self._get_param('TopicArn')
        endpoint = self._get_param('Endpoint')
        protocol = self._get_param('Protocol')
        subscription = self.backend.subscribe(topic_arn, endpoint, protocol)

        return json.dumps({
            "SubscribeResponse": {
                "SubscribeResult": {
                    "SubscriptionArn": subscription.arn,
                },
                "ResponseMetadata": {
                    "RequestId": "a8763b99-33a7-11df-a9b7-05d48da6f042"
                }
            }
        })

    def unsubscribe(self):
        subscription_arn = self._get_param('SubscriptionArn')
        self.backend.unsubscribe(subscription_arn)

        return json.dumps({
            "UnsubscribeResponse": {
                "ResponseMetadata": {
                    "RequestId": "a8763b99-33a7-11df-a9b7-05d48da6f042"
                }
            }
        })

    def list_subscriptions(self):
        next_token = self._get_param('NextToken')
        subscriptions, next_token = self.backend.list_subscriptions(next_token=next_token)

        return json.dumps({
            "ListSubscriptionsResponse": {
                "ListSubscriptionsResult": {
                    "Subscriptions": [{
                        "TopicArn": subscription.topic.arn,
                        "Protocol": subscription.protocol,
                        "SubscriptionArn": subscription.arn,
                        "Owner": subscription.topic.account_id,
                        "Endpoint": subscription.endpoint,
                    } for subscription in subscriptions],
                    'NextToken': next_token,
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def list_subscriptions_by_topic(self):
        topic_arn = self._get_param('TopicArn')
        next_token = self._get_param('NextToken')
        subscriptions, next_token = self.backend.list_subscriptions(topic_arn, next_token=next_token)

        return json.dumps({
            "ListSubscriptionsByTopicResponse": {
                "ListSubscriptionsByTopicResult": {
                    "Subscriptions": [{
                        "TopicArn": subscription.topic.arn,
                        "Protocol": subscription.protocol,
                        "SubscriptionArn": subscription.arn,
                        "Owner": subscription.topic.account_id,
                        "Endpoint": subscription.endpoint,
                    } for subscription in subscriptions],
                    'NextToken': next_token,
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def publish(self):
        target_arn = self._get_param('TargetArn')
        topic_arn = self._get_param('TopicArn')
        arn = target_arn if target_arn else topic_arn
        message = self._get_param('Message')
        message_id = self.backend.publish(arn, message)

        return json.dumps({
            "PublishResponse": {
                "PublishResult": {
                    "MessageId": message_id,
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def create_platform_application(self):
        name = self._get_param('Name')
        platform = self._get_param('Platform')
        attributes = self._get_attributes()
        platform_application = self.backend.create_platform_application(self.region, name, platform, attributes)

        return json.dumps({
            "CreatePlatformApplicationResponse": {
                "CreatePlatformApplicationResult": {
                    "PlatformApplicationArn": platform_application.arn,
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937b",
                }
            }
        })

    def get_platform_application_attributes(self):
        arn = self._get_param('PlatformApplicationArn')
        application = self.backend.get_application(arn)

        return json.dumps({
            "GetPlatformApplicationAttributesResponse": {
                "GetPlatformApplicationAttributesResult": {
                    "Attributes": application.attributes,
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937f",
                }
            }
        })

    def set_platform_application_attributes(self):
        arn = self._get_param('PlatformApplicationArn')
        attributes = self._get_attributes()

        self.backend.set_application_attributes(arn, attributes)

        return json.dumps({
            "SetPlatformApplicationAttributesResponse": {
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-12df-8963-01868b7c937f",
                }
            }
        })

    def list_platform_applications(self):
        applications = self.backend.list_platform_applications()

        return json.dumps({
            "ListPlatformApplicationsResponse": {
                "ListPlatformApplicationsResult": {
                    "PlatformApplications": [{
                        "PlatformApplicationArn": application.arn,
                        "attributes": application.attributes,
                    } for application in applications],
                    "NextToken": None
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937c",
                }
            }
        })

    def delete_platform_application(self):
        platform_arn = self._get_param('PlatformApplicationArn')
        self.backend.delete_platform_application(platform_arn)

        return json.dumps({
            "DeletePlatformApplicationResponse": {
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937e",
                }
            }
        })

    def create_platform_endpoint(self):
        application_arn = self._get_param('PlatformApplicationArn')
        application = self.backend.get_application(application_arn)

        custom_user_data = self._get_param('CustomUserData')
        token = self._get_param('Token')
        attributes = self._get_attributes()

        platform_endpoint = self.backend.create_platform_endpoint(
            self.region, application, custom_user_data, token, attributes)

        return json.dumps({
            "CreatePlatformEndpointResponse": {
                "CreatePlatformEndpointResult": {
                    "EndpointArn": platform_endpoint.arn,
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3779-11df-8963-01868b7c937b",
                }
            }
        })

    def list_endpoints_by_platform_application(self):
        application_arn = self._get_param('PlatformApplicationArn')
        endpoints = self.backend.list_endpoints_by_platform_application(application_arn)

        return json.dumps({
            "ListEndpointsByPlatformApplicationResponse": {
                "ListEndpointsByPlatformApplicationResult": {
                    "Endpoints": [
                        {
                            "Attributes": endpoint.attributes,
                            "EndpointArn": endpoint.arn,
                        } for endpoint in endpoints
                    ],
                    "NextToken": None
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def get_endpoint_attributes(self):
        arn = self._get_param('EndpointArn')
        endpoint = self.backend.get_endpoint(arn)

        return json.dumps({
            "GetEndpointAttributesResponse": {
                "GetEndpointAttributesResult": {
                    "Attributes": endpoint.attributes,
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937f",
                }
            }
        })

    def set_endpoint_attributes(self):
        arn = self._get_param('EndpointArn')
        attributes = self._get_attributes()

        self.backend.set_endpoint_attributes(arn, attributes)

        return json.dumps({
            "SetEndpointAttributesResponse": {
                "ResponseMetadata": {
                    "RequestId": "384bc68d-3775-12df-8963-01868b7c937f",
                }
            }
        })
