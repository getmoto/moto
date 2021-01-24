import boto3
import json
from moto import mock_cloudformation, mock_events
import sure  # noqa

from moto.core import ACCOUNT_ID


@mock_events
@mock_cloudformation
def test_create_archive():
    # given
    cfn_client = boto3.client("cloudformation", region_name="eu-central-1")
    name = "test-archive"
    stack_name = "test-stack"
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "EventBridge Archive Test",
        "Resources": {
            "Archive": {
                "Type": "AWS::Events::Archive",
                "Properties": {
                    "ArchiveName": name,
                    "SourceArn": {
                        "Fn::Sub": "arn:aws:events:${AWS::Region}:${AWS::AccountId}:event-bus/default"
                    },
                },
            },
        },
        "Outputs": {
            "Arn": {
                "Description": "Archive Arn",
                "Value": {"Fn::GetAtt": ["Archive", "Arn"]},
            }
        },
    }

    # when
    cfn_client.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    # then
    archive_arn = "arn:aws:events:eu-central-1:{0}:archive/{1}".format(ACCOUNT_ID, name)
    stack = cfn_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack["Outputs"][0]["OutputValue"].should.equal(archive_arn)

    events_client = boto3.client("events", region_name="eu-central-1")
    response = events_client.describe_archive(ArchiveName=name)

    response["ArchiveArn"].should.equal(archive_arn)
