import json

import boto3

from moto import mock_aws


@mock_aws
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
    }
    template_json = json.dumps(template)
    cf_client.create_stack(
        StackName="test_stack",
        TemplateBody=template_json,
    )

    arn = logs_client.describe_log_groups()["logGroups"][0]["arn"]
    tags = logs_client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert tags == {"foo": "bar"}

    cf_client.delete_stack(StackName="test_stack")
    assert logs_client.describe_log_groups()["logGroups"] == []
