from __future__ import unicode_literals

import re
import boto3
import pytest
import sure  # noqa
from os import environ
from moto import mock_efs


ARN_PATT = "^arn:(?P<Partition>[^:\n]*):(?P<Service>[^:\n]*):(?P<Region>[^:\n]*):(?P<AccountID>[^:\n]*):(?P<Ignore>(?P<ResourceType>[^:\/\n]*)[:\/])?(?P<Resource>.*)$"
STRICT_ARN_PATT = "^arn:aws:[a-z]+:[a-z]{2}-[a-z]+-[0-9]:[0-9]+:[a-z-]+\/[a-z0-9-]+$"


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

    match_obj = re.match(ARN_PATT, create_fs_resp["FileSystemArn"])
    arn_parts = match_obj.groupdict()
    arn_parts["ResourceType"].should.equal("file-system")
    arn_parts["Resource"].should.equal(create_fs_resp["FileSystemId"])
    arn_parts["Service"].should.equal("elasticfilesystem")
    arn_parts["AccountID"].should.equal(create_fs_resp["OwnerId"])


def test_create_file_system_aws_sample_1(efs):
    sample_params = {
        "CreationToken": "myFileSystem1",
        "PerformanceMode": "generalPurpose",
        "Backup": True,
        "Encrypted": True,
        "Tags": [{"Key": "Name", "Value": "Test Group1"}],
    }
    resp = efs.create_file_system(**sample_params)
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


def test_create_file_system_aws_sample_2(efs):
    sample_params = {
        "CreationToken": "myFileSystem2",
        "PerformanceMode": "generalPurpose",
        "Backup": True,
        "AvailabilityZoneName": "us-west-2b",
        "Encrypted": True,
        "ThroughputMode": "provisioned",
        "ProvisionedThroughputInMibps": 60,
        "Tags": [{"Key": "Name", "Value": "Test Group1"}],
    }
    resp = efs.create_file_system(**sample_params)
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
