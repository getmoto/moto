from __future__ import unicode_literals

import re
from os import environ

import boto3
import pytest
import sure  # noqa
from botocore.exceptions import ClientError

from moto import mock_efs

ARN_PATT = "^arn:(?P<Partition>[^:\n]*):(?P<Service>[^:\n]*):(?P<Region>[^:\n]*):(?P<AccountID>[^:\n]*):(?P<Ignore>(?P<ResourceType>[^:\/\n]*)[:\/])?(?P<Resource>.*)$"
STRICT_ARN_PATT = "^arn:aws:[a-z]+:[a-z]{2}-[a-z]+-[0-9]:[0-9]+:[a-z-]+\/[a-z0-9-]+$"

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


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    environ["AWS_ACCESS_KEY_ID"] = "testing"
    environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    environ["AWS_SECURITY_TOKEN"] = "testing"
    environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(scope="function")
def efs(aws_credentials):
    with mock_efs():
        yield boto3.client("efs", region_name="us-east-1")


# Testing Create
# ==============


def test_create_file_system_correct_use(efs):
    creation_token = "test_efs_create"
    create_fs_resp = efs.create_file_system(
        CreationToken=creation_token,
        Tags=[{"Key": "Name", "Value": "Test EFS Container"}],
    )

    # Check the response.
    create_fs_resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)
    create_fs_resp["CreationToken"].should.equal(creation_token)
    create_fs_resp["FileSystemId"].should.contain("fs-")
    create_fs_resp["CreationTime"].should.be.a("datetime.datetime")
    create_fs_resp["LifeCycleState"].should.equal("available")
    create_fs_resp["Tags"][0].should.equal(
        {"Key": "Name", "Value": "Test EFS Container"}
    )
    create_fs_resp["ThroughputMode"].should.equal("bursting")
    create_fs_resp["PerformanceMode"].should.equal("generalPurpose")
    create_fs_resp["Encrypted"].should.equal(False)
    create_fs_resp["NumberOfMountTargets"].should.equal(0)
    for key_name in ["Value", "ValueInIA", "ValueInStandard"]:
        create_fs_resp["SizeInBytes"].should.have.key(key_name)
        create_fs_resp["SizeInBytes"][key_name].should.equal(0)
    create_fs_resp["FileSystemArn"].should.match(STRICT_ARN_PATT)

    # Check the (lack of the) backup policy.
    try:
        efs.describe_backup_policy(FileSystemId=create_fs_resp["FileSystemId"])
    except ClientError as e:
        assert e.response["ResponseMetadata"]["HTTPStatusCode"] == 404
        assert "PolicyNotFound" in e.response["Error"]["Message"]
    else:
        assert False, "Found backup policy when there should be none."

    # Check the arn in detail
    match_obj = re.match(ARN_PATT, create_fs_resp["FileSystemArn"])
    arn_parts = match_obj.groupdict()
    arn_parts["ResourceType"].should.equal("file-system")
    arn_parts["Resource"].should.equal(create_fs_resp["FileSystemId"])
    arn_parts["Service"].should.equal("elasticfilesystem")
    arn_parts["AccountID"].should.equal(create_fs_resp["OwnerId"])


def test_create_file_system_aws_sample_1(efs):
    resp = efs.create_file_system(**SAMPLE_1_PARAMS)
    resp_metadata = resp.pop("ResponseMetadata")
    resp_metadata["HTTPStatusCode"].should.equal(201)
    set(resp.keys()).should.equal(
        {
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
        }
    )
    resp["Tags"].should.equal([{"Key": "Name", "Value": "Test Group1"}])
    resp["PerformanceMode"].should.equal("generalPurpose")
    resp["Encrypted"].should.equal(True)

    policy_resp = efs.describe_backup_policy(FileSystemId=resp["FileSystemId"])
    assert policy_resp["BackupPolicy"]["Status"] == "ENABLED"


def test_create_file_system_aws_sample_2(efs):
    resp = efs.create_file_system(**SAMPLE_2_PARAMS)
    resp_metadata = resp.pop("ResponseMetadata")
    resp_metadata["HTTPStatusCode"].should.equal(201)
    set(resp.keys()).should.equal(
        {
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
        }
    )
    resp["ProvisionedThroughputInMibps"].should.equal(60)
    resp["AvailabilityZoneId"].should.equal("usw2-az1")
    resp["AvailabilityZoneName"].should.equal("us-west-2b")
    resp["ThroughputMode"].should.equal("provisioned")

    policy_resp = efs.describe_backup_policy(FileSystemId=resp["FileSystemId"])
    assert policy_resp["BackupPolicy"]["Status"] == "ENABLED"


def test_create_file_system_az_name_given_backup_default(efs):
    resp = efs.create_file_system(AvailabilityZoneName="us-east-1e")
    policy_resp = efs.describe_backup_policy(FileSystemId=resp["FileSystemId"])
    assert policy_resp["BackupPolicy"]["Status"] == "ENABLED"


# Testing Describe
# ================


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
    }
    assert file_system["FileSystemId"] == create_fs_resp["FileSystemId"]

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
    }
    assert file_system["ProvisionedThroughputInMibps"] == 60
    assert file_system["AvailabilityZoneId"] == "usw2-az1"
    assert file_system["AvailabilityZoneName"] == "us-west-2b"
    assert file_system["ThroughputMode"] == "provisioned"


def test_describe_file_systems_paging(efs):
    # Create several file systems.
    for i in range(10):
        efs.create_file_system(CreationToken="foobar_{}".format(i))

    # First call (Start)
    # ------------------

    # Call the tested function
    resp1 = efs.describe_file_systems(MaxItems=4)

    # Check the response status
    resp1_metadata = resp1.pop("ResponseMetadata")
    assert resp1_metadata["HTTPStatusCode"] == 200

    # Check content of the result.
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
