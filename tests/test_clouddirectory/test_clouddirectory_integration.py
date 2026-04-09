import boto3

from moto import mock_aws
from tests import DEFAULT_ACCOUNT_ID


@mock_aws
def test_get_directory_tags_using_resourcegroupstaggingapi():
    region = "us-west-2"
    client = boto3.client("clouddirectory", region_name=region)
    directory_arn = client.create_directory(
        SchemaArn=f"arn:aws:clouddirectory:{region}:{DEFAULT_ACCOUNT_ID}:directory/test-schema/1",
        Name="test-directory",
    )["DirectoryArn"]
    client.tag_resource(
        ResourceArn=directory_arn, Tags=[{"Key": "key1", "Value": "value1"}]
    )

    # Test resourcetaggingapi
    rtapi = boto3.client("resourcegroupstaggingapi", region_name=region)
    resp = rtapi.get_resources(ResourceTypeFilters=["clouddirectory"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == directory_arn
    assert resp["ResourceTagMappingList"][0]["Tags"][0]["Key"] == "key1"
    assert resp["ResourceTagMappingList"][0]["Tags"][0]["Value"] == "value1"
