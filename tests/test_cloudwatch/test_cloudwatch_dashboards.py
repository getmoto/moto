import boto3
from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import

from moto import mock_cloudwatch


@mock_cloudwatch
def test_put_list_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    resp = client.list_dashboards()

    len(resp["DashboardEntries"]).should.equal(1)


@mock_cloudwatch
def test_put_list_prefix_nomatch_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    resp = client.list_dashboards(DashboardNamePrefix="nomatch")

    len(resp["DashboardEntries"]).should.equal(0)


@mock_cloudwatch
def test_delete_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    client.put_dashboard(DashboardName="test2", DashboardBody=widget)
    client.put_dashboard(DashboardName="test3", DashboardBody=widget)
    client.delete_dashboards(DashboardNames=["test2", "test1"])

    resp = client.list_dashboards(DashboardNamePrefix="test3")
    len(resp["DashboardEntries"]).should.equal(1)


@mock_cloudwatch
def test_delete_dashboard_fail():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'

    client.put_dashboard(DashboardName="test1", DashboardBody=widget)
    client.put_dashboard(DashboardName="test2", DashboardBody=widget)
    client.put_dashboard(DashboardName="test3", DashboardBody=widget)
    # Doesnt delete anything if all dashboards to be deleted do not exist
    try:
        client.delete_dashboards(DashboardNames=["test2", "test1", "test_no_match"])
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceNotFound")
    else:
        raise RuntimeError("Should of raised error")

    resp = client.list_dashboards()
    len(resp["DashboardEntries"]).should.equal(3)


@mock_cloudwatch
def test_get_dashboard():
    client = boto3.client("cloudwatch", region_name="eu-central-1")
    widget = '{"widgets": [{"type": "text", "x": 0, "y": 7, "width": 3, "height": 3, "properties": {"markdown": "Hello world"}}]}'
    client.put_dashboard(DashboardName="test1", DashboardBody=widget)

    resp = client.get_dashboard(DashboardName="test1")
    resp.should.contain("DashboardArn")
    resp.should.contain("DashboardBody")
    resp["DashboardName"].should.equal("test1")


@mock_cloudwatch
def test_get_dashboard_fail():
    client = boto3.client("cloudwatch", region_name="eu-central-1")

    try:
        client.get_dashboard(DashboardName="test1")
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceNotFound")
    else:
        raise RuntimeError("Should have raised error")
