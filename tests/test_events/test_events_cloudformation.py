import copy
import json
from string import Template
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import aws_verified

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

rule_with_targets = """---
AWSTemplateFormatVersion: 2010-09-09
Resources:
  MyEventBus:
    Type: AWS::Events::EventBus
    Properties:
      Name: "TestEventBusName"

  DestQueue:
    Type: AWS::SQS::Queue

  MyQueuePolicy:
    Type: AWS::SQS::QueuePolicy
    Properties:
      PolicyDocument:
          Version: 2012-10-17
          Statement:
            - Effect: Allow
              Principal:
                Service: events.amazonaws.com
              Action: sqs:SendMessage
              Resource: !GetAtt DestQueue.Arn
              Condition:
                ArnEquals:
                  aws:SourceArn: !GetAtt MyRule.Arn
            - Effect: Allow
              Principal:
                Service: events.amazonaws.com
              Action: sqs:SendMessage
              Resource: !GetAtt DestQueue.Arn
      Queues:
        - !Ref DestQueue

  MyRule:
    Type: AWS::Events::Rule
    Properties:
      EventBusName: !GetAtt MyEventBus.Name
      EventPattern:
        source:
          - my.source
        detail-type:
          - Malicious
      State: ENABLED
      Targets:
        - Id: meh
          Arn: !GetAtt DestQueue.Arn
          InputTransformer:
            InputPathsMap:
              account: $.account
              detail: $.detail
              detail-type: $.detail-type
              id: $.id
              region: $.region
              resources: $.resources
              time: $.time
            InputTemplate: '{\"id\": \"<id>\",\"detail-type\": \"<detail-type>\",\"time\":\"<time>\",\"region\": \"<region>\",\"account\": \"<account>\",\"resources\":<resources>,\"http_method\": \"POST\",\"http_endpoint\":\"/test/endpoint\",\"detail\":<detail>}'
"""


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


@aws_verified
@pytest.mark.aws_verified
def test_create_rule_with_targets():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    sqs_client = boto3.client("sqs", region_name="eu-central-1")
    sts = boto3.client("sts", "us-east-1")

    account_id = sts.get_caller_identity()["Account"]
    stack_name = f"test-stack-{str(uuid4())[0:6]}"

    # when
    cfn_client.create_stack(StackName=stack_name, TemplateBody=rule_with_targets)
    cfn_client.get_waiter("stack_create_complete").wait(StackName=stack_name)
    try:
        # then
        events_client = boto3.client("events", region_name="eu-central-1")
        rule = events_client.list_rules(EventBusName="TestEventBusName")["Rules"][0]

        targets = events_client.list_targets_by_rule(
            Rule=rule["Name"], EventBusName="TestEventBusName"
        )["Targets"]
        assert len(targets) == 1
        assert targets[0]["Id"] == "meh"
        assert targets[0]["InputTransformer"]["InputPathsMap"]["account"] == "$.account"

        resources = cfn_client.list_stack_resources(StackName=stack_name)[
            "StackResourceSummaries"
        ]
        queue = next((r for r in resources if r["LogicalResourceId"] == "DestQueue"))
        q_url = queue["PhysicalResourceId"]

        entry = dict(
            Detail='{"a": "b"}',
            DetailType="Malicious",
            EventBusName="TestEventBusName",
            Resources=["path/to/file"],
            Source="my.source",
        )
        entry_id = events_client.put_events(Entries=[entry])["Entries"][0]["EventId"]

        messages = sqs_client.receive_message(QueueUrl=q_url, WaitTimeSeconds=20)[
            "Messages"
        ]
        msg_body = json.loads(messages[0]["Body"])

        msg_body.pop("time")
        assert msg_body == {
            "id": entry_id,
            "detail-type": "Malicious",
            "region": "eu-central-1",
            "account": account_id,
            "resources": ["path/to/file"],
            "http_method": "POST",
            "http_endpoint": "/test/endpoint",
            "detail": {"a": "b"},
        }

    finally:
        cfn_client.delete_stack(StackName=stack_name)
        cfn_client.get_waiter("stack_delete_complete").wait(StackName=stack_name)

        with pytest.raises(ClientError) as exc:
            events_client.list_rules(EventBusName="TestEventBusName")
        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
