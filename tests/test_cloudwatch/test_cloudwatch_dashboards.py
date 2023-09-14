import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_cloudwatch


@mock_cloudwatch
def test_put_list_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    resp = client.list_dashboards()

    assert len(resp["DashboardEntries"]) == 1


@mock_cloudwatch
def test_put_list_prefix_nomatch_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    resp = client.list_dashboards(DashboardNamePrefix="nomatch")

    assert len(resp["DashboardEntries"]) == 0


@mock_cloudwatch
def test_delete_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    client.put_dashboard(DashboardName="test2", DashboardBody=widget)
    client.put_dashboard(DashboardName="test3", DashboardBody=widget)
    client.delete_dashboards(DashboardNames=["test2", "test1"])

    resp = client.list_dashboards(DashboardNamePrefix="test3")
    assert len(resp["DashboardEntries"]) == 1


@mock_cloudwatch
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


@mock_cloudwatch
def test_get_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'
    client.put_dashboard(DashboardName="test1", DashboardBody=widget)

    resp = client.get_dashboard(DashboardName="test1")
    assert "DashboardArn" in resp
    assert "DashboardBody" in resp
    assert resp["DashboardName"] == "test1"


@mock_cloudwatch
def test_get_dashboard_fail():
    client = boto3.client("cloudwatch", region_name="eu-central-1")

    with pytest.raises(ClientError) as exc:
        client.get_dashboard(DashboardName="test1")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFound"
