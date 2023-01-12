import re
from ipaddress import IPv4Network

import pytest
from botocore.exceptions import ClientError

from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests.test_efs.junk_drawer import has_status_code
from . import fixture_ec2, fixture_efs  # noqa # pylint: disable=unused-import


@pytest.fixture(scope="function", name="file_system")
def fixture_file_system(efs):
    create_fs_resp = efs.create_file_system(CreationToken="foobarbaz")
    create_fs_resp.pop("ResponseMetadata")
    yield create_fs_resp


@pytest.fixture(scope="function", name="subnet")
def fixture_subnet(ec2):
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
    assert resp_metadata["HTTPStatusCode"] == 200

    # Check the mount target response body.
    assert re.match("^fsmt-[a-f0-9]+$", create_mt_resp["MountTargetId"])
    assert re.match("^eni-[a-f0-9]+$", create_mt_resp["NetworkInterfaceId"])
    assert create_mt_resp["AvailabilityZoneId"] == subnet["AvailabilityZoneId"]
    assert create_mt_resp["AvailabilityZoneName"] == subnet["AvailabilityZone"]
    assert create_mt_resp["VpcId"] == subnet["VpcId"]
    assert create_mt_resp["SubnetId"] == subnet_id
    assert IPv4Network(create_mt_resp["IpAddress"]).subnet_of(
        IPv4Network(subnet["CidrBlock"])
    )
    assert create_mt_resp["FileSystemId"] == file_system_id
    assert create_mt_resp["OwnerId"] == ACCOUNT_ID
    assert create_mt_resp["LifeCycleState"] == "available"

    # Check that the number of mount targets in the fs is correct.
    desc_fs_resp = efs.describe_file_systems()
    file_system = desc_fs_resp["FileSystems"][0]
    assert file_system["NumberOfMountTargets"] == 1
    return


def test_create_mount_target_aws_sample_2(efs, ec2, file_system, subnet):
    subnet_id = subnet["SubnetId"]
    file_system_id = file_system["FileSystemId"]
    subnet_network = IPv4Network(subnet["CidrBlock"])
    for ip_addr_obj in subnet_network.hosts():
        ip_addr = ip_addr_obj.exploded
        break
    else:
        assert (
            False
        ), f"Could not generate an IP address from CIDR block: {subnet['CidrBlock']}"
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
    assert resp_metadata["HTTPStatusCode"] == 200

    # Check that setting the IP Address worked.
    assert create_mt_resp["IpAddress"] == ip_addr


def test_create_mount_target_invalid_file_system_id(efs, subnet):
    with pytest.raises(ClientError) as exc_info:
        efs.create_mount_target(FileSystemId="fs-12343289", SubnetId=subnet["SubnetId"])
    resp = exc_info.value.response
    assert has_status_code(resp, 404)
    assert "FileSystemNotFound" == resp["Error"]["Code"]


def test_create_mount_target_invalid_subnet_id(efs, file_system):
    with pytest.raises(ClientError) as exc_info:
        efs.create_mount_target(
            FileSystemId=file_system["FileSystemId"], SubnetId="subnet-12345678"
        )
    resp = exc_info.value.response
    assert has_status_code(resp, 404)
    assert "SubnetNotFound" == resp["Error"]["Code"]


def test_create_mount_target_invalid_sg_id(efs, file_system, subnet):
    with pytest.raises(ClientError) as exc_info:
        efs.create_mount_target(
            FileSystemId=file_system["FileSystemId"],
            SubnetId=subnet["SubnetId"],
            SecurityGroups=["sg-1234df235"],
        )
    resp = exc_info.value.response
    assert has_status_code(resp, 404)
    assert "SecurityGroupNotFound" == resp["Error"]["Code"]


def test_create_second_mount_target_wrong_vpc(efs, ec2, file_system, subnet):
    vpc_info = ec2.create_vpc(CidrBlock="10.1.0.0/16")
    new_subnet_info = ec2.create_subnet(
        VpcId=vpc_info["Vpc"]["VpcId"], CidrBlock="10.1.1.0/24"
    )
    efs.create_mount_target(
        FileSystemId=file_system["FileSystemId"], SubnetId=subnet["SubnetId"]
    )
    with pytest.raises(ClientError) as exc_info:
        efs.create_mount_target(
            FileSystemId=file_system["FileSystemId"],
            SubnetId=new_subnet_info["Subnet"]["SubnetId"],
        )
    resp = exc_info.value.response
    assert has_status_code(resp, 409)
    assert "MountTargetConflict" == resp["Error"]["Code"]
    assert "VPC" in resp["Error"]["Message"]


def test_create_mount_target_duplicate_subnet_id(efs, file_system, subnet):
    efs.create_mount_target(
        FileSystemId=file_system["FileSystemId"], SubnetId=subnet["SubnetId"]
    )
    with pytest.raises(ClientError) as exc_info:
        efs.create_mount_target(
            FileSystemId=file_system["FileSystemId"], SubnetId=subnet["SubnetId"]
        )
    resp = exc_info.value.response
    assert has_status_code(resp, 409)
    assert "MountTargetConflict" == resp["Error"]["Code"]
    assert "AZ" in resp["Error"]["Message"]


def test_create_mount_target_subnets_in_same_zone(efs, ec2, file_system, subnet):
    efs.create_mount_target(
        FileSystemId=file_system["FileSystemId"], SubnetId=subnet["SubnetId"]
    )
    subnet_info = ec2.create_subnet(
        VpcId=subnet["VpcId"],
        CidrBlock="172.31.96.0/20",
        AvailabilityZone=subnet["AvailabilityZone"],
    )
    with pytest.raises(ClientError) as exc_info:
        efs.create_mount_target(
            FileSystemId=file_system["FileSystemId"],
            SubnetId=subnet_info["Subnet"]["SubnetId"],
        )
    resp = exc_info.value.response
    assert has_status_code(resp, 409)
    assert "MountTargetConflict" == resp["Error"]["Code"]
    assert "AZ" in resp["Error"]["Message"]


def test_create_mount_target_ip_address_out_of_range(efs, file_system, subnet):
    with pytest.raises(ClientError) as exc_info:
        efs.create_mount_target(
            FileSystemId=file_system["FileSystemId"],
            SubnetId=subnet["SubnetId"],
            IpAddress="10.0.1.0",
        )
    resp = exc_info.value.response
    assert has_status_code(resp, 400)
    assert "BadRequest" == resp["Error"]["Code"]
    assert "Address" in resp["Error"]["Message"]


def test_create_mount_target_too_many_security_groups(efs, ec2, file_system, subnet):
    sg_id_list = []
    for i in range(6):
        sg_info = ec2.create_security_group(
            VpcId=subnet["VpcId"],
            GroupName=f"sg-{i}",
            Description=f"SG-{i} protects us from the Goa'uld.",
        )
        sg_id_list.append(sg_info["GroupId"])
    with pytest.raises(ClientError) as exc_info:
        efs.create_mount_target(
            FileSystemId=file_system["FileSystemId"],
            SubnetId=subnet["SubnetId"],
            SecurityGroups=sg_id_list,
        )
    resp = exc_info.value.response
    assert has_status_code(resp, 400)
    assert "SecurityGroupLimitExceeded" == resp["Error"]["Code"]


def test_delete_file_system_mount_targets_attached(
    efs, ec2, file_system, subnet
):  # pylint: disable=unused-argument
    efs.create_mount_target(
        FileSystemId=file_system["FileSystemId"], SubnetId=subnet["SubnetId"]
    )
    with pytest.raises(ClientError) as exc_info:
        efs.delete_file_system(FileSystemId=file_system["FileSystemId"])
    resp = exc_info.value.response
    assert has_status_code(resp, 409)
    assert "FileSystemInUse" == resp["Error"]["Code"]


def test_describe_mount_targets_minimal_case(
    efs, ec2, file_system, subnet
):  # pylint: disable=unused-argument
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


def test_describe_mount_targets__by_access_point_id(
    efs, ec2, file_system, subnet
):  # pylint: disable=unused-argument
    create_resp = efs.create_mount_target(
        FileSystemId=file_system["FileSystemId"], SubnetId=subnet["SubnetId"]
    )
    create_resp.pop("ResponseMetadata")

    ap_resp = efs.create_access_point(
        ClientToken="ct1", FileSystemId=file_system["FileSystemId"]
    )
    access_point_id = ap_resp["AccessPointId"]

    # Describe the mount targets
    ap_resp = efs.describe_mount_targets(AccessPointId=access_point_id)

    # Check the list results.
    ap_resp.should.have.key("MountTargets").length_of(1)
    ap_resp["MountTargets"][0]["MountTargetId"].should.equal(
        create_resp["MountTargetId"]
    )


def test_describe_mount_targets_paging(efs, ec2, file_system):
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


def test_describe_mount_targets_invalid_file_system_id(efs):
    with pytest.raises(ClientError) as exc_info:
        efs.describe_mount_targets(FileSystemId="fs-12343289")
    resp = exc_info.value.response
    assert has_status_code(resp, 404)
    assert "FileSystemNotFound" == resp["Error"]["Code"]


def test_describe_mount_targets_invalid_mount_target_id(efs):
    with pytest.raises(ClientError) as exc_info:
        efs.describe_mount_targets(MountTargetId="fsmt-ad9f8987")
    resp = exc_info.value.response
    assert has_status_code(resp, 404)
    assert "MountTargetNotFound" == resp["Error"]["Code"]


def test_describe_mount_targets_no_id_given(efs):
    with pytest.raises(ClientError) as exc_info:
        efs.describe_mount_targets()
    resp = exc_info.value.response
    assert has_status_code(resp, 400)
    assert "BadRequest" == resp["Error"]["Code"]


def test_delete_mount_target_minimal_case(efs, file_system, subnet):
    mt_info = efs.create_mount_target(
        FileSystemId=file_system["FileSystemId"], SubnetId=subnet["SubnetId"]
    )
    resp = efs.delete_mount_target(MountTargetId=mt_info["MountTargetId"])
    assert has_status_code(resp, 204)
    desc_resp = efs.describe_mount_targets(FileSystemId=file_system["FileSystemId"])
    assert len(desc_resp["MountTargets"]) == 0


def test_delete_mount_target_invalid_mount_target_id(efs):
    with pytest.raises(ClientError) as exc_info:
        efs.delete_mount_target(MountTargetId="fsmt-98487aef0a7")
    resp = exc_info.value.response
    assert has_status_code(resp, 404)
    assert "MountTargetNotFound" == resp["Error"]["Code"]
