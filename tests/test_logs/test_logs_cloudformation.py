import json
from uuid import uuid4

import boto3
import pytest

from tests import aws_verified


@aws_verified
@pytest.mark.aws_verified
def test_tagging():
    logs_client = boto3.client("logs", region_name="us-east-1")
    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    log_group_name = f"/moto/test/{str(uuid4())}"

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "testGroup": {
                "Type": "AWS::Logs::LogGroup",
                "Properties": {
                    "LogGroupName": log_group_name,
                    "Tags": [{"Key": "foo", "Value": "bar"}],
                },
            }
        },
    }
    template_json = json.dumps(template)
    stack_name = f"moto-test-{str(uuid4())[0:6]}"
    cf_client.create_stack(
        StackName=stack_name,
        TemplateBody=template_json,
    )
    waiter = cf_client.get_waiter("stack_create_complete")
    waiter.wait(StackName=stack_name)

    group = logs_client.describe_log_groups(logGroupNamePrefix=log_group_name)[
        "logGroups"
    ][0]

    tags = logs_client.list_tags_for_resource(resourceArn=group["logGroupArn"])["tags"]
    assert tags["foo"] == "bar"

    cf_client.delete_stack(StackName=stack_name)
    waiter = cf_client.get_waiter("stack_delete_complete")
    waiter.wait(StackName=stack_name)
    assert (
        logs_client.describe_log_groups(logGroupNamePrefix=log_group_name)["logGroups"]
        == []
    )
