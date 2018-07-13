from __future__ import unicode_literals
import boto3
import json

import sure  # noqa

from botocore.exceptions import ClientError
from nose.tools import assert_raises

from moto import mock_sns
from moto.sns.models import DEFAULT_PAGE_SIZE


@mock_sns
def test_subscribe_sms():
    client = boto3.client('sns', region_name='us-east-1')
    client.create_topic(Name="some-topic")
    resp = client.create_topic(Name="some-topic")
    arn = resp['TopicArn']

    resp = client.subscribe(
        TopicArn=arn,
        Protocol='sms',
        Endpoint='+15551234567'
    )
    resp.should.contain('SubscriptionArn')

@mock_sns
def test_double_subscription():
    client = boto3.client('sns', region_name='us-east-1')
    client.create_topic(Name="some-topic")
    resp = client.create_topic(Name="some-topic")
    arn = resp['TopicArn']

    do_subscribe_sqs = lambda sqs_arn: client.subscribe(
        TopicArn=arn,
        Protocol='sqs',
        Endpoint=sqs_arn
    )
    resp1 = do_subscribe_sqs('arn:aws:sqs:elasticmq:000000000000:foo')
    resp2 = do_subscribe_sqs('arn:aws:sqs:elasticmq:000000000000:foo')

    resp1['SubscriptionArn'].should.equal(resp2['SubscriptionArn'])


@mock_sns
def test_subscribe_bad_sms():
    client = boto3.client('sns', region_name='us-east-1')
    client.create_topic(Name="some-topic")
    resp = client.create_topic(Name="some-topic")
    arn = resp['TopicArn']

    try:
        # Test invalid number
        client.subscribe(
            TopicArn=arn,
            Protocol='sms',
            Endpoint='NAA+15551234567'
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('InvalidParameter')


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
def test_deleting_subscriptions_by_deleting_topic():
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

    # Now delete the topic
    conn.delete_topic(TopicArn=topic_arn)

    # And there should now be 0 topics
    topics_json = conn.list_topics()
    topics = topics_json["Topics"]
    topics.should.have.length_of(0)

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


@mock_sns
def test_creating_subscription_with_attributes():
    conn = boto3.client('sns', region_name='us-east-1')
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]['TopicArn']

    delivery_policy = json.dumps({
        'healthyRetryPolicy': {
            "numRetries": 10,
            "minDelayTarget": 1,
            "maxDelayTarget":2
        }
    })

    filter_policy = json.dumps({
        "store": ["example_corp"],
        "event": ["order_cancelled"],
        "encrypted": [False],
        "customer_interests": ["basketball", "baseball"]
    })

    conn.subscribe(TopicArn=topic_arn,
                   Protocol="http",
                   Endpoint="http://example.com/",
                   Attributes={
                       'RawMessageDelivery': 'true',
                       'DeliveryPolicy': delivery_policy,
                       'FilterPolicy': filter_policy
                   })

    subscriptions = conn.list_subscriptions()["Subscriptions"]
    subscriptions.should.have.length_of(1)
    subscription = subscriptions[0]
    subscription["TopicArn"].should.equal(topic_arn)
    subscription["Protocol"].should.equal("http")
    subscription["SubscriptionArn"].should.contain(topic_arn)
    subscription["Endpoint"].should.equal("http://example.com/")

    # Test the subscription attributes have been set
    subscription_arn = subscription["SubscriptionArn"]
    attrs = conn.get_subscription_attributes(
        SubscriptionArn=subscription_arn
    )

    attrs['Attributes']['RawMessageDelivery'].should.equal('true')
    attrs['Attributes']['DeliveryPolicy'].should.equal(delivery_policy)
    attrs['Attributes']['FilterPolicy'].should.equal(filter_policy)

    # Now unsubscribe the subscription
    conn.unsubscribe(SubscriptionArn=subscription["SubscriptionArn"])

    # And there should be zero subscriptions left
    subscriptions = conn.list_subscriptions()["Subscriptions"]
    subscriptions.should.have.length_of(0)

    # invalid attr name
    with assert_raises(ClientError):
        conn.subscribe(TopicArn=topic_arn,
                       Protocol="http",
                       Endpoint="http://example.com/",
                       Attributes={
                           'InvalidName': 'true'
                       })


@mock_sns
def test_set_subscription_attributes():
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

    subscription_arn = subscription["SubscriptionArn"]
    attrs = conn.get_subscription_attributes(
        SubscriptionArn=subscription_arn
    )
    attrs.should.have.key('Attributes')
    conn.set_subscription_attributes(
        SubscriptionArn=subscription_arn,
        AttributeName='RawMessageDelivery',
        AttributeValue='true'
    )
    delivery_policy = json.dumps({
        'healthyRetryPolicy': {
            "numRetries": 10,
            "minDelayTarget": 1,
            "maxDelayTarget":2
        }
    })
    conn.set_subscription_attributes(
        SubscriptionArn=subscription_arn,
        AttributeName='DeliveryPolicy',
        AttributeValue=delivery_policy
    )

    filter_policy = json.dumps({
        "store": ["example_corp"],
        "event": ["order_cancelled"],
        "encrypted": [False],
        "customer_interests": ["basketball", "baseball"]
    })
    conn.set_subscription_attributes(
        SubscriptionArn=subscription_arn,
        AttributeName='FilterPolicy',
        AttributeValue=filter_policy
    )

    attrs = conn.get_subscription_attributes(
        SubscriptionArn=subscription_arn
    )

    attrs['Attributes']['RawMessageDelivery'].should.equal('true')
    attrs['Attributes']['DeliveryPolicy'].should.equal(delivery_policy)
    attrs['Attributes']['FilterPolicy'].should.equal(filter_policy)

    # not existing subscription
    with assert_raises(ClientError):
        conn.set_subscription_attributes(
            SubscriptionArn='invalid',
            AttributeName='RawMessageDelivery',
            AttributeValue='true'
        )
    with assert_raises(ClientError):
        attrs = conn.get_subscription_attributes(
            SubscriptionArn='invalid'
        )


    # invalid attr name
    with assert_raises(ClientError):
        conn.set_subscription_attributes(
            SubscriptionArn=subscription_arn,
            AttributeName='InvalidName',
            AttributeValue='true'
        )


@mock_sns
def test_check_not_opted_out():
    conn = boto3.client('sns', region_name='us-east-1')
    response = conn.check_if_phone_number_is_opted_out(phoneNumber='+447428545375')

    response.should.contain('isOptedOut')
    response['isOptedOut'].should.be(False)


@mock_sns
def test_check_opted_out():
    # Phone number ends in 99 so is hardcoded in the endpoint to return opted
    # out status
    conn = boto3.client('sns', region_name='us-east-1')
    response = conn.check_if_phone_number_is_opted_out(phoneNumber='+447428545399')

    response.should.contain('isOptedOut')
    response['isOptedOut'].should.be(True)


@mock_sns
def test_check_opted_out_invalid():
    conn = boto3.client('sns', region_name='us-east-1')

    # Invalid phone number
    with assert_raises(ClientError):
        conn.check_if_phone_number_is_opted_out(phoneNumber='+44742LALALA')


@mock_sns
def test_list_opted_out():
    conn = boto3.client('sns', region_name='us-east-1')
    response = conn.list_phone_numbers_opted_out()

    response.should.contain('phoneNumbers')
    len(response['phoneNumbers']).should.be.greater_than(0)


@mock_sns
def test_opt_in():
    conn = boto3.client('sns', region_name='us-east-1')
    response = conn.list_phone_numbers_opted_out()
    current_len = len(response['phoneNumbers'])
    assert current_len > 0

    conn.opt_in_phone_number(phoneNumber=response['phoneNumbers'][0])

    response = conn.list_phone_numbers_opted_out()
    len(response['phoneNumbers']).should.be.greater_than(0)
    len(response['phoneNumbers']).should.be.lower_than(current_len)


@mock_sns
def test_confirm_subscription():
    conn = boto3.client('sns', region_name='us-east-1')
    response = conn.create_topic(Name='testconfirm')

    conn.confirm_subscription(
        TopicArn=response['TopicArn'],
        Token='2336412f37fb687f5d51e6e241d59b68c4e583a5cee0be6f95bbf97ab8d2441cf47b99e848408adaadf4c197e65f03473d53c4ba398f6abbf38ce2e8ebf7b4ceceb2cd817959bcde1357e58a2861b05288c535822eb88cac3db04f592285249971efc6484194fc4a4586147f16916692',
        AuthenticateOnUnsubscribe='true'
    )
