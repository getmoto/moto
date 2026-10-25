from uuid import uuid4

import boto3

from moto import mock_aws


@mock_aws
def test_connect_instance():
    client = boto3.client("connect", region_name="us-east-1")
    tag_key = str(uuid4())[0:6]
    tag_val = str(uuid4())[0:6]

    create_response = client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
        InstanceAlias="rtapi-test",
        Tags={tag_key: tag_val},
    )
    instance_arn = create_response["Arn"]

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resources = rtapi.get_resources(ResourceTypeFilters=["connect"])[
        "ResourceTagMappingList"
    ]
    assert resources == [
        {"ResourceARN": instance_arn, "Tags": [{"Key": tag_key, "Value": tag_val}]}
    ]

    resources = rtapi.get_resources(ResourceTypeFilters=["connect:instance"])[
        "ResourceTagMappingList"
    ]
    assert resources == [
        {"ResourceARN": instance_arn, "Tags": [{"Key": tag_key, "Value": tag_val}]}
    ]

    resources = rtapi.get_resources(TagFilters=[{"Key": tag_key, "Values": [tag_val]}])[
        "ResourceTagMappingList"
    ]
    assert resources == [
        {"ResourceARN": instance_arn, "Tags": [{"Key": tag_key, "Value": tag_val}]}
    ]

    assert rtapi.get_tag_keys()["TagKeys"] == [tag_key]
    assert rtapi.get_tag_values(Key=tag_key)["TagValues"] == [tag_val]


@mock_aws
def test_connect_instance_without_tags():
    client = boto3.client("connect", region_name="us-east-1")

    client.create_instance(
        IdentityManagementType="CONNECT_MANAGED",
        InboundCallsEnabled=True,
        OutboundCallsEnabled=True,
        InstanceAlias="rtapi-no-tags-test",
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resources = rtapi.get_resources(ResourceTypeFilters=["connect"])[
        "ResourceTagMappingList"
    ]
    # GetResources only returns resources that are (or were previously) tagged.
    assert resources == []
