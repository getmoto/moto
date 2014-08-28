from __future__ import unicode_literals
import boto

import sure  # noqa

from moto import mock_sns
from moto.sns.models import DEFAULT_TOPIC_POLICY, DEFAULT_EFFECTIVE_DELIVERY_POLICY


@mock_sns
def test_create_and_delete_topic():
    conn = boto.connect_sns()
    conn.create_topic("some-topic")

    topics_json = conn.get_all_topics()
    topics = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"]
    topics.should.have.length_of(1)
    topics[0]['TopicArn'].should.equal("arn:aws:sns:us-east-1:123456789012:some-topic")

    # Delete the topic
    conn.delete_topic(topics[0]['TopicArn'])

    # And there should now be 0 topics
    topics_json = conn.get_all_topics()
    topics = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"]
    topics.should.have.length_of(0)


@mock_sns
def test_topic_attributes():
    conn = boto.connect_sns()
    conn.create_topic("some-topic")

    topics_json = conn.get_all_topics()
    topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0]['TopicArn']

    attributes = conn.get_topic_attributes(topic_arn)['GetTopicAttributesResponse']['GetTopicAttributesResult']['Attributes']
    attributes["TopicArn"].should.equal("arn:aws:sns:us-east-1:123456789012:some-topic")
    attributes["Owner"].should.equal(123456789012)
    attributes["Policy"].should.equal(DEFAULT_TOPIC_POLICY)
    attributes["DisplayName"].should.equal("")
    attributes["SubscriptionsPending"].should.equal(0)
    attributes["SubscriptionsConfirmed"].should.equal(0)
    attributes["SubscriptionsDeleted"].should.equal(0)
    attributes["DeliveryPolicy"].should.equal("")
    attributes["EffectiveDeliveryPolicy"].should.equal(DEFAULT_EFFECTIVE_DELIVERY_POLICY)

    # boto can't handle unicode here :(
    conn.set_topic_attributes(topic_arn, "Policy", {b"foo": b"bar"})
    conn.set_topic_attributes(topic_arn, "DisplayName", "My display name")
    conn.set_topic_attributes(topic_arn, "DeliveryPolicy", {b"http": {b"defaultHealthyRetryPolicy": {b"numRetries": 5}}})

    attributes = conn.get_topic_attributes(topic_arn)['GetTopicAttributesResponse']['GetTopicAttributesResult']['Attributes']
    attributes["Policy"].should.equal("{'foo': 'bar'}")
    attributes["DisplayName"].should.equal("My display name")
    attributes["DeliveryPolicy"].should.equal("{'http': {'defaultHealthyRetryPolicy': {'numRetries': 5}}}")
