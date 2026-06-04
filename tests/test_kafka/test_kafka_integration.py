import boto3

from moto import mock_aws


@mock_aws
def test_get_resources_kafka():
    client = boto3.client("kafka", region_name="ap-southeast-1")

    # Create a tagged cluster
    cluster_arn = client.create_cluster_v2(
        ClusterName="TestCluster",
        Serverless={
            "VpcConfigs": [
                {
                    "SubnetIds": ["subnet-0123456789abcdef0"],
                    "SecurityGroupIds": ["sg-0123456789abcdef0"],
                }
            ]
        },
        Tags={"Test": "1"},
    )["ClusterArn"]

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="ap-southeast-1")

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["kafka"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == cluster_arn
    assert {"Key": "Test", "Value": "1"} in resp["ResourceTagMappingList"][0]["Tags"]

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["kafka"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == cluster_arn

    # Non-matching tag filter returns nothing
    resp = rtapi.get_resources(
        ResourceTypeFilters=["kafka"],
        TagFilters=[{"Key": "Test", "Values": ["2"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 0
