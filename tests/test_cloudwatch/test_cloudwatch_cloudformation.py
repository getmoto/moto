import json
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_cloudwatch_dashboard(account_id):
    # SETUP
    dashboard_name = str(uuid4())
    stack_name = f"Stack{str(uuid4())[0:6]}"
    dashboard_template_json = json.dumps(get_dashboard_template(dashboard_name))

    # CREATE
    cf = boto3.client("cloudformation", region_name="us-east-1")
    cf.create_stack(StackName=stack_name, TemplateBody=dashboard_template_json)

    # VERIFY
    cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")
    dashboard = cloudwatch.get_dashboard(DashboardName=dashboard_name)
    assert (
        dashboard["DashboardArn"]
        == f"arn:aws:cloudwatch::{account_id}:dashboard/{dashboard_name}"
    )

    # DELETE
    cf.delete_stack(StackName=stack_name)

    # VERIFY
    with pytest.raises(ClientError) as exc:
        cloudwatch.get_dashboard(DashboardName=dashboard_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFound"


def get_dashboard_template(name: str):
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "FirstDashboard": {
                "Type": "AWS::CloudWatch::Dashboard",
                "Properties": {"DashboardBody": "body", "DashboardName": name},
            }
        },
    }
