from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_list_report_plans():
    client = boto3.client("backup", "us-east-1")

    plans = client.list_report_plans()["ReportPlans"]
    assert plans == []


@mock_aws
def test_create_report_plan():
    client = boto3.client("backup", "us-east-1")

    plan_name = "RP_" + str(uuid4()).replace("-", "_")
    create = client.create_report_plan(
        ReportPlanName=plan_name,
        ReportDeliveryChannel={"S3BucketName": "mybucket"},
        ReportSetting={"ReportTemplate": "RESOURCE_COMPLIANCE_REPORT"},
    )
    assert create["ReportPlanName"] == plan_name

    get = client.describe_report_plan(ReportPlanName=plan_name)["ReportPlan"]

    assert get["ReportSetting"] == {"ReportTemplate": "RESOURCE_COMPLIANCE_REPORT"}
    assert get["ReportDeliveryChannel"] == {"S3BucketName": "mybucket"}


@mock_aws
def test_delete_report_plan():
    client = boto3.client("backup", "us-east-1")

    plan_name = "RP_" + str(uuid4()).replace("-", "_")
    client.create_report_plan(
        ReportPlanName=plan_name,
        ReportDeliveryChannel={"S3BucketName": "mybucket"},
        ReportSetting={"ReportTemplate": "RESOURCE_COMPLIANCE_REPORT"},
    )

    client.delete_report_plan(ReportPlanName=plan_name)

    with pytest.raises(ClientError) as exc:
        client.describe_report_plan(ReportPlanName=plan_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
