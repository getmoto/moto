import boto3

from moto import mock_aws


@mock_aws
def test_get_resources_kms():
    rgta_client = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")

    kms_client = boto3.client("kms", region_name="us-east-1")
    key = kms_client.create_key(
        KeyUsage="ENCRYPT_DECRYPT", Tags=[{"TagKey": "tag", "TagValue": "two"}]
    )
    key_arn = key["KeyMetadata"]["Arn"]
    expected_resource = {
        "ResourceARN": key_arn,
        "Tags": [{"Key": "tag", "Value": "two"}],
    }

    # Filter by tag (unknown)
    resp = rgta_client.get_resources(TagFilters=[{"Key": "tag", "Values": ["one"]}])
    assert resp["ResourceTagMappingList"] == []

    # Filter by tag
    resources = rgta_client.get_resources(
        TagFilters=[{"Key": "tag", "Values": ["two"]}]
    )
    assert resources["ResourceTagMappingList"] == [expected_resource]

    # Filter by type
    resources = rgta_client.get_resources(ResourceTypeFilters=["kms"])
    assert resources["ResourceTagMappingList"] == [expected_resource]

    resources = rgta_client.get_resources(ResourceTypeFilters=["kms:key"])
    assert resources["ResourceTagMappingList"] == [expected_resource]

    resources = rgta_client.get_resources(ResourceTypeFilters=["kms:alias"])
    assert resources["ResourceTagMappingList"] == []
