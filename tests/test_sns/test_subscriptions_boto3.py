from __future__ import unicode_literals
import boto3

import sure  # noqa

from moto import mock_sns
from moto.sns.models import DEFAULT_PAGE_SIZE


@mock_sns
def test_creating_subscription():
    conn = boto3.client('sns', region_name='us-east-1')
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]['TopicArn']

    conn.subscribe(TopicArn=topic_arn,
                   Protocol="http",
                   Endpoint="http://example.com/")

    subscriptions = conn.list_subscriptions()["Subscriptions"]
    subscriptions.should.have.length_of(1)
    subscription = subscriptions[0]
    subscription["TopicArn"].should.equal(topic_arn)
    subscription["Protocol"].should.equal("http")
    subscription["SubscriptionArn"].should.contain(topic_arn)
    subscription["Endpoint"].should.equal("http://example.com/")

    # Now unsubscribe the subscription
    conn.unsubscribe(SubscriptionArn=subscription["SubscriptionArn"])

    # And there should be zero subscriptions left
    subscriptions = conn.list_subscriptions()["Subscriptions"]
    subscriptions.should.have.length_of(0)


@mock_sns
def test_getting_subscriptions_by_topic():
    conn = boto3.client('sns', region_name='us-east-1')
    conn.create_topic(Name="topic1")
    conn.create_topic(Name="topic2")

    response = conn.list_topics()
    topics = response["Topics"]
    topic1_arn = topics[0]['TopicArn']
    topic2_arn = topics[1]['TopicArn']

    conn.subscribe(TopicArn=topic1_arn,
                   Protocol="http",
                   Endpoint="http://example1.com/")
    conn.subscribe(TopicArn=topic2_arn,
                   Protocol="http",
                   Endpoint="http://example2.com/")

    topic1_subscriptions = conn.list_subscriptions_by_topic(TopicArn=topic1_arn)[
        "Subscriptions"]
    topic1_subscriptions.should.have.length_of(1)
    topic1_subscriptions[0]['Endpoint'].should.equal("http://example1.com/")


@mock_sns
def test_subscription_paging():
    conn = boto3.client('sns', region_name='us-east-1')
    conn.create_topic(Name="topic1")

    response = conn.list_topics()
    topics = response["Topics"]
    topic1_arn = topics[0]['TopicArn']

    for index in range(DEFAULT_PAGE_SIZE + int(DEFAULT_PAGE_SIZE / 3)):
        conn.subscribe(TopicArn=topic1_arn,
                       Protocol='email',
                       Endpoint='email_' + str(index) + '@test.com')

    all_subscriptions = conn.list_subscriptions()
    all_subscriptions["Subscriptions"].should.have.length_of(DEFAULT_PAGE_SIZE)
    next_token = all_subscriptions["NextToken"]
    next_token.should.equal(str(DEFAULT_PAGE_SIZE))

    all_subscriptions = conn.list_subscriptions(NextToken=next_token)
    all_subscriptions["Subscriptions"].should.have.length_of(
        int(DEFAULT_PAGE_SIZE / 3))
    all_subscriptions.shouldnt.have("NextToken")

    topic1_subscriptions = conn.list_subscriptions_by_topic(
        TopicArn=topic1_arn)
    topic1_subscriptions["Subscriptions"].should.have.length_of(
        DEFAULT_PAGE_SIZE)
    next_token = topic1_subscriptions["NextToken"]
    next_token.should.equal(str(DEFAULT_PAGE_SIZE))

    topic1_subscriptions = conn.list_subscriptions_by_topic(
        TopicArn=topic1_arn, NextToken=next_token)
    topic1_subscriptions["Subscriptions"].should.have.length_of(
        int(DEFAULT_PAGE_SIZE / 3))
    topic1_subscriptions.shouldnt.have("NextToken")
