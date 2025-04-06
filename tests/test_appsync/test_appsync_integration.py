import boto3

from moto import mock_aws


@mock_aws
def test_resource_groups_tagging_api():
    region = "us-west-2"
    client = boto3.client("appsync", region_name=region)
    rtapi_client = boto3.client("resourcegroupstaggingapi", region_name=region)

    api = client.create_graphql_api(
        name="api-with-tags",
        authenticationType="API_KEY",
        tags={"key": "val", "key2": "val2"},
    )["graphqlApi"]
    client.create_graphql_api(name="api-no-tags", authenticationType="API_KEY")[
        "graphqlApi"
    ]

    resp = rtapi_client.get_resources(ResourceTypeFilters=["appsync"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == api["arn"]
    assert resp["ResourceTagMappingList"][0]["Tags"] == [
        {"Key": "key", "Value": "val"},
        {"Key": "key2", "Value": "val2"},
    ]
