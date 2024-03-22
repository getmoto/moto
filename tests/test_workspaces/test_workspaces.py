"""Unit tests for workspaces-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests.test_ds.test_ds_simple_ad_directory import create_test_directory


def create_directory():
    """Create a Directory"""
    ec2_client = boto3.client("ec2", region_name="eu-west-1")
    ds_client = boto3.client("ds", region_name="eu-west-1")
    directory_id = create_test_directory(ds_client, ec2_client)
    return directory_id


def create_security_group(client):
    """Return the ID for a valid Security group."""
    return client.create_security_group(
        GroupName="custom-sg", Description="Custom SG for workspaces"
    )


@mock_aws
def test_create_workspaces():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    resp = client.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
                "VolumeEncryptionKey": f"arn:aws:kms:eu-west-1:{ACCOUNT_ID}:key/51d81fab-b138-4bd2-8a09-07fd6d37224d",
                "UserVolumeEncryptionEnabled": True,
                "RootVolumeEncryptionEnabled": True,
                "WorkspaceProperties": {
                    "RunningMode": "ALWAYS_ON",
                    "RootVolumeSizeGib": 10,
                    "UserVolumeSizeGib": 10,
                    "ComputeTypeName": "VALUE",
                    "Protocols": [
                        "PCOIP",
                    ],
                },
                "Tags": [
                    {"Key": "foo", "Value": "bar"},
                ],
            },
        ]
    )
    pending_requests = resp["PendingRequests"]
    assert len(pending_requests) > 0
    assert "WorkspaceId" in pending_requests[0]
    assert "DirectoryId" in pending_requests[0]
    assert "UserName" in pending_requests[0]
    assert "State" in pending_requests[0]
    assert "BundleId" in pending_requests[0]
    assert "VolumeEncryptionKey" in pending_requests[0]
    assert "UserVolumeEncryptionEnabled" in pending_requests[0]
    assert "RootVolumeEncryptionEnabled" in pending_requests[0]
    assert "WorkspaceProperties" in pending_requests[0]


@mock_aws
def test_create_workspaces_with_invalid_directory_id():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = "d-906787e2cx"
    with pytest.raises(ClientError) as exc:
        client.create_workspaces(
            Workspaces=[
                {
                    "DirectoryId": directory_id,
                    "UserName": "Administrator",
                    "BundleId": "wsb-bh8rsxt14",
                },
            ]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"


@mock_aws
def test_create_workspaces_with_unknown_directory_id():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = "d-906787e2ce"
    resp = client.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
            },
        ]
    )
    failed_requests = resp["FailedRequests"]
    assert len(failed_requests) > 0
    assert "WorkspaceRequest" in failed_requests[0]
    assert "ErrorCode" in failed_requests[0]
    assert "ErrorMessage" in failed_requests[0]


@mock_aws
def test_create_workspaces_with_auto_stop_timeout_and_alwayson():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    resp = client.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
                "WorkspaceProperties": {
                    "RunningMode": "ALWAYS_ON",
                    "RunningModeAutoStopTimeoutInMinutes": 123,
                },
            },
        ]
    )
    failed_requests = resp["FailedRequests"]
    assert len(failed_requests) > 0
    assert (
        failed_requests[0]["ErrorCode"]
        == "AutoStopTimeoutIsNotApplicableForAnAlwaysOnWorkspace"
    )


@mock_aws
def test_create_workspaces_with_auto_stop_timeout_and_manual():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    resp = client.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
                "WorkspaceProperties": {
                    "RunningMode": "MANUAL",
                    "RunningModeAutoStopTimeoutInMinutes": 123,
                },
            },
        ]
    )
    failed_requests = resp["FailedRequests"]
    assert len(failed_requests) > 0
    assert (
        failed_requests[0]["ErrorCode"]
        == "AutoStopTimeoutIsNotDefaultForManualWorkspace"
    )


@mock_aws
def test_describe_workspaces():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    for _ in range(2):
        client.create_workspaces(
            Workspaces=[
                {
                    "DirectoryId": directory_id,
                    "UserName": "Administrator",
                    "BundleId": "wsb-bh8rsxt14",
                }
            ]
        )
    resp = client.describe_workspaces()
    assert len(resp["Workspaces"]) == 2
    workspace = resp["Workspaces"][0]
    assert "WorkspaceId" in workspace
    assert "DirectoryId" in workspace
    assert "UserName" in workspace
    assert "State" in workspace
    assert "BundleId" in workspace


@mock_aws
def test_describe_workspaces_with_directory_and_username():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    client.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
            }
        ]
    )
    resp = client.describe_workspaces(
        DirectoryId=directory_id, UserName="Administrator"
    )

    workspace = resp["Workspaces"][0]
    assert workspace["DirectoryId"] == directory_id
    assert workspace["UserName"] == "Administrator"


@mock_aws
def test_describe_workspaces_invalid_parameters():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    response = client.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
            }
        ]
    )
    workspace_id = response["PendingRequests"][0]["WorkspaceId"]
    with pytest.raises(ClientError) as exc:
        client.describe_workspaces(
            WorkspaceIds=[workspace_id], DirectoryId=directory_id
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValuesException"

    with pytest.raises(ClientError) as exc:
        client.describe_workspaces(
            WorkspaceIds=[workspace_id], BundleId="wsb-bh8rsxt14"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValuesException"

    with pytest.raises(ClientError) as exc:
        client.describe_workspaces(DirectoryId=directory_id, BundleId="wsb-bh8rsxt14")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValuesException"


@mock_aws
def test_describe_workspaces_only_user_name_used():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    client.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
            }
        ]
    )
    with pytest.raises(ClientError) as exc:
        client.describe_workspaces(
            UserName="user1",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValuesException"


@mock_aws
def test_register_workspace_directory():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    resp = client.describe_workspace_directories(DirectoryIds=[directory_id])
    assert "RegistrationCode" in resp["Directories"][0]
    assert (
        resp["Directories"][0]["WorkspaceCreationProperties"]["EnableWorkDocs"] is False
    )
    assert resp["Directories"][0]["Tenancy"] == "SHARED"


@mock_aws
def test_register_workspace_directory_enable_self_service():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(
        DirectoryId=directory_id,
        EnableWorkDocs=True,
        EnableSelfService=True,
        Tenancy="DEDICATED",
    )
    resp = client.describe_workspace_directories(DirectoryIds=[directory_id])
    self_service_permissions = resp["Directories"][0]["SelfservicePermissions"]
    assert "RegistrationCode" in resp["Directories"][0]
    assert (
        resp["Directories"][0]["WorkspaceCreationProperties"]["EnableWorkDocs"] is True
    )
    assert self_service_permissions["IncreaseVolumeSize"] == "ENABLED"
    assert self_service_permissions["ChangeComputeType"] == "ENABLED"
    assert self_service_permissions["SwitchRunningMode"] == "ENABLED"
    assert self_service_permissions["RebuildWorkspace"] == "ENABLED"
    assert resp["Directories"][0]["Tenancy"] == "DEDICATED"


@mock_aws
def test_register_workspace_directory_with_subnets():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    resp = client.describe_workspace_directories(DirectoryIds=[directory_id])
    assert "RegistrationCode" in resp["Directories"][0]
    assert (
        resp["Directories"][0]["WorkspaceCreationProperties"]["EnableWorkDocs"] is False
    )
    assert resp["Directories"][0]["Tenancy"] == "SHARED"


@mock_aws
def test_describe_workspace_directories():
    client = boto3.client("workspaces", region_name="eu-west-1")
    for _ in range(2):
        directory_id = create_directory()
        client.register_workspace_directory(
            DirectoryId=directory_id,
            EnableWorkDocs=True,
        )
    resp = client.describe_workspace_directories()
    assert len(resp["Directories"]) == 2
    directory = resp["Directories"][0]
    assert "DirectoryId" in directory
    assert "DirectoryName" in directory
    assert "RegistrationCode" in directory
    assert "SubnetIds" in directory
    assert "DnsIpAddresses" in directory
    assert "CustomerUserName" in directory
    assert "IamRoleId" in directory
    assert "DirectoryType" in directory
    assert "WorkspaceSecurityGroupId" in directory
    assert "State" in directory
    assert "WorkspaceCreationProperties" in directory
    assert "WorkspaceAccessProperties" in directory
    assert "Tenancy" in directory
    assert "SelfservicePermissions" in directory
    assert "SamlProperties" in directory
    assert "CertificateBasedAuthProperties" in directory


@mock_aws
def test_describe_workspace_directories_with_directory_id():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(
        DirectoryId=directory_id,
        EnableWorkDocs=True,
    )
    resp = client.describe_workspace_directories(DirectoryIds=[directory_id])
    assert len(resp["Directories"]) == 1
    directory = resp["Directories"][0]
    assert directory["DirectoryId"] == directory_id


@mock_aws
def test_describe_workspace_directories_with_invalid_directory_id():
    client = boto3.client("workspaces", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.describe_workspace_directories(DirectoryIds=["d-9067f997cx"])
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"


@mock_aws
def test_modify_workspace_creation_properties():
    client = boto3.client("workspaces", region_name="eu-west-1")
    ec2_client = boto3.client("ec2", region_name="eu-west-1")
    directory_id = create_directory()
    sg = create_security_group(client=ec2_client)
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    client.modify_workspace_creation_properties(
        ResourceId=directory_id,
        WorkspaceCreationProperties={
            "EnableWorkDocs": False,
            "CustomSecurityGroupId": sg["GroupId"],
        },
    )
    resp = client.describe_workspace_directories(DirectoryIds=[directory_id])
    directory = resp["Directories"][0]
    assert (
        directory["WorkspaceCreationProperties"]["CustomSecurityGroupId"]
        == sg["GroupId"]
    )


@mock_aws
def test_modify_workspace_creation_properties_invalid_request():
    client = boto3.client("workspaces", region_name="eu-west-1")
    ec2_client = boto3.client("ec2", region_name="eu-west-1")
    sg = create_security_group(client=ec2_client)
    with pytest.raises(ClientError) as exc:
        client.modify_workspace_creation_properties(
            ResourceId="d-9067f6c44b",  # Invalid DirectoryID
            WorkspaceCreationProperties={
                "EnableWorkDocs": False,
                "CustomSecurityGroupId": sg["GroupId"],
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"


@mock_aws
def test_create_tags():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(
        DirectoryId=directory_id,
        EnableWorkDocs=True,
        Tags=[
            {"Key": "foo1", "Value": "bar1"},
        ],
    )
    client.create_tags(
        ResourceId=directory_id,
        Tags=[
            {"Key": "foo2", "Value": "bar2"},
        ],
    )
    resp = client.describe_tags(ResourceId=directory_id)
    assert resp["TagList"][1]["Key"] == "foo2"


@mock_aws
def test_describe_tags():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(
        DirectoryId=directory_id,
        EnableWorkDocs=True,
        Tags=[
            {"Key": "foo", "Value": "bar"},
        ],
    )
    resp = client.describe_tags(ResourceId=directory_id)
    assert resp["TagList"][0]["Key"] == "foo"


@mock_aws
def test_describe_client_properties():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(
        DirectoryId=directory_id,
        EnableWorkDocs=True,
    )
    resp = client.describe_client_properties(ResourceIds=[directory_id])
    assert "ClientProperties" in resp["ClientPropertiesList"][0]


@mock_aws
def test_modify_client_properties():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(
        DirectoryId=directory_id,
        EnableWorkDocs=True,
    )
    client.modify_client_properties(
        ResourceId=directory_id,
        ClientProperties={
            "ReconnectEnabled": "DISABLED",
            "LogUploadEnabled": "DISABLED",
        },
    )
    resp = client.describe_client_properties(ResourceIds=[directory_id])
    client_properties_list = resp["ClientPropertiesList"][0]["ClientProperties"]
    assert client_properties_list["ReconnectEnabled"] == "DISABLED"
    assert client_properties_list["LogUploadEnabled"] == "DISABLED"


@mock_aws
def test_create_workspace_image():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    workspace = client.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
            },
        ]
    )
    workspace_id = workspace["PendingRequests"][0]["WorkspaceId"]
    resp = client.create_workspace_image(
        Name="test-image",
        Description="Test Description for workspace images",
        WorkspaceId=workspace_id,
    )
    assert "ImageId" in resp
    assert "Name" in resp
    assert "Description" in resp
    assert "State" in resp
    assert "RequiredTenancy" in resp
    assert "Created" in resp
    assert "OwnerAccountId" in resp


@mock_aws
def test_create_workspace_image_invalid_workspace():
    client = boto3.client("workspaces", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.create_workspace_image(
            Name="test-image",
            Description="Invalid workspace id",
            WorkspaceId="ws-hbfljyz9x",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_create_workspace_image_already_exists():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    workspace = client.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
            },
        ]
    )
    workspace_id = workspace["PendingRequests"][0]["WorkspaceId"]
    client.create_workspace_image(
        Name="test-image",
        Description="Test Description for workspace images",
        WorkspaceId=workspace_id,
    )
    with pytest.raises(ClientError) as exc:
        client.create_workspace_image(
            Name="test-image",
            Description="Image with same name",
            WorkspaceId=workspace_id,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceAlreadyExistsException"


@mock_aws
def test_describe_workspace_images():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    workspace = client.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
            },
        ]
    )
    workspace_id = workspace["PendingRequests"][0]["WorkspaceId"]
    image = client.create_workspace_image(
        Name="test-image",
        Description="Test Description for workspace images",
        WorkspaceId=workspace_id,
    )
    resp = client.describe_workspace_images(ImageIds=[image["ImageId"]])
    assert "ImageId" in resp["Images"][0]
    assert "Name" in resp["Images"][0]
    assert "Description" in resp["Images"][0]
    assert "State" in resp["Images"][0]
    assert "RequiredTenancy" in resp["Images"][0]
    assert "Created" in resp["Images"][0]
    assert "OwnerAccountId" in resp["Images"][0]
    assert "Updates" in resp["Images"][0]


@mock_aws
def test_update_workspace_image_permission():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    workspace = client.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
            },
        ]
    )
    workspace_id = workspace["PendingRequests"][0]["WorkspaceId"]
    image = client.create_workspace_image(
        Name="test-image",
        Description="Test Description for workspace images",
        WorkspaceId=workspace_id,
    )
    client.update_workspace_image_permission(
        ImageId=image["ImageId"], AllowCopyImage=True, SharedAccountId="111111111111"
    )
    resp = client.describe_workspace_image_permissions(ImageId=image["ImageId"])
    assert resp["ImagePermissions"][0]["SharedAccountId"] == "111111111111"

    client.update_workspace_image_permission(
        ImageId=image["ImageId"], AllowCopyImage=False, SharedAccountId="111111111111"
    )
    resp = client.describe_workspace_image_permissions(ImageId=image["ImageId"])
    assert len(resp["ImagePermissions"]) == 0


@mock_aws
def test_describe_workspace_image_permissions():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    workspace = client.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
            },
        ]
    )
    workspace_id = workspace["PendingRequests"][0]["WorkspaceId"]
    image = client.create_workspace_image(
        Name="test-image",
        Description="Test Description for workspace images",
        WorkspaceId=workspace_id,
    )
    client.update_workspace_image_permission(
        ImageId=image["ImageId"], AllowCopyImage=True, SharedAccountId="111111111111"
    )
    resp = client.describe_workspace_image_permissions(ImageId=image["ImageId"])
    assert resp["ImageId"] == image["ImageId"]
    assert resp["ImagePermissions"][0]["SharedAccountId"] == "111111111111"


@mock_aws
def test_describe_workspace_image_permissions_with_invalid_image_id():
    client = boto3.client("workspaces", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.describe_workspace_image_permissions(ImageId="foo")
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"


@mock_aws
def test_deregister_workspace_directory():
    client = boto3.client("workspaces", region_name="eu-west-1")
    directory_id = create_directory()
    client.register_workspace_directory(DirectoryId=directory_id, EnableWorkDocs=False)
    resp = client.describe_workspace_directories(DirectoryIds=[directory_id])
    assert len(resp["Directories"]) > 0
    client.deregister_workspace_directory(DirectoryId=directory_id)
    resp = client.describe_workspace_directories(DirectoryIds=[directory_id])
    assert len(resp["Directories"]) == 0


@mock_aws
def test_modify_selfservice_permissions():
    client = boto3.client("workspaces", region_name="eu-west-1")

    directory_id = create_directory()
    client.register_workspace_directory(
        DirectoryId=directory_id,
        EnableWorkDocs=True,
    )
    resp = client.describe_workspace_directories(DirectoryIds=[directory_id])
    assert (
        resp["Directories"][0]["SelfservicePermissions"]["IncreaseVolumeSize"]
        == "DISABLED"
    )
    client.modify_selfservice_permissions(
        ResourceId=directory_id,
        SelfservicePermissions={
            "RestartWorkspace": "ENABLED",
            "IncreaseVolumeSize": "ENABLED",
            "ChangeComputeType": "ENABLED",
            "SwitchRunningMode": "ENABLED",
            "RebuildWorkspace": "ENABLED",
        },
    )
    resp = client.describe_workspace_directories(DirectoryIds=[directory_id])
    assert (
        resp["Directories"][0]["SelfservicePermissions"]["IncreaseVolumeSize"]
        == "ENABLED"
    )
