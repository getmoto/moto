import json
import re

import boto3

from moto import mock_cloudformation, mock_logs


@mock_logs
@mock_cloudformation
def test_tagging():
    logs_client = boto3.client("logs", region_name="us-east-1")
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "testGroup": {
                "Type": "AWS::Logs::LogGroup",
                "Properties": {"Tags": [{"Key": "foo", "Value": "bar"}]},
            }
        },
        "Outputs": {"LogGroup": {"Value": {"Ref": "testGroup"}}},
    }
    template_json = json.dumps(template)
    cf_client.create_stack(
        StackName="test_stack",
        TemplateBody=template_json,
    )
    stack_description = cf_client.describe_stacks(StackName="test_stack")["Stacks"][0]

    arn = logs_client.describe_log_groups()["logGroups"][0]["arn"]
    tags = logs_client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert tags == {"foo": "bar"}
