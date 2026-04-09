import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from .test_kinesisanalyticsv2 import FAKE_TAGS


@mock_aws
def test_resource_groups_tagging_api():
    region = "us-east-2"
    client = boto3.client("kinesisanalyticsv2", region_name=region)
    rtapi_client = boto3.client("resourcegroupstaggingapi", region_name=region)

    app_resp = client.create_application(
        ApplicationName="test_application",
        RuntimeEnvironment="FLINK-1_20",
        ServiceExecutionRole=f"arn:aws:iam::{ACCOUNT_ID}:role/application_role",
        Tags=FAKE_TAGS,
    )
    app = app_resp.get("ApplicationDetail")
    app_arn = app.get("ApplicationARN")

    resp = rtapi_client.get_resources(ResourceTypeFilters=["kinesisanalyticsv2"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == app_arn
    assert resp["ResourceTagMappingList"][0]["Tags"] == FAKE_TAGS
