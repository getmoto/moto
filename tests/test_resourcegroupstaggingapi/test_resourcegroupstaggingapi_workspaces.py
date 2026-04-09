import boto3

from moto import mock_aws
from tests.test_ds.test_ds_simple_ad_directory import create_test_directory


def create_directory():
    ec2_client = boto3.client("ec2", region_name="eu-central-1")
    ds_client = boto3.client("ds", region_name="eu-central-1")
    directory_id = create_test_directory(ds_client, ec2_client)
    return directory_id


@mock_aws
def test_get_resources_workspaces():
    workspaces = boto3.client("workspaces", region_name="eu-central-1")

    # Create two tagged Workspaces
    directory_id = create_directory()
    workspaces.register_workspace_directory(DirectoryId=directory_id)
    workspaces.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
                "Tags": [
                    {"Key": "Test", "Value": "1"},
                ],
            },
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
                "Tags": [
                    {"Key": "Test", "Value": "2"},
                ],
            },
        ]
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["workspaces"])
    assert len(resp["ResourceTagMappingList"]) == 2

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["workspaces"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "1"} in resp["ResourceTagMappingList"][0]["Tags"]


@mock_aws
def test_get_resources_workspace_directories():
    workspaces = boto3.client("workspaces", region_name="eu-central-1")

    # Create two tagged Workspaces Directories
    for i in range(1, 3):
        i_str = str(i)
        directory_id = create_directory()
        workspaces.register_workspace_directory(
            DirectoryId=directory_id,
            Tags=[{"Key": "Test", "Value": i_str}],
        )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["workspaces-directory"])
    assert len(resp["ResourceTagMappingList"]) == 2

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["workspaces-directory"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "1"} in resp["ResourceTagMappingList"][0]["Tags"]


@mock_aws
def test_get_resources_workspace_images():
    workspaces = boto3.client("workspaces", region_name="eu-central-1")

    # Create two tagged Workspace Images
    directory_id = create_directory()
    workspaces.register_workspace_directory(DirectoryId=directory_id)
    resp = workspaces.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
            },
        ]
    )
    workspace_id = resp["PendingRequests"][0]["WorkspaceId"]
    for i in range(1, 3):
        i_str = str(i)
        _ = workspaces.create_workspace_image(
            Name=f"test-image-{i_str}",
            Description="Test workspace image",
            WorkspaceId=workspace_id,
            Tags=[{"Key": "Test", "Value": i_str}],
        )
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["workspaces-image"])
    assert len(resp["ResourceTagMappingList"]) == 2

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["workspaces-image"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "1"} in resp["ResourceTagMappingList"][0]["Tags"]
