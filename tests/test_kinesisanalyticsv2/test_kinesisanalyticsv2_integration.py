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


@mock_aws
def test_tag_and_untag_resources():
    region = "us-east-2"
    client = boto3.client("kinesisanalyticsv2", region_name=region)
    rtapi_client = boto3.client("resourcegroupstaggingapi", region_name=region)

    app_arn = client.create_application(
        ApplicationName="test_application",
        RuntimeEnvironment="FLINK-1_20",
        ServiceExecutionRole=f"arn:aws:iam::{ACCOUNT_ID}:role/application_role",
        Tags=[{"Key": "Test", "Value": "1"}],
    )["ApplicationDetail"]["ApplicationARN"]

    # Basic test
    resp = rtapi_client.get_resources(ResourceTypeFilters=["kinesisanalyticsv2"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == app_arn
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test", "Value": "1"}]

    # Add a tag through the Resource Groups Tagging API
    failed = rtapi_client.tag_resources(
        ResourceARNList=[app_arn],
        Tags={"Test2": "2"},
    )
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi_client.get_resources(ResourceTypeFilters=["kinesisanalyticsv2"])
    tags = resp["ResourceTagMappingList"][0]["Tags"]
    assert {"Key": "Test", "Value": "1"} in tags
    assert {"Key": "Test2", "Value": "2"} in tags

    # Filtering on the newly-added tag returns the application
    resp = rtapi_client.get_resources(
        ResourceTypeFilters=["kinesisanalyticsv2"],
        TagFilters=[{"Key": "Test2", "Values": ["2"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == app_arn

    # Remove the original tag through the Resource Groups Tagging API
    failed = rtapi_client.untag_resources(
        ResourceARNList=[app_arn],
        TagKeys=["Test"],
    )
    assert failed["FailedResourcesMap"] == {}

    resp = rtapi_client.get_resources(ResourceTypeFilters=["kinesisanalyticsv2"])
    tags = resp["ResourceTagMappingList"][0]["Tags"]
    assert tags == [{"Key": "Test2", "Value": "2"}]

    # The removed tag no longer matches
    resp = rtapi_client.get_resources(
        ResourceTypeFilters=["kinesisanalyticsv2"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 0
