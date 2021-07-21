from __future__ import unicode_literals

from ipaddress import IPv4Network
from os import environ

import boto3
import pytest
import sure  # noqa

from moto import mock_ec2, mock_efs
from moto.core import ACCOUNT_ID


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    environ["AWS_ACCESS_KEY_ID"] = "testing"
    environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    environ["AWS_SECURITY_TOKEN"] = "testing"
    environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(scope="function")
def ec2(aws_credentials):
    with mock_ec2():
        yield boto3.client("ec2", region_name="us-east-1")


@pytest.fixture(scope="function")
def efs(aws_credentials):
    with mock_efs():
        yield boto3.client("efs", region_name="us-east-1")


def test_create_mount_target_minimal_correct_use(efs, ec2):
    # Create a file system.
    create_fs_resp = efs.create_file_system(CreationToken="foobarbaz")

    # Choose a subnet.
    desc_sn_resp = ec2.describe_subnets()
    subnet = desc_sn_resp["Subnets"][0]
    subnet_id = subnet["SubnetId"]

    # Create the mount target.
    create_mt_resp = efs.create_mount_target(
        FileSystemId=create_fs_resp["FileSystemId"], SubnetId=subnet_id
    )

    # Check the mount target response code.
    resp_metadata = create_mt_resp.pop("ResponseMetadata")
    resp_metadata["HTTPStatusCode"].should.equal(200)

    # Check the mount target response body.
    create_mt_resp["MountTargetId"].should.match("^fsmt-[a-f0-9]+$")
    create_mt_resp["NetworkInterfaceId"].should.match("^eni-[a-f0-9]+$")
    create_mt_resp["AvailabilityZoneId"].should.equal(subnet["AvailabilityZoneId"])
    create_mt_resp["AvailabilityZoneName"].should.equal(subnet["AvailabilityZone"])
    create_mt_resp["VpcId"].should.equal(subnet["VpcId"])
    create_mt_resp["SubnetId"].should.equal(subnet_id)
    assert IPv4Network(create_mt_resp["IpAddress"]).subnet_of(
        IPv4Network(subnet["CidrBlock"])
    )
    create_mt_resp["FileSystemId"].should.equal(create_fs_resp["FileSystemId"])
    create_mt_resp["OwnerId"].should.equal(ACCOUNT_ID)

    # Check that the number of mount targets in the fs is correct.
    desc_fs_resp = efs.describe_file_systems()
    file_system = desc_fs_resp["FileSystems"][0]
    file_system["NumberOfMountTargets"].should.equal(1)
    return
