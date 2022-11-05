import pytest
from botocore.exceptions import ClientError

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


def test_describe_mount_target_security_groups__unknown(efs):
    with pytest.raises(ClientError) as exc_info:
        efs.describe_mount_target_security_groups(MountTargetId="mt-asdf1234asdf")
    err = exc_info.value.response["Error"]
    err["Code"].should.equal("MountTargetNotFound")
    err["Message"].should.equal("Mount target 'mt-asdf1234asdf' does not exist.")


def test_describe_mount_target_security_groups(efs, ec2, file_system, subnet):
    subnet_id = subnet["SubnetId"]
    file_system_id = file_system["FileSystemId"]

    desc_sg_resp = ec2.describe_security_groups()
    security_group_id = desc_sg_resp["SecurityGroups"][0]["GroupId"]

    # Create Mount Target
    sample_input = {
        "FileSystemId": file_system_id,
        "SubnetId": subnet_id,
        "SecurityGroups": [security_group_id],
    }
    create_mt_resp = efs.create_mount_target(**sample_input)
    mount_target_id = create_mt_resp["MountTargetId"]

    # Describe it's Security Groups
    resp = efs.describe_mount_target_security_groups(MountTargetId=mount_target_id)
    resp.should.have.key("SecurityGroups").equals([security_group_id])


def test_modify_mount_target_security_groups__unknown(efs):
    with pytest.raises(ClientError) as exc_info:
        efs.modify_mount_target_security_groups(
            MountTargetId="mt-asdf1234asdf", SecurityGroups=[]
        )
    err = exc_info.value.response["Error"]
    err["Code"].should.equal("MountTargetNotFound")
    err["Message"].should.equal("Mount target 'mt-asdf1234asdf' does not exist.")


def test_modify_mount_target_security_groups(efs, ec2, file_system, subnet):
    subnet_id = subnet["SubnetId"]
    file_system_id = file_system["FileSystemId"]

    desc_sg_resp = ec2.describe_security_groups()["SecurityGroups"]
    security_group_id = desc_sg_resp[0]["GroupId"]

    # Create Mount Target
    sample_input = {
        "FileSystemId": file_system_id,
        "SubnetId": subnet_id,
        "SecurityGroups": [security_group_id],
    }
    create_mt_resp = efs.create_mount_target(**sample_input)
    mount_target_id = create_mt_resp["MountTargetId"]
    network_interface_id = create_mt_resp["NetworkInterfaceId"]

    # Create alternative security groups
    sg_id_2 = ec2.create_security_group(
        VpcId=subnet["VpcId"], GroupName="sg-2", Description="SG-2"
    )["GroupId"]
    sg_id_3 = ec2.create_security_group(
        VpcId=subnet["VpcId"], GroupName="sg-3", Description="SG-3"
    )["GroupId"]

    # Modify it's Security Groups
    efs.modify_mount_target_security_groups(
        MountTargetId=mount_target_id, SecurityGroups=[sg_id_2, sg_id_3]
    )

    # Describe it's Security Groups
    resp = efs.describe_mount_target_security_groups(MountTargetId=mount_target_id)
    resp.should.have.key("SecurityGroups").equals([sg_id_2, sg_id_3])

    # Verify EC2 reflects this change
    resp = ec2.describe_network_interfaces(NetworkInterfaceIds=[network_interface_id])
    network_interface = resp["NetworkInterfaces"][0]
    network_interface["Groups"].should.have.length_of(2)
    set([sg["GroupId"] for sg in network_interface["Groups"]]).should.equal(
        {sg_id_2, sg_id_3}
    )
