from __future__ import unicode_literals

from ipaddress import IPv4Network
from os import environ

import boto3
import pytest
import sure  # noqa
from botocore.exceptions import ClientError

from moto import mock_ec2, mock_efs
from moto.core import ACCOUNT_ID
from tests.test_efs.junk_drawer import has_status_code


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


@pytest.fixture(scope="function")
def file_system(efs):
    create_fs_resp = efs.create_file_system(CreationToken="foobarbaz")
    create_fs_resp.pop("ResponseMetadata")
    yield create_fs_resp


@pytest.fixture(scope="function")
def subnet(ec2):
    desc_sn_resp = ec2.describe_subnets()
    subnet = desc_sn_resp["Subnets"][0]
    yield subnet


def test_create_mount_target_minimal_correct_use(efs, file_system, subnet):
    subnet_id = subnet["SubnetId"]
    file_system_id = file_system["FileSystemId"]

    # Create the mount target.
    create_mt_resp = efs.create_mount_target(
        FileSystemId=file_system_id, SubnetId=subnet_id
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
    create_mt_resp["FileSystemId"].should.equal(file_system_id)
    create_mt_resp["OwnerId"].should.equal(ACCOUNT_ID)
    create_mt_resp["LifeCycleState"].should.equal("available")

    # Check that the number of mount targets in the fs is correct.
    desc_fs_resp = efs.describe_file_systems()
    file_system = desc_fs_resp["FileSystems"][0]
    file_system["NumberOfMountTargets"].should.equal(1)
    return


def test_create_mount_target_aws_sample_2(efs, ec2, file_system, subnet):
    subnet_id = subnet["SubnetId"]
    file_system_id = file_system["FileSystemId"]
    subnet_network = IPv4Network(subnet["CidrBlock"])
    for ip_addr_obj in subnet_network.hosts():
        ip_addr = ip_addr_obj.exploded
        break
    else:
        assert False, "Could not generate an IP address from CIDR block: {}".format(
            subnet["CidrBlock"]
        )
    desc_sg_resp = ec2.describe_security_groups()
    security_group = desc_sg_resp["SecurityGroups"][0]
    security_group_id = security_group["GroupId"]

    # Make sure nothing chokes.
    sample_input = {
        "FileSystemId": file_system_id,
        "SubnetId": subnet_id,
        "IpAddress": ip_addr,
        "SecurityGroups": [security_group_id],
    }
    create_mt_resp = efs.create_mount_target(**sample_input)

    # Check the mount target response code.
    resp_metadata = create_mt_resp.pop("ResponseMetadata")
    resp_metadata["HTTPStatusCode"].should.equal(200)

    # Check that setting the IP Address worked.
    create_mt_resp["IpAddress"].should.equal(ip_addr)


def test_delete_file_system_mount_targets_attached(efs, ec2, file_system, subnet):
    efs.create_mount_target(
        FileSystemId=file_system["FileSystemId"], SubnetId=subnet["SubnetId"]
    )
    try:
        efs.delete_file_system(FileSystemId=file_system["FileSystemId"])
    except ClientError as e:
        assert has_status_code(e.response, 409)
        assert "FileSystemInUse" in e.response["Error"]["Message"]
    except Exception as e:
        assert False, "Got an unexpected exception: {}".format(e)
    else:
        assert False, "Expected an FileSystemInUse error."


def test_describe_mount_targets_minimal_case(efs, ec2, file_system, subnet):
    create_resp = efs.create_mount_target(
        FileSystemId=file_system["FileSystemId"], SubnetId=subnet["SubnetId"]
    )
    create_resp.pop("ResponseMetadata")

    # Describe the mount targets
    desc_mt_resp = efs.describe_mount_targets(FileSystemId=file_system["FileSystemId"])
    desc_mt_resp_metadata = desc_mt_resp.pop("ResponseMetadata")
    assert desc_mt_resp_metadata["HTTPStatusCode"] == 200

    # Check the list results.
    mt_list = desc_mt_resp["MountTargets"]
    assert len(mt_list) == 1
    mount_target = mt_list[0]
    assert mount_target["MountTargetId"] == create_resp["MountTargetId"]

    # Pop out the timestamps and see if the rest of the description is the same.
    assert mount_target == create_resp


def test_describe_file_systems_paging(efs, ec2, file_system):
    fs_id = file_system["FileSystemId"]

    # Get a list of subnets.
    subnet_list = ec2.describe_subnets()["Subnets"]

    # Create several mount targets.
    for subnet in subnet_list:
        efs.create_mount_target(FileSystemId=fs_id, SubnetId=subnet["SubnetId"])

    # First call (Start)
    # ------------------

    # Call the tested function
    resp1 = efs.describe_mount_targets(FileSystemId=fs_id, MaxItems=2)

    # Check the response status
    assert has_status_code(resp1, 200)

    # Check content of the result.
    resp1.pop("ResponseMetadata")
    assert set(resp1.keys()) == {"NextMarker", "MountTargets"}
    assert len(resp1["MountTargets"]) == 2
    mt_id_set_1 = {mt["MountTargetId"] for mt in resp1["MountTargets"]}

    # Second call (Middle)
    # --------------------

    # Get the next marker.
    resp2 = efs.describe_mount_targets(
        FileSystemId=fs_id, MaxItems=2, Marker=resp1["NextMarker"]
    )

    # Check the response status
    resp2_metadata = resp2.pop("ResponseMetadata")
    assert resp2_metadata["HTTPStatusCode"] == 200

    # Check the response contents.
    assert set(resp2.keys()) == {"NextMarker", "MountTargets", "Marker"}
    assert len(resp2["MountTargets"]) == 2
    assert resp2["Marker"] == resp1["NextMarker"]
    mt_id_set_2 = {mt["MountTargetId"] for mt in resp2["MountTargets"]}
    assert mt_id_set_1 & mt_id_set_2 == set()

    # Third call (End)
    # ----------------

    # Get the last marker results
    resp3 = efs.describe_mount_targets(
        FileSystemId=fs_id, MaxItems=20, Marker=resp2["NextMarker"]
    )

    # Check the response status
    resp3_metadata = resp3.pop("ResponseMetadata")
    assert resp3_metadata["HTTPStatusCode"] == 200

    # Check the response contents.
    assert set(resp3.keys()) == {"MountTargets", "Marker"}
    assert resp3["Marker"] == resp2["NextMarker"]
    mt_id_set_3 = {mt["MountTargetId"] for mt in resp3["MountTargets"]}
    assert mt_id_set_3 & (mt_id_set_1 | mt_id_set_2) == set()
