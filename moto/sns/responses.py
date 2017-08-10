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

        if self.request_json:
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

        template = self.response_template(CREATE_TOPIC_TEMPLATE)
        return template.render(topic=topic)

    def list_topics(self):
        next_token = self._get_param('NextToken')
        topics, next_token = self.backend.list_topics(next_token=next_token)

        if self.request_json:
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

        template = self.response_template(LIST_TOPICS_TEMPLATE)
        return template.render(topics=topics, next_token=next_token)

    def delete_topic(self):
        topic_arn = self._get_param('TopicArn')
        self.backend.delete_topic(topic_arn)

        if self.request_json:
            return json.dumps({
                'DeleteTopicResponse': {
                    'ResponseMetadata': {
                        'RequestId': 'a8dec8b3-33a4-11df-8963-01868b7c937a',
                    }
                }
            })

        template = self.response_template(DELETE_TOPIC_TEMPLATE)
        return template.render()

    def get_topic_attributes(self):
        topic_arn = self._get_param('TopicArn')
        topic = self.backend.get_topic(topic_arn)

        if self.request_json:
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

        template = self.response_template(GET_TOPIC_ATTRIBUTES_TEMPLATE)
        return template.render(topic=topic)

    def set_topic_attributes(self):
        topic_arn = self._get_param('TopicArn')
        attribute_name = self._get_param('AttributeName')
        attribute_name = camelcase_to_underscores(attribute_name)
        attribute_value = self._get_param('AttributeValue')
        self.backend.set_topic_attribute(
            topic_arn, attribute_name, attribute_value)

        if self.request_json:
            return json.dumps({
                "SetTopicAttributesResponse": {
                    "ResponseMetadata": {
                        "RequestId": "a8763b99-33a7-11df-a9b7-05d48da6f042"
                    }
                }
            })

        template = self.response_template(SET_TOPIC_ATTRIBUTES_TEMPLATE)
        return template.render()

    def subscribe(self):
        topic_arn = self._get_param('TopicArn')
        endpoint = self._get_param('Endpoint')
        protocol = self._get_param('Protocol')
        subscription = self.backend.subscribe(topic_arn, endpoint, protocol)

        if self.request_json:
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

        template = self.response_template(SUBSCRIBE_TEMPLATE)
        return template.render(subscription=subscription)

    def unsubscribe(self):
        subscription_arn = self._get_param('SubscriptionArn')
        self.backend.unsubscribe(subscription_arn)

        if self.request_json:
            return json.dumps({
                "UnsubscribeResponse": {
                    "ResponseMetadata": {
                        "RequestId": "a8763b99-33a7-11df-a9b7-05d48da6f042"
                    }
                }
            })

        template = self.response_template(UNSUBSCRIBE_TEMPLATE)
        return template.render()

    def list_subscriptions(self):
        next_token = self._get_param('NextToken')
        subscriptions, next_token = self.backend.list_subscriptions(
            next_token=next_token)

        if self.request_json:
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

        template = self.response_template(LIST_SUBSCRIPTIONS_TEMPLATE)
        return template.render(subscriptions=subscriptions,
                               next_token=next_token)

    def list_subscriptions_by_topic(self):
        topic_arn = self._get_param('TopicArn')
        next_token = self._get_param('NextToken')
        subscriptions, next_token = self.backend.list_subscriptions(
            topic_arn, next_token=next_token)

        if self.request_json:
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

        template = self.response_template(LIST_SUBSCRIPTIONS_BY_TOPIC_TEMPLATE)
        return template.render(subscriptions=subscriptions,
                               next_token=next_token)

    def publish(self):
        target_arn = self._get_param('TargetArn')
        topic_arn = self._get_param('TopicArn')
        arn = target_arn if target_arn else topic_arn
        message = self._get_param('Message')
        message_id = self.backend.publish(arn, message)

        if self.request_json:
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

        template = self.response_template(PUBLISH_TEMPLATE)
        return template.render(message_id=message_id)

    def create_platform_application(self):
        name = self._get_param('Name')
        platform = self._get_param('Platform')
        attributes = self._get_attributes()
        platform_application = self.backend.create_platform_application(
            self.region, name, platform, attributes)

        if self.request_json:
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

        template = self.response_template(CREATE_PLATFORM_APPLICATION_TEMPLATE)
        return template.render(platform_application=platform_application)

    def get_platform_application_attributes(self):
        arn = self._get_param('PlatformApplicationArn')
        application = self.backend.get_application(arn)

        if self.request_json:
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

        template = self.response_template(
            GET_PLATFORM_APPLICATION_ATTRIBUTES_TEMPLATE)
        return template.render(application=application)

    def set_platform_application_attributes(self):
        arn = self._get_param('PlatformApplicationArn')
        attributes = self._get_attributes()

        self.backend.set_application_attributes(arn, attributes)

        if self.request_json:
            return json.dumps({
                "SetPlatformApplicationAttributesResponse": {
                    "ResponseMetadata": {
                        "RequestId": "384ac68d-3775-12df-8963-01868b7c937f",
                    }
                }
            })

        template = self.response_template(
            SET_PLATFORM_APPLICATION_ATTRIBUTES_TEMPLATE)
        return template.render()

    def list_platform_applications(self):
        applications = self.backend.list_platform_applications()

        if self.request_json:
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

        template = self.response_template(LIST_PLATFORM_APPLICATIONS_TEMPLATE)
        return template.render(applications=applications)

    def delete_platform_application(self):
        platform_arn = self._get_param('PlatformApplicationArn')
        self.backend.delete_platform_application(platform_arn)

        if self.request_json:
            return json.dumps({
                "DeletePlatformApplicationResponse": {
                    "ResponseMetadata": {
                        "RequestId": "384ac68d-3775-11df-8963-01868b7c937e",
                    }
                }
            })

        template = self.response_template(DELETE_PLATFORM_APPLICATION_TEMPLATE)
        return template.render()

    def create_platform_endpoint(self):
        application_arn = self._get_param('PlatformApplicationArn')
        application = self.backend.get_application(application_arn)

        custom_user_data = self._get_param('CustomUserData')
        token = self._get_param('Token')
        attributes = self._get_attributes()

        platform_endpoint = self.backend.create_platform_endpoint(
            self.region, application, custom_user_data, token, attributes)

        if self.request_json:
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

        template = self.response_template(CREATE_PLATFORM_ENDPOINT_TEMPLATE)
        return template.render(platform_endpoint=platform_endpoint)

    def list_endpoints_by_platform_application(self):
        application_arn = self._get_param('PlatformApplicationArn')
        endpoints = self.backend.list_endpoints_by_platform_application(
            application_arn)

        if self.request_json:
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

        template = self.response_template(
            LIST_ENDPOINTS_BY_PLATFORM_APPLICATION_TEMPLATE)
        return template.render(endpoints=endpoints)

    def get_endpoint_attributes(self):
        arn = self._get_param('EndpointArn')
        endpoint = self.backend.get_endpoint(arn)

        if self.request_json:
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

        template = self.response_template(GET_ENDPOINT_ATTRIBUTES_TEMPLATE)
        return template.render(endpoint=endpoint)

    def set_endpoint_attributes(self):
        arn = self._get_param('EndpointArn')
        attributes = self._get_attributes()

        self.backend.set_endpoint_attributes(arn, attributes)

        if self.request_json:
            return json.dumps({
                "SetEndpointAttributesResponse": {
                    "ResponseMetadata": {
                        "RequestId": "384bc68d-3775-12df-8963-01868b7c937f",
                    }
                }
            })

        template = self.response_template(SET_ENDPOINT_ATTRIBUTES_TEMPLATE)
        return template.render()

    def delete_endpoint(self):
        arn = self._get_param('EndpointArn')
        self.backend.delete_endpoint(arn)

        if self.request_json:
            return json.dumps({
                "DeleteEndpointResponse": {
                    "ResponseMetadata": {
                        "RequestId": "384bc68d-3775-12df-8963-01868b7c937f",
                    }
                }
            })

        template = self.response_template(DELETE_ENDPOINT_TEMPLATE)
        return template.render()


CREATE_TOPIC_TEMPLATE = """<CreateTopicResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
     <CreateTopicResult>
       <TopicArn>{{ topic.arn }}</TopicArn>
     </CreateTopicResult>
     <ResponseMetadata>
       <RequestId>a8dec8b3-33a4-11df-8963-01868b7c937a</RequestId>
     </ResponseMetadata>
   </CreateTopicResponse>"""

LIST_TOPICS_TEMPLATE = """<ListTopicsResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <ListTopicsResult>
    <Topics>
    {% for topic in topics %}
      <member>
        <TopicArn>{{ topic.arn }}</TopicArn>
      </member>
    {% endfor %}
    </Topics>
    {% if next_token  %}
    <NextToken>{{ next_token }}</NextToken>
    {% endif %}
  </ListTopicsResult>
  <ResponseMetadata>
    <RequestId>3f1478c7-33a9-11df-9540-99d0768312d3</RequestId>
  </ResponseMetadata>
</ListTopicsResponse>"""

DELETE_TOPIC_TEMPLATE = """<DeleteTopicResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <ResponseMetadata>
    <RequestId>f3aa9ac9-3c3d-11df-8235-9dab105e9c32</RequestId>
  </ResponseMetadata>
</DeleteTopicResponse>"""

GET_TOPIC_ATTRIBUTES_TEMPLATE = """<GetTopicAttributesResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <GetTopicAttributesResult>
    <Attributes>
      <entry>
        <key>Owner</key>
        <value>{{ topic.account_id }}</value>
      </entry>
      <entry>
        <key>Policy</key>
        <value>{{ topic.policy }}</value>
      </entry>
      <entry>
        <key>TopicArn</key>
        <value>{{ topic.arn }}</value>
      </entry>
      <entry>
        <key>DisplayName</key>
        <value>{{ topic.display_name }}</value>
      </entry>
      <entry>
        <key>SubscriptionsPending</key>
        <value>{{ topic.subscriptions_pending }}</value>
      </entry>
      <entry>
        <key>SubscriptionsConfirmed</key>
        <value>{{ topic.subscriptions_confimed }}</value>
      </entry>
      <entry>
        <key>SubscriptionsDeleted</key>
        <value>{{ topic.subscriptions_deleted }}</value>
      </entry>
      <entry>
        <key>DeliveryPolicy</key>
        <value>{{ topic.delivery_policy }}</value>
      </entry>
      <entry>
        <key>EffectiveDeliveryPolicy</key>
        <value>{{ topic.effective_delivery_policy }}</value>
      </entry>
    </Attributes>
  </GetTopicAttributesResult>
  <ResponseMetadata>
    <RequestId>057f074c-33a7-11df-9540-99d0768312d3</RequestId>
  </ResponseMetadata>
</GetTopicAttributesResponse>"""

SET_TOPIC_ATTRIBUTES_TEMPLATE = """<SetTopicAttributesResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <ResponseMetadata>
    <RequestId>a8763b99-33a7-11df-a9b7-05d48da6f042</RequestId>
  </ResponseMetadata>
</SetTopicAttributesResponse>"""

CREATE_PLATFORM_APPLICATION_TEMPLATE = """<CreatePlatformApplicationResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <CreatePlatformApplicationResult>
    <PlatformApplicationArn>{{ platform_application.arn }}</PlatformApplicationArn>
  </CreatePlatformApplicationResult>
  <ResponseMetadata>
    <RequestId>b6f0e78b-e9d4-5a0e-b973-adc04e8a4ff9</RequestId>
  </ResponseMetadata>
</CreatePlatformApplicationResponse>"""

CREATE_PLATFORM_ENDPOINT_TEMPLATE = """<CreatePlatformEndpointResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <CreatePlatformEndpointResult>
    <EndpointArn>{{ platform_endpoint.arn }}</EndpointArn>
  </CreatePlatformEndpointResult>
  <ResponseMetadata>
    <RequestId>6613341d-3e15-53f7-bf3c-7e56994ba278</RequestId>
  </ResponseMetadata>
</CreatePlatformEndpointResponse>"""

LIST_PLATFORM_APPLICATIONS_TEMPLATE = """<ListPlatformApplicationsResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <ListPlatformApplicationsResult>
    <PlatformApplications>
    {% for application in applications %}
      <member>
      <PlatformApplicationArn>{{ application.arn }}</PlatformApplicationArn>
        <Attributes>
        {% for attribute in application.attributes %}
          <entry>
            <key>{{ attribute }}</key>
            <value>{{ application.attributes[attribute] }}</value>
          </entry>
        {% endfor %}
        </Attributes>
      </member>
    {% endfor %}
    </PlatformApplications>
  </ListPlatformApplicationsResult>
  <ResponseMetadata>
    <RequestId>315a335e-85d8-52df-9349-791283cbb529</RequestId>
  </ResponseMetadata>
</ListPlatformApplicationsResponse>"""

DELETE_PLATFORM_APPLICATION_TEMPLATE = """<DeletePlatformApplicationResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <ResponseMetadata>
    <RequestId>097dac18-7a77-5823-a8dd-e65476dcb037</RequestId>
  </ResponseMetadata>
</DeletePlatformApplicationResponse>"""

GET_ENDPOINT_ATTRIBUTES_TEMPLATE = """<GetEndpointAttributesResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <GetEndpointAttributesResult>
    <Attributes>
    {% for attribute in endpoint.attributes %}
      <entry>
        <key>{{ attribute }}</key>
        <value>{{ endpoint.attributes[attribute] }}</value>
      </entry>
    {% endfor %}
    </Attributes>
  </GetEndpointAttributesResult>
  <ResponseMetadata>
    <RequestId>6c725a19-a142-5b77-94f9-1055a9ea04e7</RequestId>
  </ResponseMetadata>
</GetEndpointAttributesResponse>"""

LIST_ENDPOINTS_BY_PLATFORM_APPLICATION_TEMPLATE = """<ListEndpointsByPlatformApplicationResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <ListEndpointsByPlatformApplicationResult>
    <Endpoints>
      {% for endpoint in endpoints %}
      <member>
        <EndpointArn>{{ endpoint.arn }}</EndpointArn>
        <Attributes>
          {% for attribute in endpoint.attributes %}
          <entry>
            <key>{{ attribute }}</key>
            <value>{{ endpoint.attributes[attribute] }}</value>
          </entry>
          {% endfor %}
        </Attributes>
      </member>
      {% endfor %}
    </Endpoints>
  </ListEndpointsByPlatformApplicationResult>
  <ResponseMetadata>
    <RequestId>9a48768c-dac8-5a60-aec0-3cc27ea08d96</RequestId>
  </ResponseMetadata>
</ListEndpointsByPlatformApplicationResponse>"""

GET_PLATFORM_APPLICATION_ATTRIBUTES_TEMPLATE = """<GetPlatformApplicationAttributesResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <GetPlatformApplicationAttributesResult>
    <Attributes>
    {% for attribute in application.attributes %}
      <entry>
        <key>{{ attribute }}</key>
        <value>{{ application.attributes[attribute] }}</value>
      </entry>
    {% endfor %}
    </Attributes>
  </GetPlatformApplicationAttributesResult>
  <ResponseMetadata>
    <RequestId>74848df2-87f6-55ed-890c-c7be80442462</RequestId>
  </ResponseMetadata>
</GetPlatformApplicationAttributesResponse>"""

PUBLISH_TEMPLATE = """<PublishResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <PublishResult>
    <MessageId>{{ message_id }}</MessageId>
  </PublishResult>
  <ResponseMetadata>
    <RequestId>f187a3c1-376f-11df-8963-01868b7c937a</RequestId>
  </ResponseMetadata>
</PublishResponse>"""

SET_ENDPOINT_ATTRIBUTES_TEMPLATE = """<SetEndpointAttributesResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <ResponseMetadata>
    <RequestId>2fe0bfc7-3e85-5ee5-a9e2-f58b35e85f6a</RequestId>
  </ResponseMetadata>
</SetEndpointAttributesResponse>"""

DELETE_ENDPOINT_TEMPLATE = """<DeleteEndpointResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
 <ResponseMetadata>
 <RequestId>c1d2b191-353c-5a5f-8969-fbdd3900afa8</RequestId>
 </ResponseMetadata>
</DeleteEndpointResponse>"""


SET_PLATFORM_APPLICATION_ATTRIBUTES_TEMPLATE = """<SetPlatformApplicationAttributesResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <ResponseMetadata>
    <RequestId>cf577bcc-b3dc-5463-88f1-3180b9412395</RequestId>
  </ResponseMetadata>
</SetPlatformApplicationAttributesResponse>"""

SUBSCRIBE_TEMPLATE = """<SubscribeResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <SubscribeResult>
    <SubscriptionArn>{{ subscription.arn }}</SubscriptionArn>
  </SubscribeResult>
  <ResponseMetadata>
    <RequestId>c4407779-24a4-56fa-982c-3d927f93a775</RequestId>
  </ResponseMetadata>
</SubscribeResponse>"""

UNSUBSCRIBE_TEMPLATE = """<UnsubscribeResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <ResponseMetadata>
    <RequestId>18e0ac39-3776-11df-84c0-b93cc1666b84</RequestId>
  </ResponseMetadata>
</UnsubscribeResponse>"""

LIST_SUBSCRIPTIONS_TEMPLATE = """<ListSubscriptionsResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <ListSubscriptionsResult>
    <Subscriptions>
    {% for subscription in subscriptions %}
      <member>
        <TopicArn>{{ subscription.topic.arn }}</TopicArn>
        <Protocol>{{ subscription.protocol }}</Protocol>
        <SubscriptionArn>{{ subscription.arn }}</SubscriptionArn>
        <Owner>{{ subscription.account_id }}</Owner>
        <Endpoint>{{ subscription.endpoint }}</Endpoint>
      </member>
    {% endfor %}
    </Subscriptions>
    {% if next_token  %}
    <NextToken>{{ next_token }}</NextToken>
    {% endif %}
  </ListSubscriptionsResult>
  <ResponseMetadata>
    <RequestId>384ac68d-3775-11df-8963-01868b7c937a</RequestId>
  </ResponseMetadata>
</ListSubscriptionsResponse>"""

LIST_SUBSCRIPTIONS_BY_TOPIC_TEMPLATE = """<ListSubscriptionsByTopicResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">
  <ListSubscriptionsByTopicResult>
    <Subscriptions>
    {% for subscription in subscriptions %}
      <member>
        <TopicArn>{{ subscription.topic.arn }}</TopicArn>
        <Protocol>{{ subscription.protocol }}</Protocol>
        <SubscriptionArn>{{ subscription.arn }}</SubscriptionArn>
        <Owner>{{ subscription.account_id }}</Owner>
        <Endpoint>{{ subscription.endpoint }}</Endpoint>
      </member>
    {% endfor %}
    </Subscriptions>
    {% if next_token  %}
    <NextToken>{{ next_token }}</NextToken>
    {% endif %}
  </ListSubscriptionsByTopicResult>
  <ResponseMetadata>
    <RequestId>384ac68d-3775-11df-8963-01868b7c937a</RequestId>
  </ResponseMetadata>
</ListSubscriptionsByTopicResponse>"""
