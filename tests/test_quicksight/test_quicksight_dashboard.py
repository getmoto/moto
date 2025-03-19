import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_dashboard():
    client = boto3.client("quicksight", region_name="us-east-2")
    resp = client.create_dashboard(
        AwsAccountId=ACCOUNT_ID,
        DashboardId="my-test-dashboard",
        Name="My Test Dashboard",
    )

    assert resp["Arn"] == (
        f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:dashboard/my-test-dashboard"
    )
    assert resp["DashboardId"] == "my-test-dashboard"


@mock_aws
def test_describe_dashboard():
    client = boto3.client("quicksight", region_name="us-east-2")
    for i in range(3):
        client.create_dashboard(
            AwsAccountId=ACCOUNT_ID,
            DashboardId=f"my-test-dashboard-{i}",
            Name=f"My Test Dashboard {i}",
            VersionDescription="This is my test dashboard",
        )

    resp = client.describe_dashboard(
        AwsAccountId=ACCOUNT_ID, DashboardId="my-test-dashboard-1"
    )["Dashboard"]
    assert resp["Arn"] == (
        f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:dashboard/my-test-dashboard-1"
    )
    assert resp["DashboardId"] == "my-test-dashboard-1"
    assert resp["Name"] == "My Test Dashboard 1"
    assert "Version" in resp
    assert resp["Version"]["Status"] == "CREATION_SUCCESSFUL"
    assert resp["Version"]["VersionNumber"] == 1
    assert resp["Version"]["Description"] == "This is my test dashboard"


@mock_aws
def test_list_dashboards():
    client = boto3.client("quicksight", region_name="ap-southeast-1")
    for i in range(5):
        client.create_dashboard(
            AwsAccountId=ACCOUNT_ID,
            DashboardId=f"my-test-dashboard-{i}",
            Name=f"My Test Dashboard {i}",
        )

    resp = client.list_dashboards(AwsAccountId=ACCOUNT_ID)
    assert len(resp["DashboardSummaryList"]) == 5
    dashboard = resp["DashboardSummaryList"][0]
    assert "Arn" in dashboard
    assert "DashboardId" in dashboard
    assert "Name" in dashboard
    assert "CreatedTime" in dashboard
