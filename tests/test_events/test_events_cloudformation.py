import copy
import json
from string import Template

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

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


@mock_aws
def test_create_archive():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-archive"
    stack_name = "test-stack"
    template = archive_template.substitute({"archive_name": name})

    # when
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    # then
    archive_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:archive/{name}"
    stack = cfn_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    assert stack["Outputs"][0]["OutputValue"] == archive_arn

    events_client = boto3.client("events", region_name="eu-central-1")
    response = events_client.describe_archive(ArchiveName=name)

    assert response["ArchiveArn"] == archive_arn


@mock_aws
def test_update_archive():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-archive"
    stack_name = "test-stack"
    template = archive_template.substitute({"archive_name": name})
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    template_update = copy.deepcopy(json.loads(template))
    template_update["Resources"]["Archive"]["Properties"]["Description"] = (
        "test archive"
    )

    # when
    cfn_client.update_stack(
        StackName=stack_name, TemplateBody=json.dumps(template_update)
    )

    # then
    events_client = boto3.client("events", region_name="eu-central-1")
    response = events_client.describe_archive(ArchiveName=name)

    assert (
        response["ArchiveArn"]
        == f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:archive/{name}"
    )
    assert response["Description"] == "test archive"


@mock_aws
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
    assert len(response) == 0


@mock_aws
def test_create_rule():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-rule"
    stack_name = "test-stack"
    template = rule_template.substitute({"rule_name": name})

    # when
    cfn_client.create_stack(StackName=stack_name, TemplateBody=template)

    # then
    rule_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:rule/{name}"
    stack = cfn_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    assert stack["Outputs"][0]["OutputValue"] == rule_arn

    events_client = boto3.client("events", region_name="eu-central-1")
    response = events_client.describe_rule(Name=name)

    assert response["Arn"] == rule_arn
    assert response["EventPattern"] == '{"detail-type": ["SomeDetailType"]}'


@mock_aws
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

    with pytest.raises(ClientError) as exc:
        events_client.describe_rule(Name=name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Rule test-rule does not exist."
