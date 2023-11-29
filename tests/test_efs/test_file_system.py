import re

import pytest
from botocore.exceptions import ClientError

from tests.test_efs.junk_drawer import has_status_code

from . import fixture_efs  # noqa # pylint: disable=unused-import

ARN_PATT = r"^arn:(?P<Partition>[^:\n]*):(?P<Service>[^:\n]*):(?P<Region>[^:\n]*):(?P<AccountID>[^:\n]*):(?P<Ignore>(?P<ResourceType>[^:\/\n]*)[:\/])?(?P<Resource>.*)$"
STRICT_ARN_PATT = r"^arn:aws:[a-z]+:[a-z]{2}-[a-z]+-[0-9]:[0-9]+:[a-z-]+\/[a-z0-9-]+$"

SAMPLE_1_PARAMS = {
    "CreationToken": "myFileSystem1",
    "PerformanceMode": "generalPurpose",
    "Backup": True,
    "Encrypted": True,
    "Tags": [{"Key": "Name", "Value": "Test Group1"}],
}

SAMPLE_2_PARAMS = {
    "CreationToken": "myFileSystem2",
    "PerformanceMode": "generalPurpose",
    "Backup": True,
    "AvailabilityZoneName": "us-west-2b",
    "Encrypted": True,
    "ThroughputMode": "provisioned",
    "ProvisionedThroughputInMibps": 60,
    "Tags": [{"Key": "Name", "Value": "Test Group1"}],
}


# Testing Create
# ==============


def test_create_file_system_correct_use(efs):
    from datetime import datetime

    creation_token = "test_efs_create"
    create_fs_resp = efs.create_file_system(
        CreationToken=creation_token,
        Tags=[{"Key": "Name", "Value": "Test EFS Container"}],
    )

    # Check the response.
    assert has_status_code(create_fs_resp, 201)
    assert create_fs_resp["CreationToken"] == creation_token
    assert "fs-" in create_fs_resp["FileSystemId"]
    assert isinstance(create_fs_resp["CreationTime"], datetime)
    assert create_fs_resp["LifeCycleState"] == "available"
    assert create_fs_resp["Tags"][0] == {"Key": "Name", "Value": "Test EFS Container"}
    assert create_fs_resp["ThroughputMode"] == "bursting"
    assert create_fs_resp["PerformanceMode"] == "generalPurpose"
    assert create_fs_resp["Encrypted"] is False
    assert create_fs_resp["NumberOfMountTargets"] == 0
    assert create_fs_resp["Name"] == "Test EFS Container"

    for key_name in ["Value", "ValueInIA", "ValueInStandard"]:
        assert key_name in create_fs_resp["SizeInBytes"]
        assert create_fs_resp["SizeInBytes"][key_name] == 0
    assert re.match(STRICT_ARN_PATT, create_fs_resp["FileSystemArn"])

    # Check the (lack of the) backup policy.
    with pytest.raises(ClientError) as exc_info:
        efs.describe_backup_policy(FileSystemId=create_fs_resp["FileSystemId"])
    resp = exc_info.value.response
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert "PolicyNotFound" == resp["Error"]["Code"]

    # Check the arn in detail
    match_obj = re.match(ARN_PATT, create_fs_resp["FileSystemArn"])
    arn_parts = match_obj.groupdict()
    assert arn_parts["ResourceType"] == "file-system"
    assert arn_parts["Resource"] == create_fs_resp["FileSystemId"]
    assert arn_parts["Service"] == "elasticfilesystem"
    assert arn_parts["AccountID"] == create_fs_resp["OwnerId"]


def test_create_file_system_aws_sample_1(efs):
    resp = efs.create_file_system(**SAMPLE_1_PARAMS)
    resp_metadata = resp.pop("ResponseMetadata")
    assert resp_metadata["HTTPStatusCode"] == 201
    assert set(resp.keys()) == {
        "OwnerId",
        "CreationToken",
        "Encrypted",
        "PerformanceMode",
        "FileSystemId",
        "FileSystemArn",
        "CreationTime",
        "LifeCycleState",
        "NumberOfMountTargets",
        "SizeInBytes",
        "Tags",
        "ThroughputMode",
        "Name",
    }
    assert resp["Tags"] == [{"Key": "Name", "Value": "Test Group1"}]
    assert resp["PerformanceMode"] == "generalPurpose"
    assert resp["Encrypted"]
    assert resp["Name"] == "Test Group1"

    policy_resp = efs.describe_backup_policy(FileSystemId=resp["FileSystemId"])
    assert policy_resp["BackupPolicy"]["Status"] == "ENABLED"


def test_create_file_system_aws_sample_2(efs):
    resp = efs.create_file_system(**SAMPLE_2_PARAMS)
    resp_metadata = resp.pop("ResponseMetadata")
    assert resp_metadata["HTTPStatusCode"] == 201
    assert set(resp.keys()) == {
        "AvailabilityZoneId",
        "AvailabilityZoneName",
        "PerformanceMode",
        "ProvisionedThroughputInMibps",
        "SizeInBytes",
        "Tags",
        "ThroughputMode",
        "CreationTime",
        "CreationToken",
        "Encrypted",
        "LifeCycleState",
        "FileSystemId",
        "FileSystemArn",
        "NumberOfMountTargets",
        "OwnerId",
        "Name",
    }
    assert resp["ProvisionedThroughputInMibps"] == 60
    assert resp["AvailabilityZoneId"] == "usw2-az1"
    assert resp["AvailabilityZoneName"] == "us-west-2b"
    assert resp["ThroughputMode"] == "provisioned"
    assert resp["Name"] == "Test Group1"

    policy_resp = efs.describe_backup_policy(FileSystemId=resp["FileSystemId"])
    assert policy_resp["BackupPolicy"]["Status"] == "ENABLED"


def test_create_file_system_az_name_given_backup_default(efs):
    resp = efs.create_file_system(AvailabilityZoneName="us-east-1e")
    policy_resp = efs.describe_backup_policy(FileSystemId=resp["FileSystemId"])
    assert policy_resp["BackupPolicy"]["Status"] == "ENABLED"


def test_create_file_system_no_creation_token_given(efs):
    # Note that from the API docs, it would seem this should create an error. However it
    # turns out that botocore just automatically assigns a UUID.
    resp = efs.create_file_system()
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 201
    assert "CreationToken" in resp


def test_create_file_system_file_system_already_exists(efs):
    efs.create_file_system(CreationToken="foo")
    with pytest.raises(ClientError) as exc_info:
        efs.create_file_system(CreationToken="foo")
    resp = exc_info.value.response
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 409
    assert "FileSystemAlreadyExists" == resp["Error"]["Code"]


# Testing Describe
# ================


def test_describe_file_systems_using_identifier(efs):
    # Create the file system.
    create_fs_resp = efs.create_file_system(CreationToken="foobar")
    create_fs_resp.pop("ResponseMetadata")
    fs_id = create_fs_resp["FileSystemId"]

    # Describe the file system.
    desc_fs_resp = efs.describe_file_systems(FileSystemId=fs_id)
    assert len(desc_fs_resp["FileSystems"]) == 1
    assert desc_fs_resp["FileSystems"][0]["FileSystemId"] == fs_id
    assert desc_fs_resp["FileSystems"][0]["Name"] == ""


def test_describe_file_systems_using_unknown_identifier(efs):
    with pytest.raises(ClientError) as exc:
        efs.describe_file_systems(FileSystemId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "FileSystemNotFound"
    # Verified against AWS
    assert err["Message"] == "File system 'unknown' does not exist."


def test_describe_file_systems_minimal_case(efs):
    # Create the file system.
    create_fs_resp = efs.create_file_system(CreationToken="foobar")
    create_fs_resp.pop("ResponseMetadata")

    # Describe the file systems.
    desc_fs_resp = efs.describe_file_systems()
    desc_fs_resp_metadata = desc_fs_resp.pop("ResponseMetadata")
    assert desc_fs_resp_metadata["HTTPStatusCode"] == 200

    # Check the list results.
    fs_list = desc_fs_resp["FileSystems"]
    assert len(fs_list) == 1
    file_system = fs_list[0]
    assert set(file_system.keys()) == {
        "CreationTime",
        "CreationToken",
        "Encrypted",
        "LifeCycleState",
        "PerformanceMode",
        "SizeInBytes",
        "Tags",
        "ThroughputMode",
        "FileSystemId",
        "FileSystemArn",
        "NumberOfMountTargets",
        "OwnerId",
        "Name",
    }
    assert file_system["FileSystemId"] == create_fs_resp["FileSystemId"]
    assert file_system["Name"] == ""

    # Pop out the timestamps and see if the rest of the description is the same.
    create_fs_resp["SizeInBytes"].pop("Timestamp")
    file_system["SizeInBytes"].pop("Timestamp")
    assert file_system == create_fs_resp


def test_describe_file_systems_aws_create_sample_2(efs):
    efs.create_file_system(**SAMPLE_2_PARAMS)

    # Describe the file systems.
    desc_resp = efs.describe_file_systems()
    desc_fs_resp_metadata = desc_resp.pop("ResponseMetadata")
    assert desc_fs_resp_metadata["HTTPStatusCode"] == 200

    # Check the list results.
    fs_list = desc_resp["FileSystems"]
    assert len(fs_list) == 1
    file_system = fs_list[0]

    assert set(file_system.keys()) == {
        "AvailabilityZoneId",
        "AvailabilityZoneName",
        "CreationTime",
        "CreationToken",
        "Encrypted",
        "LifeCycleState",
        "PerformanceMode",
        "ProvisionedThroughputInMibps",
        "SizeInBytes",
        "Tags",
        "ThroughputMode",
        "FileSystemId",
        "FileSystemArn",
        "NumberOfMountTargets",
        "OwnerId",
        "Name",
    }
    assert file_system["ProvisionedThroughputInMibps"] == 60
    assert file_system["AvailabilityZoneId"] == "usw2-az1"
    assert file_system["AvailabilityZoneName"] == "us-west-2b"
    assert file_system["ThroughputMode"] == "provisioned"
    assert file_system["Name"] == "Test Group1"


def test_describe_file_systems_paging(efs):
    # Create several file systems.
    for i in range(10):
        efs.create_file_system(CreationToken=f"foobar_{i}")

    # First call (Start)
    # ------------------

    # Call the tested function
    resp1 = efs.describe_file_systems(MaxItems=4)

    # Check the response status
    assert has_status_code(resp1, 200)

    # Check content of the result.
    resp1.pop("ResponseMetadata")
    assert set(resp1.keys()) == {"NextMarker", "FileSystems"}
    assert len(resp1["FileSystems"]) == 4
    fs_id_set_1 = {fs["FileSystemId"] for fs in resp1["FileSystems"]}

    # Second call (Middle)
    # --------------------

    # Get the next marker.
    resp2 = efs.describe_file_systems(MaxItems=4, Marker=resp1["NextMarker"])

    # Check the response status
    resp2_metadata = resp2.pop("ResponseMetadata")
    assert resp2_metadata["HTTPStatusCode"] == 200

    # Check the response contents.
    assert set(resp2.keys()) == {"NextMarker", "FileSystems", "Marker"}
    assert len(resp2["FileSystems"]) == 4
    assert resp2["Marker"] == resp1["NextMarker"]
    fs_id_set_2 = {fs["FileSystemId"] for fs in resp2["FileSystems"]}
    assert fs_id_set_1 & fs_id_set_2 == set()

    # Third call (End)
    # ----------------

    # Get the last marker results
    resp3 = efs.describe_file_systems(MaxItems=4, Marker=resp2["NextMarker"])

    # Check the response status
    resp3_metadata = resp3.pop("ResponseMetadata")
    assert resp3_metadata["HTTPStatusCode"] == 200

    # Check the response contents.
    assert set(resp3.keys()) == {"FileSystems", "Marker"}
    assert len(resp3["FileSystems"]) == 2
    assert resp3["Marker"] == resp2["NextMarker"]
    fs_id_set_3 = {fs["FileSystemId"] for fs in resp3["FileSystems"]}
    assert fs_id_set_3 & (fs_id_set_1 | fs_id_set_2) == set()


def test_describe_file_systems_invalid_marker(efs):
    with pytest.raises(ClientError) as exc_info:
        efs.describe_file_systems(Marker="fiddlesticks")
    resp = exc_info.value.response
    assert has_status_code(resp, 400)
    assert "BadRequest" == resp["Error"]["Code"]


def test_describe_file_systems_invalid_creation_token(efs):
    resp = efs.describe_file_systems(CreationToken="fizzle")
    assert has_status_code(resp, 200)
    assert len(resp["FileSystems"]) == 0


def test_describe_file_systems_invalid_file_system_id(efs):
    with pytest.raises(ClientError) as exc_info:
        efs.describe_file_systems(FileSystemId="fs-29879313")
    resp = exc_info.value.response
    assert has_status_code(resp, 404)
    assert "FileSystemNotFound" == resp["Error"]["Code"]


def test_describe_file_system_creation_token_and_file_system_id(efs):
    with pytest.raises(ClientError) as exc_info:
        efs.describe_file_systems(CreationToken="fizzle", FileSystemId="fs-07987987")
    resp = exc_info.value.response
    assert has_status_code(resp, 400)
    assert "BadRequest" == resp["Error"]["Code"]


# Testing Delete
# ==============


def test_delete_file_system_minimal_case(efs):
    # Create the file system
    resp = efs.create_file_system()

    # Describe the file system, prove it shows up.
    desc1 = efs.describe_file_systems()
    assert len(desc1["FileSystems"]) == 1
    assert resp["FileSystemId"] in {fs["FileSystemId"] for fs in desc1["FileSystems"]}

    # Delete the file system.
    del_resp = efs.delete_file_system(FileSystemId=resp["FileSystemId"])
    assert has_status_code(del_resp, 204)

    # Check that the file system is no longer there.
    desc2 = efs.describe_file_systems()
    assert len(desc2["FileSystems"]) == 0


def test_delete_file_system_invalid_file_system_id(efs):
    with pytest.raises(ClientError) as exc_info:
        efs.delete_file_system(FileSystemId="fs-2394287")
    resp = exc_info.value.response
    assert has_status_code(resp, 404)
    assert "FileSystemNotFound" == resp["Error"]["Code"]
