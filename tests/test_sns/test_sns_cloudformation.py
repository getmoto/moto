import boto3
import json
import sure  # noqa # pylint: disable=unused-import

from moto import mock_cloudformation, mock_sns


@mock_cloudformation
@mock_sns
def test_sns_topic():
    dummy_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MySNSTopic": {
                "Type": "AWS::SNS::Topic",
                "Properties": {
                    "Subscription": [
                        {"Endpoint": "https://example.com", "Protocol": "https"}
                    ],
                    "TopicName": "my_topics",
                },
            }
        },
        "Outputs": {
            "topic_name": {"Value": {"Fn::GetAtt": ["MySNSTopic", "TopicName"]}},
            "topic_arn": {"Value": {"Ref": "MySNSTopic"}},
        },
    }
    template_json = json.dumps(dummy_template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    sns = boto3.client("sns", region_name="us-west-1")
    topics = sns.list_topics()["Topics"]
    topics.should.have.length_of(1)
    topic_arn = topics[0]["TopicArn"]
    topic_arn.should.contain("my_topics")

    subscriptions = sns.list_subscriptions()["Subscriptions"]
    subscriptions.should.have.length_of(1)
    subscription = subscriptions[0]
    subscription["TopicArn"].should.equal(topic_arn)
    subscription["Protocol"].should.equal("https")
    subscription["SubscriptionArn"].should.contain(topic_arn)
    subscription["Endpoint"].should.equal("https://example.com")

    stack = cf.describe_stacks(StackName="test_stack")["Stacks"][0]
    topic_name_output = [x for x in stack["Outputs"] if x["OutputKey"] == "topic_name"][
        0
    ]
    topic_name_output["OutputValue"].should.equal("my_topics")
    topic_arn_output = [x for x in stack["Outputs"] if x["OutputKey"] == "topic_arn"][0]
    topic_arn_output["OutputValue"].should.equal(topic_arn)


@mock_cloudformation
@mock_sns
def test_sns_update_topic():
    dummy_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MySNSTopic": {
                "Type": "AWS::SNS::Topic",
                "Properties": {
                    "Subscription": [
                        {"Endpoint": "https://example.com", "Protocol": "https"}
                    ],
                    "TopicName": "my_topics",
                },
            }
        },
        "Outputs": {
            "topic_name": {"Value": {"Fn::GetAtt": ["MySNSTopic", "TopicName"]}},
            "topic_arn": {"Value": {"Ref": "MySNSTopic"}},
        },
    }
    sns_template_json = json.dumps(dummy_template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=sns_template_json)

    sns = boto3.client("sns", region_name="us-west-1")
    topics = sns.list_topics()["Topics"]
    topics.should.have.length_of(1)

    dummy_template["Resources"]["MySNSTopic"]["Properties"]["Subscription"][0][
        "Endpoint"
    ] = "https://example-updated.com"
    sns_template_json = json.dumps(dummy_template)
    cf.update_stack(StackName="test_stack", TemplateBody=sns_template_json)

    topics = sns.list_topics()["Topics"]
    topics.should.have.length_of(1)
    topic_arn = topics[0]["TopicArn"]
    topic_arn.should.contain("my_topics")

    subscriptions = sns.list_subscriptions()["Subscriptions"]
    subscriptions.should.have.length_of(1)
    subscription = subscriptions[0]
    subscription["TopicArn"].should.equal(topic_arn)
    subscription["Protocol"].should.equal("https")
    subscription["SubscriptionArn"].should.contain(topic_arn)
    subscription["Endpoint"].should.equal("https://example-updated.com")


@mock_cloudformation
@mock_sns
def test_sns_update_remove_topic():
    dummy_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MySNSTopic": {
                "Type": "AWS::SNS::Topic",
                "Properties": {
                    "Subscription": [
                        {"Endpoint": "https://example.com", "Protocol": "https"}
                    ],
                    "TopicName": "my_topics",
                },
            }
        },
        "Outputs": {
            "topic_name": {"Value": {"Fn::GetAtt": ["MySNSTopic", "TopicName"]}},
            "topic_arn": {"Value": {"Ref": "MySNSTopic"}},
        },
    }
    sns_template_json = json.dumps(dummy_template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=sns_template_json)

    sns = boto3.client("sns", region_name="us-west-1")
    topics = sns.list_topics()["Topics"]
    topics.should.have.length_of(1)

    dummy_template["Resources"].pop("MySNSTopic")
    dummy_template.pop("Outputs")
    sns_template_json = json.dumps(dummy_template)
    cf.update_stack(StackName="test_stack", TemplateBody=sns_template_json)

    topics = sns.list_topics()["Topics"]
    topics.should.have.length_of(0)


@mock_cloudformation
@mock_sns
def test_sns_delete_topic():
    dummy_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MySNSTopic": {
                "Type": "AWS::SNS::Topic",
                "Properties": {
                    "Subscription": [
                        {"Endpoint": "https://example.com", "Protocol": "https"}
                    ],
                    "TopicName": "my_topics",
                },
            }
        },
        "Outputs": {
            "topic_name": {"Value": {"Fn::GetAtt": ["MySNSTopic", "TopicName"]}},
            "topic_arn": {"Value": {"Ref": "MySNSTopic"}},
        },
    }
    sns_template_json = json.dumps(dummy_template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=sns_template_json)

    sns = boto3.client("sns", region_name="us-west-1")
    topics = sns.list_topics()["Topics"]
    topics.should.have.length_of(1)

    cf.delete_stack(StackName="test_stack")

    topics = sns.list_topics()["Topics"]
    topics.should.have.length_of(0)
