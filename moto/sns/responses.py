import json

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from .models import sns_backend


class SNSResponse(BaseResponse):

    def create_topic(self):
        name = self._get_param('Name')
        topic = sns_backend.create_topic(name)

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
        topics = sns_backend.list_topics()

        return json.dumps({
            'ListTopicsResponse': {
                'ListTopicsResult': {
                    'Topics': [{'TopicArn': topic.arn} for topic in topics],
                    'NextToken': None,
                }
            },
            'ResponseMetadata': {
                'RequestId': 'a8dec8b3-33a4-11df-8963-01868b7c937a',
            }
        })

    def delete_topic(self):
        topic_arn = self._get_param('TopicArn')
        sns_backend.delete_topic(topic_arn)

        return json.dumps({
            'DeleteTopicResponse': {
                'ResponseMetadata': {
                    'RequestId': 'a8dec8b3-33a4-11df-8963-01868b7c937a',
                }
            }
        })

    def get_topic_attributes(self):
        topic_arn = self._get_param('TopicArn')
        topic = sns_backend.get_topic(topic_arn)

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
        sns_backend.set_topic_attribute(topic_arn, attribute_name, attribute_value)

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
        subscription = sns_backend.subscribe(topic_arn, endpoint, protocol)

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
        sns_backend.unsubscribe(subscription_arn)

        return json.dumps({
            "UnsubscribeResponse": {
                "ResponseMetadata": {
                    "RequestId": "a8763b99-33a7-11df-a9b7-05d48da6f042"
                }
            }
        })

    def list_subscriptions(self):
        subscriptions = sns_backend.list_subscriptions()

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
                    'NextToken': None,
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def list_subscriptions_by_topic(self):
        topic_arn = self._get_param('TopicArn')
        subscriptions = sns_backend.list_subscriptions(topic_arn)

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
                    'NextToken': None,
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def publish(self):
        topic_arn = self._get_param('TopicArn')
        message = self._get_param('Message')
        message_id = sns_backend.publish(topic_arn, message)

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
