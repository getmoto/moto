import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
@pytest.mark.parametrize(
    "region,partition", [("eu-central-1", "aws"), ("cn-north-1", "aws-cn")]
)
def test_put_list_dashboard(region, partition):
    client = boto3.client("cloudwatch", region_name=region)
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    dashboards = client.list_dashboards()["DashboardEntries"]

    assert len(dashboards) == 1
    assert (
        dashboards[0]["DashboardArn"]
        == f"arn:{partition}:cloudwatch::123456789012:dashboard/test1"
    )


@mock_aws
def test_put_list_prefix_nomatch_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    resp = client.list_dashboards(DashboardNamePrefix="nomatch")

    assert len(resp["DashboardEntries"]) == 0


@mock_aws
def test_delete_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    client.put_dashboard(DashboardName="test2", DashboardBody=widget)
    client.put_dashboard(DashboardName="test3", DashboardBody=widget)
    client.delete_dashboards(DashboardNames=["test2", "test1"])

    resp = client.list_dashboards(DashboardNamePrefix="test3")
    assert len(resp["DashboardEntries"]) == 1


@mock_aws
def test_delete_dashboard_fail():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    client.put_dashboard(DashboardName="test2", DashboardBody=widget)
    client.put_dashboard(DashboardName="test3", DashboardBody=widget)
    # Doesn't delete anything if some dashboards to be deleted do not exist
    with pytest.raises(ClientError) as exc:
        client.delete_dashboards(DashboardNames=["test2", "test1", "test_no_match"])
    assert exc.value.response["Error"]["Code"] == "ResourceNotFound"

    resp = client.list_dashboards()
    assert len(resp["DashboardEntries"]) == 3


@mock_aws
def test_get_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'
    client.put_dashboard(DashboardName="test1", DashboardBody=widget)

    resp = client.get_dashboard(DashboardName="test1")
    assert "DashboardArn" in resp
    assert "DashboardBody" in resp
    assert resp["DashboardName"] == "test1"


@mock_aws
def test_get_dashboard_fail():
    client = boto3.client("cloudwatch", region_name="eu-central-1")

    with pytest.raises(ClientError) as exc:
        client.get_dashboard(DashboardName="test1")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFound"
