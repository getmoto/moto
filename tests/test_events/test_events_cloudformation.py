import pytest
import copy
from string import Template

import boto3
import json
from botocore.exceptions import ClientError
from moto import mock_cloudformation, mock_events
import sure  # noqa

from moto.core import ACCOUNT_ID

archive_template = Template(
    json.dumps(
        {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "EventBridge Archive Test",
            "Resources": {
                "Archive": {
                    "Type": "AWS::Events::Archive",
                    "Properties": {
                        "ArchiveName": "${archive_name}",
                        "SourceArn": {
                            "Fn::Sub": "arn:aws:events:$${AWS::Region}:$${AWS::AccountId}:event-bus/default"
                        },
                    },
                }
            },
            "Outputs": {
                "Arn": {
                    "Description": "Archive Arn",
                    "Value": {"Fn::GetAtt": ["Archive", "Arn"]},
                }
            },
        }
    )
)


rule_template = Template(
    json.dumps(
        {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "EventBridge Rule Test",
            "Resources": {
                "Rule": {
                    "Type": "AWS::Events::Rule",
                    "Properties": {
                        "Name": "${rule_name}",
                        "EventPattern": {"detail-type": ["SomeDetailType"]},
                    },
                }
            },
            "Outputs": {
                "Arn": {
                    "Description": "Rule Arn",
                    "Value": {"Fn::GetAtt": ["Rule", "Arn"]},
                }
            },
        }
    )
)


empty = json.dumps(
    {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "EventBridge Rule Test",
        "Resources": {},
    }
)


@mock_events
@mock_cloudformation
def test_create_archive():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-archive"
    stack_name = "test-stack"
    template = archive_template.substitute({"archive_name": name})

    # when
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    # then
    archive_arn = "arn:aws:events:eu-central-1:{0}:archive/{1}".format(ACCOUNT_ID, name)
    stack = cfn_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack["Outputs"][0]["OutputValue"].should.equal(archive_arn)

    events_client = boto3.client("events", region_name="eu-central-1")
    response = events_client.describe_archive(ArchiveName=name)

    response["ArchiveArn"].should.equal(archive_arn)


@mock_events
@mock_cloudformation
def test_update_archive():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-archive"
    stack_name = "test-stack"
    template = archive_template.substitute({"archive_name": name})
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    template_update = copy.deepcopy(json.loads(template))
    template_update["Resources"]["Archive"]["Properties"][
        "Description"
    ] = "test archive"

    # when
    cfn_client.update_stack(
        StackName=stack_name, TemplateBody=json.dumps(template_update)
    )

    # then
    events_client = boto3.client("events", region_name="eu-central-1")
    response = events_client.describe_archive(ArchiveName=name)

    response["ArchiveArn"].should.equal(
        "arn:aws:events:eu-central-1:{0}:archive/{1}".format(ACCOUNT_ID, name)
    )
    response["Description"].should.equal("test archive")


@mock_events
@mock_cloudformation
def test_delete_archive():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-archive"
    stack_name = "test-stack"
    template = archive_template.substitute({"archive_name": name})
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    # when
    cfn_client.delete_stack(StackName=stack_name)

    # then
    events_client = boto3.client("events", region_name="eu-central-1")
    response = events_client.list_archives(NamePrefix="test")["Archives"]
    response.should.have.length_of(0)


@mock_events
@mock_cloudformation
def test_create_rule():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-rule"
    stack_name = "test-stack"
    template = rule_template.substitute({"rule_name": name})

    # when
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    # then
    rule_arn = "arn:aws:events:eu-central-1:{0}:rule/{1}".format(ACCOUNT_ID, name)
    stack = cfn_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack["Outputs"][0]["OutputValue"].should.equal(rule_arn)

    events_client = boto3.client("events", region_name="eu-central-1")
    response = events_client.describe_rule(Name=name)

    response["Arn"].should.equal(rule_arn)
    response["EventPattern"].should.equal('{"detail-type": ["SomeDetailType"]}')


@mock_events
@mock_cloudformation
def test_delete_rule():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-rule"
    stack_name = "test-stack"
    template = rule_template.substitute({"rule_name": name})
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    # when
    cfn_client.update_stack(StackName=stack_name, TemplateBody=empty)

    # then
    events_client = boto3.client("events", region_name="eu-central-1")

    with pytest.raises(ClientError, match="does not exist") as e:

        events_client.describe_rule(Name=name)
