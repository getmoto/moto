from __future__ import unicode_literals
import boto3
import six
import json

import sure  # noqa

from botocore.exceptions import ClientError
from moto import mock_sns
from moto.sns.models import DEFAULT_TOPIC_POLICY, DEFAULT_EFFECTIVE_DELIVERY_POLICY, DEFAULT_PAGE_SIZE


@mock_sns
def test_create_and_delete_topic():
    conn = boto3.client("sns", region_name="us-east-1")
    for topic_name in ('some-topic', '-some-topic-', '_some-topic_', 'a' * 256):
        conn.create_topic(Name=topic_name)

        topics_json = conn.list_topics()
        topics = topics_json["Topics"]
        topics.should.have.length_of(1)
        topics[0]['TopicArn'].should.equal(
            "arn:aws:sns:{0}:123456789012:{1}"
            .format(conn._client_config.region_name, topic_name)
        )

        # Delete the topic
        conn.delete_topic(TopicArn=topics[0]['TopicArn'])

        # And there should now be 0 topics
        topics_json = conn.list_topics()
        topics = topics_json["Topics"]
        topics.should.have.length_of(0)


@mock_sns
def test_create_topic_with_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name='some-topic-with-attribute', Attributes={'DisplayName': 'test-topic'})
    topics_json = conn.list_topics()
    topic_arn = topics_json["Topics"][0]['TopicArn']

    attributes = conn.get_topic_attributes(TopicArn=topic_arn)['Attributes']
    attributes['DisplayName'].should.equal('test-topic')


@mock_sns
def test_create_topic_should_be_indempodent():
    conn = boto3.client("sns", region_name="us-east-1")
    topic_arn = conn.create_topic(Name="some-topic")['TopicArn']
    conn.set_topic_attributes(
        TopicArn=topic_arn,
        AttributeName="DisplayName",
        AttributeValue="should_be_set"
    )
    topic_display_name = conn.get_topic_attributes(
        TopicArn=topic_arn
    )['Attributes']['DisplayName']
    topic_display_name.should.be.equal("should_be_set")

    #recreate topic to prove indempodentcy
    topic_arn = conn.create_topic(Name="some-topic")['TopicArn']
    topic_display_name = conn.get_topic_attributes(
        TopicArn=topic_arn
    )['Attributes']['DisplayName']
    topic_display_name.should.be.equal("should_be_set")

@mock_sns
def test_get_missing_topic():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.get_topic_attributes.when.called_with(
        TopicArn="a-fake-arn").should.throw(ClientError)

@mock_sns
def test_create_topic_must_meet_constraints():
    conn = boto3.client("sns", region_name="us-east-1")
    common_random_chars = [':', ";", "!", "@", "|", "^", "%"]
    for char in common_random_chars:
        conn.create_topic.when.called_with(
            Name="no%s_invalidchar" % char).should.throw(ClientError)
    conn.create_topic.when.called_with(
            Name="no spaces allowed").should.throw(ClientError)


@mock_sns
def test_create_topic_should_be_of_certain_length():
    conn = boto3.client("sns", region_name="us-east-1")
    too_short = ""
    conn.create_topic.when.called_with(
            Name=too_short).should.throw(ClientError)
    too_long = "x" * 257
    conn.create_topic.when.called_with(
            Name=too_long).should.throw(ClientError)


@mock_sns
def test_create_topic_in_multiple_regions():
    for region in ['us-west-1', 'us-west-2']:
        conn = boto3.client("sns", region_name=region)
        conn.create_topic(Name="some-topic")
        list(conn.list_topics()["Topics"]).should.have.length_of(1)


@mock_sns
def test_topic_corresponds_to_region():
    for region in ['us-east-1', 'us-west-2']:
        conn = boto3.client("sns", region_name=region)
        conn.create_topic(Name="some-topic")
        topics_json = conn.list_topics()
        topic_arn = topics_json["Topics"][0]['TopicArn']
        topic_arn.should.equal(
            "arn:aws:sns:{0}:123456789012:some-topic".format(region))


@mock_sns
def test_topic_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_topic(Name="some-topic")

    topics_json = conn.list_topics()
    topic_arn = topics_json["Topics"][0]['TopicArn']

    attributes = conn.get_topic_attributes(TopicArn=topic_arn)['Attributes']
    attributes["TopicArn"].should.equal(
        "arn:aws:sns:{0}:123456789012:some-topic"
        .format(conn._client_config.region_name)
    )
    attributes["Owner"].should.equal('123456789012')
    json.loads(attributes["Policy"]).should.equal(DEFAULT_TOPIC_POLICY)
    attributes["DisplayName"].should.equal("")
    attributes["SubscriptionsPending"].should.equal('0')
    attributes["SubscriptionsConfirmed"].should.equal('0')
    attributes["SubscriptionsDeleted"].should.equal('0')
    attributes["DeliveryPolicy"].should.equal("")
    json.loads(attributes["EffectiveDeliveryPolicy"]).should.equal(
        DEFAULT_EFFECTIVE_DELIVERY_POLICY)

    # boto can't handle prefix-mandatory strings:
    # i.e. unicode on Python 2 -- u"foobar"
    # and bytes on Python 3 -- b"foobar"
    if six.PY2:
        policy = json.dumps({b"foo": b"bar"})
        displayname = b"My display name"
        delivery = json.dumps(
            {b"http": {b"defaultHealthyRetryPolicy": {b"numRetries": 5}}})
    else:
        policy = json.dumps({u"foo": u"bar"})
        displayname = u"My display name"
        delivery = json.dumps(
            {u"http": {u"defaultHealthyRetryPolicy": {u"numRetries": 5}}})
    conn.set_topic_attributes(TopicArn=topic_arn,
                              AttributeName="Policy",
                              AttributeValue=policy)
    conn.set_topic_attributes(TopicArn=topic_arn,
                              AttributeName="DisplayName",
                              AttributeValue=displayname)
    conn.set_topic_attributes(TopicArn=topic_arn,
                              AttributeName="DeliveryPolicy",
                              AttributeValue=delivery)

    attributes = conn.get_topic_attributes(TopicArn=topic_arn)['Attributes']
    attributes["Policy"].should.equal('{"foo": "bar"}')
    attributes["DisplayName"].should.equal("My display name")
    attributes["DeliveryPolicy"].should.equal(
        '{"http": {"defaultHealthyRetryPolicy": {"numRetries": 5}}}')


@mock_sns
def test_topic_paging():
    conn = boto3.client("sns", region_name="us-east-1")
    for index in range(DEFAULT_PAGE_SIZE + int(DEFAULT_PAGE_SIZE / 2)):
        conn.create_topic(Name="some-topic_" + str(index))

    response = conn.list_topics()
    topics_list = response["Topics"]
    next_token = response["NextToken"]

    len(topics_list).should.equal(DEFAULT_PAGE_SIZE)
    int(next_token).should.equal(DEFAULT_PAGE_SIZE)

    response = conn.list_topics(NextToken=next_token)
    topics_list = response["Topics"]
    response.shouldnt.have("NextToken")

    topics_list.should.have.length_of(int(DEFAULT_PAGE_SIZE / 2))


@mock_sns
def test_add_remove_permissions():
    conn = boto3.client('sns', region_name='us-east-1')
    response = conn.create_topic(Name='testpermissions')

    conn.add_permission(
        TopicArn=response['TopicArn'],
        Label='Test1234',
        AWSAccountId=['999999999999'],
        ActionName=['AddPermission']
    )
    conn.remove_permission(
        TopicArn=response['TopicArn'],
        Label='Test1234'
    )
