from __future__ import unicode_literals
import boto
import json
import six

import sure  # noqa

from boto.exception import BotoServerError
from moto import mock_sns_deprecated
from moto.sns.models import DEFAULT_EFFECTIVE_DELIVERY_POLICY, DEFAULT_PAGE_SIZE
from moto.core import ACCOUNT_ID


@mock_sns_deprecated
def test_create_and_delete_topic():
    conn = boto.connect_sns()
    conn.create_topic("some-topic")

    topics_json = conn.get_all_topics()
    topics = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"]
    topics.should.have.length_of(1)
    topics[0]["TopicArn"].should.equal(
        "arn:aws:sns:{0}:{1}:some-topic".format(conn.region.name, ACCOUNT_ID)
    )

    # Delete the topic
    conn.delete_topic(topics[0]["TopicArn"])

    # And there should now be 0 topics
    topics_json = conn.get_all_topics()
    topics = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"]
    topics.should.have.length_of(0)


@mock_sns_deprecated
def test_delete_non_existent_topic():
    conn = boto.connect_sns()
    conn.delete_topic.when.called_with("a-fake-arn").should.throw(BotoServerError)


@mock_sns_deprecated
def test_get_missing_topic():
    conn = boto.connect_sns()
    conn.get_topic_attributes.when.called_with("a-fake-arn").should.throw(
        BotoServerError
    )


@mock_sns_deprecated
def test_create_topic_in_multiple_regions():
    for region in ["us-west-1", "us-west-2"]:
        conn = boto.sns.connect_to_region(region)
        conn.create_topic("some-topic")
        list(
            conn.get_all_topics()["ListTopicsResponse"]["ListTopicsResult"]["Topics"]
        ).should.have.length_of(1)


@mock_sns_deprecated
def test_topic_corresponds_to_region():
    for region in ["us-east-1", "us-west-2"]:
        conn = boto.sns.connect_to_region(region)
        conn.create_topic("some-topic")
        topics_json = conn.get_all_topics()
        topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0][
            "TopicArn"
        ]
        topic_arn.should.equal(
            "arn:aws:sns:{0}:{1}:some-topic".format(region, ACCOUNT_ID)
        )


@mock_sns_deprecated
def test_topic_attributes():
    conn = boto.connect_sns()
    conn.create_topic("some-topic")

    topics_json = conn.get_all_topics()
    topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0][
        "TopicArn"
    ]

    attributes = conn.get_topic_attributes(topic_arn)["GetTopicAttributesResponse"][
        "GetTopicAttributesResult"
    ]["Attributes"]
    attributes["TopicArn"].should.equal(
        "arn:aws:sns:{0}:{1}:some-topic".format(conn.region.name, ACCOUNT_ID)
    )
    attributes["Owner"].should.equal(ACCOUNT_ID)
    json.loads(attributes["Policy"]).should.equal(
        {
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
                    "Resource": "arn:aws:sns:us-east-1:{}:some-topic".format(
                        ACCOUNT_ID
                    ),
                    "Condition": {"StringEquals": {"AWS:SourceOwner": ACCOUNT_ID}},
                }
            ],
        }
    )
    attributes["DisplayName"].should.equal("")
    attributes["SubscriptionsPending"].should.equal(0)
    attributes["SubscriptionsConfirmed"].should.equal(0)
    attributes["SubscriptionsDeleted"].should.equal(0)
    attributes["DeliveryPolicy"].should.equal("")
    json.loads(attributes["EffectiveDeliveryPolicy"]).should.equal(
        DEFAULT_EFFECTIVE_DELIVERY_POLICY
    )

    # boto can't handle prefix-mandatory strings:
    # i.e. unicode on Python 2 -- u"foobar"
    # and bytes on Python 3 -- b"foobar"
    if six.PY2:
        policy = json.dumps({b"foo": b"bar"})
        displayname = b"My display name"
        delivery = {b"http": {b"defaultHealthyRetryPolicy": {b"numRetries": 5}}}
    else:
        policy = json.dumps({"foo": "bar"})
        displayname = "My display name"
        delivery = {"http": {"defaultHealthyRetryPolicy": {"numRetries": 5}}}
    conn.set_topic_attributes(topic_arn, "Policy", policy)
    conn.set_topic_attributes(topic_arn, "DisplayName", displayname)
    conn.set_topic_attributes(topic_arn, "DeliveryPolicy", delivery)

    attributes = conn.get_topic_attributes(topic_arn)["GetTopicAttributesResponse"][
        "GetTopicAttributesResult"
    ]["Attributes"]
    attributes["Policy"].should.equal('{"foo": "bar"}')
    attributes["DisplayName"].should.equal("My display name")
    attributes["DeliveryPolicy"].should.equal(
        "{'http': {'defaultHealthyRetryPolicy': {'numRetries': 5}}}"
    )


@mock_sns_deprecated
def test_topic_paging():
    conn = boto.connect_sns()
    for index in range(DEFAULT_PAGE_SIZE + int(DEFAULT_PAGE_SIZE / 2)):
        conn.create_topic("some-topic_" + str(index))

    topics_json = conn.get_all_topics()
    topics_list = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"]
    next_token = topics_json["ListTopicsResponse"]["ListTopicsResult"]["NextToken"]

    len(topics_list).should.equal(DEFAULT_PAGE_SIZE)
    next_token.should.equal(DEFAULT_PAGE_SIZE)

    topics_json = conn.get_all_topics(next_token=next_token)
    topics_list = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"]
    next_token = topics_json["ListTopicsResponse"]["ListTopicsResult"]["NextToken"]

    topics_list.should.have.length_of(int(DEFAULT_PAGE_SIZE / 2))
    next_token.should.equal(None)
