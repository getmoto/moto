import warnings

import boto3

from moto import mock_aws


@mock_aws
def test_get_resources_workspacesweb():
    ww_client = boto3.client("workspaces-web", region_name="ap-southeast-1")
    arn = ww_client.create_portal(
        additionalEncryptionContext={"Key1": "Encryption", "Key2": "Context"},
        authenticationType="Standard",
        clientToken="TestClient",
        customerManagedKey="abcd1234-5678-90ab-cdef-FAKEKEY",
        displayName="TestDisplayName",
        instanceType="TestInstanceType",
        maxConcurrentSessions=5,
        tags=[
            {"Key": "TestKey", "Value": "TestValue"},
            {"Key": "TestKey2", "Value": "TestValue2"},
        ],
    )["portalArn"]
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="ap-southeast-1")
    resp = rtapi.get_resources(ResourceTypeFilters=["workspaces-web"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "TestKey", "Value": "TestValue"} in resp["ResourceTagMappingList"][
        0
    ]["Tags"]
    resp = rtapi.get_resources(
        ResourceTypeFilters=["workspaces-web"],
        TagFilters=[{"Key": "TestKey3", "Values": ["TestValue3"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 0
    ww_client.tag_resource(
        resourceArn=arn, tags=[{"Key": "TestKey3", "Value": "TestValue3"}]
    )
    resp = rtapi.get_resources(
        ResourceTypeFilters=["workspaces-web"],
        TagFilters=[{"Key": "TestKey3", "Values": ["TestValue3"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1


@mock_aws
def test_get_resources_workspacesweb_in_unknown_region():
    session = boto3.Session()
    all_regions = session.get_available_regions("ec2")
    supported_regions = session.get_available_regions("workspaces-web")
    unsupported_regions = [reg for reg in all_regions if reg not in supported_regions]
    if not unsupported_regions:
        warnings.warn(
            "All regions supported - unable to test unsupported region", stacklevel=2
        )
        return

    region = unsupported_regions[0]
    rtapi = boto3.client("resourcegroupstaggingapi", region_name=region)
    resp = rtapi.get_resources(ResourceTypeFilters=["workspaces-web"])
    assert len(resp["ResourceTagMappingList"]) == 0
