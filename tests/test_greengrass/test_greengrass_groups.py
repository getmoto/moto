import boto3
from botocore.exceptions import ClientError
import freezegun
import pytest

from moto import mock_greengrass
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.settings import TEST_SERVER_MODE


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_group():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_core_ver = {
        "Cores": [
            {
                "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
                "Id": "123456789",
                "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
            }
        ]
    }

    create_core_def_res = client.create_core_definition(
        InitialVersion=init_core_ver, Name="TestCore"
    )
    core_def_ver_arn = create_core_def_res["LatestVersionArn"]

    init_grp = {"CoreDefinitionVersionArn": core_def_ver_arn}

    grp_name = "TestGroup"
    create_grp_res = client.create_group(Name=grp_name, InitialVersion=init_grp)
    create_grp_res.should.have.key("Arn")
    create_grp_res.should.have.key("Id")
    create_grp_res.should.have.key("LastUpdatedTimestamp")
    create_grp_res.should.have.key("LatestVersion")
    create_grp_res.should.have.key("LatestVersionArn")
    create_grp_res.should.have.key("Name").equals(grp_name)
    create_grp_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)

    if not TEST_SERVER_MODE:
        create_grp_res.should.have.key("CreationTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )
        create_grp_res.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_list_groups():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    grp_name = "TestGroup"
    create_grp_res = client.create_group(Name=grp_name)
    group_id = create_grp_res["Id"]

    list_res = client.list_groups()

    group = list_res["Groups"][0]
    group.should.have.key("Name").equals(grp_name)
    group.should.have.key("Arn")
    group.should.have.key("Id").equals(group_id)
    group.should.have.key("LatestVersion")
    group.should.have.key("LatestVersionArn")
    if not TEST_SERVER_MODE:
        group.should.have.key("CreationTimestamp").equal("2022-06-01T12:00:00.000Z")
        group.should.have.key("LastUpdatedTimestamp").equals("2022-06-01T12:00:00.000Z")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_get_group():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    grp_name = "TestGroup"
    create_res = client.create_group(Name=grp_name)
    group_id = create_res["Id"]
    group_arn = create_res["Arn"]
    latest_version = create_res["LatestVersion"]
    latest_version_arn = create_res["LatestVersionArn"]

    get_res = client.get_group(GroupId=group_id)

    get_res.should.have.key("Name").equals(grp_name)
    get_res.should.have.key("Arn").equals(group_arn)
    get_res.should.have.key("Id").equals(group_id)
    get_res.should.have.key("LatestVersion").equals(latest_version)
    get_res.should.have.key("LatestVersionArn").equals(latest_version_arn)
    get_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    if not TEST_SERVER_MODE:
        get_res.should.have.key("CreationTimestamp").equal("2022-06-01T12:00:00.000Z")
        get_res.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )


@mock_greengrass
def test_get_group_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.get_group(GroupId="b552443b-1888-469b-81f8-0ebc5ca92949")
    ex.value.response["Error"]["Message"].should.equal(
        "That Group Definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_delete_group():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    create_res = client.create_group(Name="TestGroup")

    group_id = create_res["Id"]
    del_res = client.delete_group(GroupId=group_id)
    del_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_greengrass
def test_delete_group_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.delete_group(GroupId="6fbffc21-989e-4d29-a793-a42f450a78c6")
    ex.value.response["Error"]["Message"].should.equal(
        "That group definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_update_group():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    create_res = client.create_group(Name="TestGroup")

    group_id = create_res["Id"]
    updated_group_name = "UpdatedGroup"
    update_res = client.update_group(GroupId=group_id, Name=updated_group_name)
    update_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    get_res = client.get_group(GroupId=group_id)
    get_res.should.have.key("Name").equals(updated_group_name)


@mock_greengrass
def test_update_group_with_empty_name():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    create_res = client.create_group(Name="TestGroup")

    group_id = create_res["Id"]

    with pytest.raises(ClientError) as ex:
        client.update_group(GroupId=group_id, Name="")
    ex.value.response["Error"]["Message"].should.equal(
        "Input does not contain any attributes to be updated"
    )
    ex.value.response["Error"]["Code"].should.equal(
        "InvalidContainerDefinitionException"
    )


@mock_greengrass
def test_update_group_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.update_group(GroupId="6fbffc21-989e-4d29-a793-a42f450a78c6", Name="123")
    ex.value.response["Error"]["Message"].should.equal(
        "That group definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_group_version():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    create_grp_res = client.create_group(Name="TestGroup")
    group_id = create_grp_res["Id"]

    group_ver_res = client.create_group_version(GroupId=group_id)
    group_ver_res.should.have.key("Arn")
    group_ver_res.should.have.key("CreationTimestamp")
    group_ver_res.should.have.key("Id").equals(group_id)
    group_ver_res.should.have.key("Version")

    if not TEST_SERVER_MODE:
        group_ver_res["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")


@mock_greengrass
def test_create_group_version_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.create_group_version(GroupId="cd2ea6dc-6634-4e89-8441-8003500435f9")

    ex.value.response["Error"]["Message"].should.equal("That group does not exist.")
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@pytest.mark.parametrize(
    "def_ver_key_name,arn,error_message",
    [
        (
            "CoreDefinitionVersionArn",
            "123",
            "Cores definition reference does not exist",
        ),
        (
            "CoreDefinitionVersionArn",
            "arn:aws:greengrass:ap-northeast-1:944137583148:/greengrass/definition/cores/fc3b3e5b-f1ce-4639-88d3-3ad897d95b2a/versions/dd0f800c-246c-4973-82cf-45b109cbd99b",
            "Cores definition reference does not exist",
        ),
        (
            "DeviceDefinitionVersionArn",
            "123",
            "Devices definition reference does not exist",
        ),
        (
            "DeviceDefinitionVersionArn",
            "arn:aws:greengrass:ap-northeast-1:944137583148:/greengrass/definition/devices/fc3b3e5b-f1ce-4639-88d3-3ad897d95b2a/versions/dd0f800c-246c-4973-82cf-45b109cbd99b",
            "Devices definition reference does not exist",
        ),
        (
            "FunctionDefinitionVersionArn",
            "123",
            "Lambda definition reference does not exist",
        ),
        (
            "FunctionDefinitionVersionArn",
            "arn:aws:greengrass:ap-northeast-1:944137583148:/greengrass/definition/functions/fc3b3e5b-f1ce-4639-88d3-3ad897d95b2a/versions/dd0f800c-246c-4973-82cf-45b109cbd99b",
            "Lambda definition reference does not exist",
        ),
        (
            "ResourceDefinitionVersionArn",
            "123",
            "Resource definition reference does not exist",
        ),
        (
            "ResourceDefinitionVersionArn",
            "arn:aws:greengrass:ap-northeast-1:944137583148:/greengrass/definition/resources/fc3b3e5b-f1ce-4639-88d3-3ad897d95b2a/versions/dd0f800c-246c-4973-82cf-45b109cbd99b",
            "Resource definition reference does not exist",
        ),
        (
            "SubscriptionDefinitionVersionArn",
            "123",
            "Subscription definition reference does not exist",
        ),
        (
            "SubscriptionDefinitionVersionArn",
            "arn:aws:greengrass:ap-northeast-1:944137583148:/greengrass/definition/subscriptions/fc3b3e5b-f1ce-4639-88d3-3ad897d95b2a/versions/dd0f800c-246c-4973-82cf-45b109cbd99b",
            "Subscription definition reference does not exist",
        ),
    ],
)
@mock_greengrass
def test_create_group_version_with_invalid_version_arn(
    def_ver_key_name, arn, error_message
):

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    create_grp_res = client.create_group(Name="TestGroup")
    group_id = create_grp_res["Id"]

    definition_versions = {def_ver_key_name: arn}

    with pytest.raises(ClientError) as ex:
        client.create_group_version(GroupId=group_id, **definition_versions)

    ex.value.response["Error"]["Message"].should.equal(
        f"The group is invalid or corrupted. (ErrorDetails: [{error_message}])"
    )
    ex.value.response["Error"]["Code"].should.equal("400")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_list_group_versions():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    create_res = client.create_group(Name="TestGroup")
    group_id = create_res["Id"]

    group_vers_res = client.list_group_versions(GroupId=group_id)

    group_vers_res.should.have.key("Versions")
    group_ver = group_vers_res["Versions"][0]
    group_ver.should.have.key("Arn")
    group_ver.should.have.key("CreationTimestamp")
    group_ver.should.have.key("Id").equals(group_id)
    group_ver.should.have.key("Version")

    if not TEST_SERVER_MODE:
        group_ver["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")


@mock_greengrass
def test_list_group_versions_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.list_group_versions(GroupId="7b0bdeae-54c7-47cf-9f93-561e672efd9c")
    ex.value.response["Error"]["Message"].should.equal(
        "That group definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_get_group_version():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_core_ver = {
        "Cores": [
            {
                "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
                "Id": "123456789",
                "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
            }
        ]
    }

    create_core_def_res = client.create_core_definition(
        InitialVersion=init_core_ver, Name="TestCore"
    )
    core_def_ver_arn = create_core_def_res["LatestVersionArn"]

    init_device_ver = {
        "Devices": [
            {
                "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
                "Id": "123",
                "SyncShadow": True,
                "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
            }
        ]
    }

    create_device_res = client.create_device_definition(
        InitialVersion=init_device_ver, Name="TestDevice"
    )
    device_def_ver_arn = create_device_res["LatestVersionArn"]

    init_func_ver = {
        "Functions": [
            {
                "FunctionArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:1",
                "Id": "1234567890",
                "FunctionConfiguration": {
                    "MemorySize": 16384,
                    "EncodingType": "binary",
                    "Pinned": True,
                    "Timeout": 3,
                },
            }
        ]
    }
    create_func_res = client.create_function_definition(
        InitialVersion=init_func_ver, Name="TestFunc"
    )
    func_def_ver_arn = create_func_res["LatestVersionArn"]

    init_resource_ver = {
        "Resources": [
            {
                "Id": "123",
                "Name": "test_directory",
                "ResourceDataContainer": {
                    "LocalVolumeResourceData": {
                        "DestinationPath": "/test_dir",
                        "GroupOwnerSetting": {"AutoAddGroupOwner": True},
                        "SourcePath": "/home/ggc_user/test_dir",
                    }
                },
            }
        ]
    }

    create_resource_res = client.create_resource_definition(
        InitialVersion=init_resource_ver, Name="TestResource"
    )
    resource_def_ver_arn = create_resource_res["LatestVersionArn"]

    init_subscription_ver = {
        "Subscriptions": [
            {
                "Id": "123456",
                "Source": "arn:aws:lambda:ap-northeast-1:123456789012:function:test_func:1",
                "Subject": "foo/bar",
                "Target": "cloud",
            }
        ]
    }
    create_subscription_res = client.create_subscription_definition(
        InitialVersion=init_subscription_ver, Name="TestSubscription"
    )
    subscription_def_ver_arn = create_subscription_res["LatestVersionArn"]

    definition = {
        "CoreDefinitionVersionArn": core_def_ver_arn,
        "DeviceDefinitionVersionArn": device_def_ver_arn,
        "FunctionDefinitionVersionArn": func_def_ver_arn,
        "ResourceDefinitionVersionArn": resource_def_ver_arn,
        "SubscriptionDefinitionVersionArn": subscription_def_ver_arn,
    }

    grp_name = "TestGroup"
    create_res = client.create_group(Name=grp_name, InitialVersion=definition)
    group_id = create_res["Id"]
    group_ver_id = create_res["LatestVersion"]

    group_ver_res = client.get_group_version(
        GroupId=group_id, GroupVersionId=group_ver_id
    )

    group_ver_res.should.have.key("Arn")
    group_ver_res.should.have.key("CreationTimestamp")
    group_ver_res.should.have.key("Definition").should.equal(definition)
    group_ver_res.should.have.key("Id").equals(group_id)
    group_ver_res.should.have.key("Version").should.equal(group_ver_id)

    if not TEST_SERVER_MODE:
        group_ver_res["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")


@mock_greengrass
def test_get_group_version_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.get_group_version(
            GroupId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
            GroupVersionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That group definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_get_group_version_with_invalid_version_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    create_res = client.create_group(Name="TestGroup")

    group_id = create_res["Id"]
    invalid_group_ver_id = "7b0bdeae-54c7-47cf-9f93-561e672efd9c"

    with pytest.raises(ClientError) as ex:
        client.get_group_version(
            GroupId=group_id,
            GroupVersionId=invalid_group_ver_id,
        )
    ex.value.response["Error"]["Message"].should.equal(
        f"Version {invalid_group_ver_id} of Group Definition {group_id} does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("VersionNotFoundException")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_associate_role_to_group():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    res = client.associate_role_to_group(
        GroupId="abc002c8-1093-485e-9324-3baadf38e582",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/greengrass-role",
    )

    res.should.have.key("AssociatedAt")
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_get_associated_role():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    group_id = "abc002c8-1093-485e-9324-3baadf38e582"
    role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/greengrass-role"
    client.associate_role_to_group(GroupId=group_id, RoleArn=role_arn)

    res = client.get_associated_role(GroupId=group_id)
    res.should.have.key("AssociatedAt")
    res.should.have.key("RoleArn").should.equal(role_arn)
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    if not TEST_SERVER_MODE:
        res["AssociatedAt"].should.equal("2022-06-01T12:00:00.000Z")


@mock_greengrass
def test_get_associated_role_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.get_associated_role(GroupId="abc002c8-1093-485e-9324-3baadf38e582")

    ex.value.response["Error"]["Message"].should.equal(
        "You need to attach an IAM role to this deployment group."
    )
    ex.value.response["Error"]["Code"].should.equal("404")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_disassociate_role_from_group():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    group_id = "abc002c8-1093-485e-9324-3baadf38e582"
    role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/greengrass-role"
    client.associate_role_to_group(GroupId=group_id, RoleArn=role_arn)
    client.get_associated_role(GroupId=group_id)

    res = client.disassociate_role_from_group(GroupId=group_id)
    res.should.have.key("DisassociatedAt")
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    if not TEST_SERVER_MODE:
        res["DisassociatedAt"].should.equal("2022-06-01T12:00:00.000Z")

    with pytest.raises(ClientError) as ex:
        client.get_associated_role(GroupId=group_id)

    ex.value.response["Error"]["Message"].should.equal(
        "You need to attach an IAM role to this deployment group."
    )
    ex.value.response["Error"]["Code"].should.equal("404")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_disassociate_role_from_group_with_none_exists_group_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    group_id = "abc002c8-1093-485e-9324-3baadf38e582"
    res = client.disassociate_role_from_group(GroupId=group_id)
    res.should.have.key("DisassociatedAt")
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    if not TEST_SERVER_MODE:
        res["DisassociatedAt"].should.equal("2022-06-01T12:00:00.000Z")
