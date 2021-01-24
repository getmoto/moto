import boto3
import json
from moto import mock_cloudformation, mock_events
import sure  # noqa


@mock_events
@mock_cloudformation
def test_create_archive():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "EventBridge Archive Test",
        "Resources": {
            "archive": {
                "Type": "AWS::Events::Archive",
                "Properties": {
                    "ArchiveName": "test-archive",
                    "SourceArn": {
                        "Fn::Sub": "arn:aws:events:${AWS::Region}:${AWS::AccountId}:event-bus/default"
                    },
                },
            },
        },
    }

    # when
    cfn_client.create_stack(StackName="test-stack", TemplateBody=json.dumps(template))

    # then
    events_client = boto3.client("events", region_name="eu-central-1")
    # ToDo: implement check, when list or describe method is implemented
