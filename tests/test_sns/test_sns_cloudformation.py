import json

import boto3
import pytest

from moto import mock_cloudformation, mock_sns


@mock_cloudformation
@mock_sns
def test_sns_topic():
    dummy_template = get_template(with_properties=True)
    template_json = json.dumps(dummy_template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    sns = boto3.client("sns", region_name="us-west-1")
    topics = sns.list_topics()["Topics"]
    assert len(topics) == 1
    topic_arn = topics[0]["TopicArn"]
    assert "my_topics" in topic_arn

    subscriptions = sns.list_subscriptions()["Subscriptions"]
    assert len(subscriptions) == 1
    subscription = subscriptions[0]
    assert subscription["TopicArn"] == topic_arn
    assert subscription["Protocol"] == "https"
    assert topic_arn in subscription["SubscriptionArn"]
    assert subscription["Endpoint"] == "https://example.com"

    stack = cf.describe_stacks(StackName="test_stack")["Stacks"][0]
    topic_name_output = [x for x in stack["Outputs"] if x["OutputKey"] == "topic_name"][
        0
    ]
    assert topic_name_output["OutputValue"] == "my_topics"
    topic_arn_output = [x for x in stack["Outputs"] if x["OutputKey"] == "topic_arn"][0]
    assert topic_arn_output["OutputValue"] == topic_arn


@mock_cloudformation
@mock_sns
def test_sns_update_topic():
    dummy_template = get_template(with_properties=True)
    sns_template_json = json.dumps(dummy_template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=sns_template_json)

    sns = boto3.client("sns", region_name="us-west-1")
    topics = sns.list_topics()["Topics"]
    assert len(topics) == 1

    dummy_template["Resources"]["MySNSTopic"]["Properties"]["Subscription"][0][
        "Endpoint"
    ] = "https://example-updated.com"
    sns_template_json = json.dumps(dummy_template)
    cf.update_stack(StackName="test_stack", TemplateBody=sns_template_json)

    topics = sns.list_topics()["Topics"]
    assert len(topics) == 1
    topic_arn = topics[0]["TopicArn"]
    assert "my_topics" in topic_arn

    subscriptions = sns.list_subscriptions()["Subscriptions"]
    assert len(subscriptions) == 1
    subscription = subscriptions[0]
    assert subscription["TopicArn"] == topic_arn
    assert subscription["Protocol"] == "https"
    assert topic_arn in subscription["SubscriptionArn"]
    assert subscription["Endpoint"] == "https://example-updated.com"


@mock_cloudformation
@mock_sns
@pytest.mark.parametrize("with_properties", [True, False])
def test_sns_update_remove_topic(with_properties):
    dummy_template = get_template(with_properties)
    sns_template_json = json.dumps(dummy_template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=sns_template_json)

    sns = boto3.client("sns", region_name="us-west-1")
    topics = sns.list_topics()["Topics"]
    assert len(topics) == 1

    dummy_template["Resources"].pop("MySNSTopic")
    dummy_template.pop("Outputs")
    sns_template_json = json.dumps(dummy_template)
    cf.update_stack(StackName="test_stack", TemplateBody=sns_template_json)

    topics = sns.list_topics()["Topics"]
    assert len(topics) == 0


@mock_cloudformation
@mock_sns
@pytest.mark.parametrize("with_properties", [True, False])
def test_sns_delete_topic(with_properties):
    sns_template_json = json.dumps(get_template(with_properties))
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=sns_template_json)

    sns = boto3.client("sns", region_name="us-west-1")
    topics = sns.list_topics()["Topics"]
    assert len(topics) == 1

    cf.delete_stack(StackName="test_stack")

    topics = sns.list_topics()["Topics"]
    assert len(topics) == 0


def get_template(with_properties):
    dummy_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {"MySNSTopic": {"Type": "AWS::SNS::Topic"}},
        "Outputs": {
            "topic_name": {"Value": {"Fn::GetAtt": ["MySNSTopic", "TopicName"]}},
            "topic_arn": {"Value": {"Ref": "MySNSTopic"}},
        },
    }
    if with_properties:
        dummy_template["Resources"]["MySNSTopic"]["Properties"] = {
            "Subscription": [{"Endpoint": "https://example.com", "Protocol": "https"}],
            "TopicName": "my_topics",
        }
    return dummy_template
