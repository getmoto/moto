import pytest

import boto
import boto3
from boto.exception import EC2ResponseError
from botocore.exceptions import ClientError
from uuid import uuid4

import sure  # noqa # pylint: disable=unused-import

from moto import mock_ec2, mock_ec2_deprecated
from tests import EXAMPLE_AMI_ID

import logging


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_allocate_classic():
    """Allocate/release Classic EIP"""
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as ex:
        standard = conn.allocate_address(dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the AllocateAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    standard = conn.allocate_address()
    standard.should.be.a(boto.ec2.address.Address)
    standard.public_ip.should.be.a(str)
    standard.instance_id.should.be.none
    standard.domain.should.be.equal("standard")

    with pytest.raises(EC2ResponseError) as ex:
        standard.release(dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ReleaseAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    standard.release()
    standard.should_not.be.within(conn.get_all_addresses())


@mock_ec2
def test_eip_allocate_classic_boto3():
    """Allocate/release Classic EIP"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.allocate_address(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the AllocateAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    standard = client.allocate_address()
    standard.should.have.key("PublicIp")
    standard.should.have.key("Domain").equal("standard")

    public_ip = standard["PublicIp"]

    standard = ec2.ClassicAddress(public_ip)
    standard.load()

    with pytest.raises(ClientError) as ex:
        standard.release(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the ReleaseAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    standard.release()

    all_addresses = client.describe_addresses()["Addresses"]
    [a["PublicIp"] for a in all_addresses].shouldnt.contain(public_ip)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_allocate_vpc():
    """Allocate/release VPC EIP"""
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as ex:
        vpc = conn.allocate_address(domain="vpc", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the AllocateAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    vpc = conn.allocate_address(domain="vpc")
    vpc.should.be.a(boto.ec2.address.Address)
    vpc.domain.should.be.equal("vpc")
    logging.debug("vpc alloc_id:".format(vpc.allocation_id))
    vpc.release()


@mock_ec2
def test_describe_addresses_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_addresses(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DescribeAddresses operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
def test_eip_allocate_vpc_boto3():
    """Allocate/release VPC EIP"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.allocate_address(Domain="vpc", DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the AllocateAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    vpc = client.allocate_address(Domain="vpc")
    vpc.should.have.key("AllocationId")
    vpc.should.have.key("Domain").equal("vpc")

    allocation_id = vpc["AllocationId"]

    all_addresses = client.describe_addresses()["Addresses"]
    [a["AllocationId"] for a in all_addresses if "AllocationId" in a].should.contain(
        allocation_id
    )

    vpc = ec2.VpcAddress(allocation_id)
    vpc.release()

    all_addresses = client.describe_addresses()["Addresses"]
    [a["AllocationId"] for a in all_addresses if "AllocationId" in a].shouldnt.contain(
        allocation_id
    )


@mock_ec2
def test_specific_eip_allocate_vpc():
    """Allocate VPC EIP with specific address"""
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = client.allocate_address(Domain="vpc", Address="127.38.43.222")
    vpc["Domain"].should.be.equal("vpc")
    vpc["PublicIp"].should.be.equal("127.38.43.222")
    logging.debug("vpc alloc_id:".format(vpc["AllocationId"]))


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_allocate_invalid_domain():
    """Allocate EIP invalid domain"""
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.allocate_address(domain="bogus")
    cm.value.code.should.equal("InvalidParameterValue")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_eip_allocate_invalid_domain_boto3():
    """Allocate EIP invalid domain"""
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.allocate_address(Domain="bogus")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("InvalidParameterValue")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_associate_classic():
    """Associate/Disassociate EIP to classic instance"""
    conn = boto.connect_ec2("the_key", "the_secret")

    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    eip = conn.allocate_address()
    eip.instance_id.should.be.none

    with pytest.raises(EC2ResponseError) as cm:
        conn.associate_address(public_ip=eip.public_ip)
    cm.value.code.should.equal("MissingParameter")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    with pytest.raises(EC2ResponseError) as ex:
        conn.associate_address(
            instance_id=instance.id, public_ip=eip.public_ip, dry_run=True
        )
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the AssociateAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.associate_address(instance_id=instance.id, public_ip=eip.public_ip)
    # no .update() on address ):
    eip = conn.get_all_addresses(addresses=[eip.public_ip])[0]
    eip.instance_id.should.be.equal(instance.id)

    with pytest.raises(EC2ResponseError) as ex:
        conn.disassociate_address(public_ip=eip.public_ip, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DisAssociateAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.disassociate_address(public_ip=eip.public_ip)
    # no .update() on address ):
    eip = conn.get_all_addresses(addresses=[eip.public_ip])[0]
    eip.instance_id.should.be.equal("")
    eip.release()
    eip.should_not.be.within(conn.get_all_addresses())
    eip = None

    instance.terminate()


@mock_ec2
def test_eip_associate_classic_boto3():
    """Associate/Disassociate EIP to classic instance"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = ec2.Instance(reservation["Instances"][0]["InstanceId"])

    eip = client.allocate_address()
    eip = ec2.ClassicAddress(eip["PublicIp"])
    eip.instance_id.should.be.empty

    with pytest.raises(ClientError) as ex:
        client.associate_address(PublicIp=eip.public_ip)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("MissingParameter")
    ex.value.response["Error"]["Message"].should.equal(
        "Invalid request, expect InstanceId/NetworkId parameter."
    )

    with pytest.raises(ClientError) as ex:
        client.associate_address(
            InstanceId=instance.id, PublicIp=eip.public_ip, DryRun=True
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the AssociateAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    client.associate_address(InstanceId=instance.id, PublicIp=eip.public_ip)
    eip.reload()
    eip.instance_id.should.be.equal(instance.id)

    with pytest.raises(ClientError) as ex:
        client.disassociate_address(PublicIp=eip.public_ip, DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DisAssociateAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    client.disassociate_address(PublicIp=eip.public_ip)
    eip.reload()
    eip.instance_id.should.be.equal("")
    eip.release()

    with pytest.raises(ClientError) as ex:
        client.describe_addresses(PublicIps=[eip.public_ip])
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidAddress.NotFound")
    err["Message"].should.equal("Address '{'" + eip.public_ip + "'}' not found.")

    instance.terminate()


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_associate_vpc():
    """Associate/Disassociate EIP to VPC instance"""
    conn = boto.connect_ec2("the_key", "the_secret")

    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    eip = conn.allocate_address(domain="vpc")
    eip.instance_id.should.be.none

    with pytest.raises(EC2ResponseError) as cm:
        conn.associate_address(allocation_id=eip.allocation_id)
    cm.value.code.should.equal("MissingParameter")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    conn.associate_address(instance_id=instance.id, allocation_id=eip.allocation_id)
    # no .update() on address ):
    eip = conn.get_all_addresses(addresses=[eip.public_ip])[0]
    eip.instance_id.should.be.equal(instance.id)
    conn.disassociate_address(association_id=eip.association_id)
    # no .update() on address ):
    eip = conn.get_all_addresses(addresses=[eip.public_ip])[0]
    eip.instance_id.should.be.equal("")
    eip.association_id.should.be.none

    with pytest.raises(EC2ResponseError) as ex:
        eip.release(dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ReleaseAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    eip.release()
    eip = None

    instance.terminate()


@mock_ec2
def test_eip_associate_vpc_boto3():
    """Associate/Disassociate EIP to VPC instance"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = ec2.Instance(reservation["Instances"][0]["InstanceId"])

    eip = client.allocate_address(Domain="vpc")
    eip.shouldnt.have.key("InstanceId")
    eip = ec2.VpcAddress(eip["AllocationId"])

    with pytest.raises(ClientError) as ex:
        client.associate_address(AllocationId=eip.allocation_id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("MissingParameter")
    ex.value.response["Error"]["Message"].should.equal(
        "Invalid request, expect InstanceId/NetworkId parameter."
    )

    client.associate_address(InstanceId=instance.id, AllocationId=eip.allocation_id)

    eip.reload()
    eip.instance_id.should.be.equal(instance.id)
    client.disassociate_address(AssociationId=eip.association_id)

    eip.reload()
    eip.instance_id.should.be.equal("")
    eip.association_id.should.be.none

    with pytest.raises(ClientError) as ex:
        eip.release(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the ReleaseAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    eip.release()
    instance.terminate()


@mock_ec2
def test_eip_boto3_vpc_association():
    """Associate EIP to VPC instance in a new subnet with boto3"""
    service = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc_res = client.create_vpc(CidrBlock="10.0.0.0/24")
    subnet_res = client.create_subnet(
        VpcId=vpc_res["Vpc"]["VpcId"], CidrBlock="10.0.0.0/24"
    )
    instance = service.create_instances(
        **{
            "InstanceType": "t2.micro",
            "ImageId": EXAMPLE_AMI_ID,
            "MinCount": 1,
            "MaxCount": 1,
            "SubnetId": subnet_res["Subnet"]["SubnetId"],
        }
    )[0]
    allocation_id = client.allocate_address(Domain="vpc")["AllocationId"]
    address = service.VpcAddress(allocation_id)
    address.load()
    address.association_id.should.be.none
    address.instance_id.should.be.empty
    address.network_interface_id.should.be.empty
    client.associate_address(
        InstanceId=instance.id, AllocationId=allocation_id, AllowReassociation=False
    )
    instance.load()
    address.reload()
    address.association_id.should_not.be.none
    instance.public_ip_address.should_not.be.none
    instance.public_dns_name.should_not.be.none
    address.network_interface_id.should.equal(
        instance.network_interfaces_attribute[0].get("NetworkInterfaceId")
    )
    address.public_ip.should.equal(instance.public_ip_address)
    address.instance_id.should.equal(instance.id)

    client.disassociate_address(AssociationId=address.association_id)
    instance.reload()
    address.reload()
    instance.public_ip_address.should.be.none
    address.network_interface_id.should.be.empty
    address.association_id.should.be.none
    address.instance_id.should.be.empty


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_associate_network_interface():
    """Associate/Disassociate EIP to NIC"""
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    eni = conn.create_network_interface(subnet.id)

    eip = conn.allocate_address(domain="vpc")
    eip.network_interface_id.should.be.none

    with pytest.raises(EC2ResponseError) as cm:
        conn.associate_address(network_interface_id=eni.id)
    cm.value.code.should.equal("MissingParameter")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    conn.associate_address(network_interface_id=eni.id, allocation_id=eip.allocation_id)
    # no .update() on address ):
    eip = conn.get_all_addresses(addresses=[eip.public_ip])[0]
    eip.network_interface_id.should.be.equal(eni.id)

    conn.disassociate_address(association_id=eip.association_id)
    # no .update() on address ):
    eip = conn.get_all_addresses(addresses=[eip.public_ip])[0]
    eip.network_interface_id.should.be.equal("")
    eip.association_id.should.be.none
    eip.release()
    eip = None


@mock_ec2
def test_eip_associate_network_interface_boto3():
    """Associate/Disassociate EIP to NIC"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    eni = ec2.create_network_interface(SubnetId=subnet.id)

    eip = client.allocate_address(Domain="vpc")
    eip = ec2.ClassicAddress(eip["PublicIp"])
    eip.network_interface_id.should.be.empty

    with pytest.raises(ClientError) as ex:
        client.associate_address(NetworkInterfaceId=eni.id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("MissingParameter")
    ex.value.response["Error"]["Message"].should.equal(
        "Invalid request, expect PublicIp/AllocationId parameter."
    )

    client.associate_address(NetworkInterfaceId=eni.id, AllocationId=eip.allocation_id)

    eip.reload()
    eip.network_interface_id.should.be.equal(eni.id)

    client.disassociate_address(AssociationId=eip.association_id)

    eip.reload()
    eip.network_interface_id.should.be.empty
    eip.association_id.should.be.none
    eip.release()


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_reassociate():
    """reassociate EIP"""
    conn = boto.connect_ec2("the_key", "the_secret")

    reservation = conn.run_instances(EXAMPLE_AMI_ID, min_count=2)
    instance1, instance2 = reservation.instances

    eip = conn.allocate_address()
    conn.associate_address(instance_id=instance1.id, public_ip=eip.public_ip)

    # Same ID is idempotent
    conn.associate_address(instance_id=instance1.id, public_ip=eip.public_ip)

    # Different ID detects resource association
    with pytest.raises(EC2ResponseError) as cm:
        conn.associate_address(
            instance_id=instance2.id, public_ip=eip.public_ip, allow_reassociation=False
        )
    cm.value.code.should.equal("Resource.AlreadyAssociated")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    conn.associate_address.when.called_with(
        instance_id=instance2.id, public_ip=eip.public_ip, allow_reassociation=True
    ).should_not.throw(EC2ResponseError)

    eip.release()

    instance1.terminate()
    instance2.terminate()


@mock_ec2
def test_eip_reassociate_boto3():
    """reassociate EIP"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    instance1 = ec2.Instance(reservation["Instances"][0]["InstanceId"])
    instance2 = ec2.Instance(reservation["Instances"][1]["InstanceId"])

    eip = client.allocate_address()
    eip = ec2.ClassicAddress(eip["PublicIp"])
    client.associate_address(InstanceId=instance1.id, PublicIp=eip.public_ip)

    # Same ID is idempotent
    client.associate_address(InstanceId=instance1.id, PublicIp=eip.public_ip)

    eip.reload()
    eip.instance_id.should.equal(instance1.id)

    # Different ID detects resource association
    with pytest.raises(ClientError) as ex:
        client.associate_address(
            InstanceId=instance2.id, PublicIp=eip.public_ip, AllowReassociation=False
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("Resource.AlreadyAssociated")

    client.associate_address(
        InstanceId=instance2.id, PublicIp=eip.public_ip, AllowReassociation=True
    )

    eip.reload()
    eip.instance_id.should.equal(instance2.id)

    eip.release()
    instance1.terminate()
    instance2.terminate()


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_reassociate_nic():
    """reassociate EIP"""
    conn = boto.connect_vpc("the_key", "the_secret")

    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    eni1 = conn.create_network_interface(subnet.id)
    eni2 = conn.create_network_interface(subnet.id)

    eip = conn.allocate_address()
    conn.associate_address(network_interface_id=eni1.id, public_ip=eip.public_ip)

    # Same ID is idempotent
    conn.associate_address(network_interface_id=eni1.id, public_ip=eip.public_ip)

    # Different ID detects resource association
    with pytest.raises(EC2ResponseError) as cm:
        conn.associate_address(network_interface_id=eni2.id, public_ip=eip.public_ip)
    cm.value.code.should.equal("Resource.AlreadyAssociated")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    conn.associate_address.when.called_with(
        network_interface_id=eni2.id, public_ip=eip.public_ip, allow_reassociation=True
    ).should_not.throw(EC2ResponseError)

    eip.release()
    eip = None


@mock_ec2
def test_eip_reassociate_nic_boto3():
    """reassociate EIP"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = client.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.0.0/18")["Subnet"]
    eni1 = ec2.create_network_interface(SubnetId=subnet["SubnetId"])
    eni2 = ec2.create_network_interface(SubnetId=subnet["SubnetId"])

    eip = ec2.ClassicAddress(client.allocate_address()["PublicIp"])
    client.associate_address(NetworkInterfaceId=eni1.id, PublicIp=eip.public_ip)

    # Same ID is idempotent
    client.associate_address(NetworkInterfaceId=eni1.id, PublicIp=eip.public_ip)

    eip.reload()
    eip.network_interface_id.should.equal(eni1.id)

    # Different ID detects resource association
    with pytest.raises(ClientError) as ex:
        client.associate_address(NetworkInterfaceId=eni2.id, PublicIp=eip.public_ip)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("Resource.AlreadyAssociated")

    client.associate_address(
        NetworkInterfaceId=eni2.id, PublicIp=eip.public_ip, AllowReassociation=True
    )

    eip.reload()
    eip.network_interface_id.should.equal(eni2.id)

    eip.release()


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_associate_invalid_args():
    """Associate EIP, invalid args"""
    conn = boto.connect_ec2("the_key", "the_secret")

    reservation = conn.run_instances(EXAMPLE_AMI_ID)
    instance = reservation.instances[0]

    conn.allocate_address()

    with pytest.raises(EC2ResponseError) as cm:
        conn.associate_address(instance_id=instance.id)
    cm.value.code.should.equal("MissingParameter")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    instance.terminate()


@mock_ec2
def test_eip_associate_invalid_args_boto3():
    """Associate EIP, invalid args """
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = ec2.Instance(reservation["Instances"][0]["InstanceId"])

    client.allocate_address()

    with pytest.raises(ClientError) as ex:
        client.associate_address(InstanceId=instance.id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("MissingParameter")

    instance.terminate()


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_disassociate_bogus_association():
    """Disassociate bogus EIP"""
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.disassociate_address(association_id="bogus")
    cm.value.code.should.equal("InvalidAssociationID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_eip_disassociate_bogus_association_boto3():
    """Disassociate bogus EIP"""
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.disassociate_address(AssociationId="bogus")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("InvalidAssociationID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_release_bogus_eip():
    """Release bogus EIP"""
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.release_address(allocation_id="bogus")
    cm.value.code.should.equal("InvalidAllocationID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_eip_release_bogus_eip_boto3():
    """Release bogus EIP"""
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.release_address(AllocationId="bogus")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("InvalidAllocationID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_disassociate_arg_error():
    """Invalid arguments disassociate address"""
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.disassociate_address()
    cm.value.code.should.equal("MissingParameter")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_eip_disassociate_arg_error_boto3():
    """Invalid arguments disassociate address"""
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.disassociate_address()
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("MissingParameter")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_release_arg_error():
    """Invalid arguments release address"""
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.release_address()
    cm.value.code.should.equal("MissingParameter")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_eip_release_arg_error_boto3():
    """Invalid arguments release address"""
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.release_address()
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("MissingParameter")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_describe():
    """Listing of allocated Elastic IP Addresses."""
    conn = boto.connect_ec2("the_key", "the_secret")
    eips = []
    number_of_classic_ips = 2
    number_of_vpc_ips = 2

    # allocate some IPs
    for _ in range(number_of_classic_ips):
        eips.append(conn.allocate_address())
    for _ in range(number_of_vpc_ips):
        eips.append(conn.allocate_address(domain="vpc"))
    len(eips).should.be.equal(number_of_classic_ips + number_of_vpc_ips)

    # Can we find each one individually?
    for eip in eips:
        if eip.allocation_id:
            lookup_addresses = conn.get_all_addresses(
                allocation_ids=[eip.allocation_id]
            )
        else:
            lookup_addresses = conn.get_all_addresses(addresses=[eip.public_ip])
        len(lookup_addresses).should.be.equal(1)
        lookup_addresses[0].public_ip.should.be.equal(eip.public_ip)

    # Can we find first two when we search for them?
    lookup_addresses = conn.get_all_addresses(
        addresses=[eips[0].public_ip, eips[1].public_ip]
    )
    len(lookup_addresses).should.be.equal(2)
    lookup_addresses[0].public_ip.should.be.equal(eips[0].public_ip)
    lookup_addresses[1].public_ip.should.be.equal(eips[1].public_ip)

    # Release all IPs
    for eip in eips:
        eip.release()
    len(conn.get_all_addresses()).should.be.equal(0)


@mock_ec2
def test_eip_describe_boto3():
    """Listing of allocated Elastic IP Addresses."""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    eips = []
    number_of_classic_ips = 2
    number_of_vpc_ips = 2

    # allocate some IPs
    for _ in range(number_of_classic_ips):
        eips.append(ec2.ClassicAddress(client.allocate_address()["PublicIp"]))
    for _ in range(number_of_vpc_ips):
        eip_id = client.allocate_address(Domain="vpc")["AllocationId"]
        eips.append(ec2.VpcAddress(eip_id))
    eips.should.have.length_of(number_of_classic_ips + number_of_vpc_ips)

    # Can we find each one individually?
    for eip in eips:
        if eip.allocation_id:
            lookup_addresses = client.describe_addresses(
                AllocationIds=[eip.allocation_id]
            )["Addresses"]
        else:
            lookup_addresses = client.describe_addresses(PublicIps=[eip.public_ip])[
                "Addresses"
            ]
        len(lookup_addresses).should.be.equal(1)
        lookup_addresses[0]["PublicIp"].should.be.equal(eip.public_ip)

    # Can we find first two when we search for them?
    lookup_addresses = client.describe_addresses(
        PublicIps=[eips[0].public_ip, eips[1].public_ip]
    )["Addresses"]
    lookup_addresses.should.have.length_of(2)
    lookup_addresses[0]["PublicIp"].should.be.equal(eips[0].public_ip)
    lookup_addresses[1]["PublicIp"].should.be.equal(eips[1].public_ip)

    # Release all IPs
    for eip in eips:
        eip.release()
    all_addresses = client.describe_addresses()["Addresses"]
    [a["PublicIp"] for a in all_addresses].shouldnt.contain(eips[0].public_ip)
    [a["PublicIp"] for a in all_addresses].shouldnt.contain(eips[1].public_ip)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_eip_describe_none():
    """Error when search for bogus IP"""
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_addresses(addresses=["256.256.256.256"])
    cm.value.code.should.equal("InvalidAddress.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_eip_describe_none_boto3():
    """Error when search for bogus IP"""
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_addresses(PublicIps=["256.256.256.256"])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"]["RequestId"].shouldnt.be.none
    ex.value.response["Error"]["Code"].should.equal("InvalidAddress.NotFound")


@mock_ec2
def test_eip_filters():
    service = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc_res = client.create_vpc(CidrBlock="10.0.0.0/24")
    subnet_res = client.create_subnet(
        VpcId=vpc_res["Vpc"]["VpcId"], CidrBlock="10.0.0.0/24"
    )

    def create_inst_with_eip():
        instance = service.create_instances(
            **{
                "InstanceType": "t2.micro",
                "ImageId": EXAMPLE_AMI_ID,
                "MinCount": 1,
                "MaxCount": 1,
                "SubnetId": subnet_res["Subnet"]["SubnetId"],
            }
        )[0]
        allocation_id = client.allocate_address(Domain="vpc")["AllocationId"]
        _ = client.associate_address(
            InstanceId=instance.id, AllocationId=allocation_id, AllowReassociation=False
        )
        instance.load()
        address = service.VpcAddress(allocation_id)
        address.load()
        return instance, address

    inst1, eip1 = create_inst_with_eip()
    inst2, eip2 = create_inst_with_eip()
    inst3, eip3 = create_inst_with_eip()

    # Param search by AllocationId
    addresses = list(service.vpc_addresses.filter(AllocationIds=[eip2.allocation_id]))
    len(addresses).should.be.equal(1)
    addresses[0].public_ip.should.equal(eip2.public_ip)
    inst2.public_ip_address.should.equal(addresses[0].public_ip)

    # Param search by PublicIp
    addresses = list(service.vpc_addresses.filter(PublicIps=[eip3.public_ip]))
    len(addresses).should.be.equal(1)
    addresses[0].public_ip.should.equal(eip3.public_ip)
    inst3.public_ip_address.should.equal(addresses[0].public_ip)

    # Param search by Filter
    def check_vpc_filter_valid(filter_name, filter_values, all_values=True):
        addresses = list(
            service.vpc_addresses.filter(
                Filters=[{"Name": filter_name, "Values": filter_values}]
            )
        )
        if all_values:
            len(addresses).should.equal(2)
            ips = [addr.public_ip for addr in addresses]
            set(ips).should.equal(set([eip1.public_ip, eip2.public_ip]))
            ips.should.contain(inst1.public_ip_address)
        else:
            ips = [addr.public_ip for addr in addresses]
            ips.should.contain(eip1.public_ip)
            ips.should.contain(eip2.public_ip)

    def check_vpc_filter_invalid(filter_name):
        addresses = list(
            service.vpc_addresses.filter(
                Filters=[{"Name": filter_name, "Values": ["dummy1", "dummy2"]}]
            )
        )
        len(addresses).should.equal(0)

    def check_vpc_filter(filter_name, filter_values, all_values=True):
        check_vpc_filter_valid(filter_name, filter_values, all_values)
        check_vpc_filter_invalid(filter_name)

    check_vpc_filter("allocation-id", [eip1.allocation_id, eip2.allocation_id])
    check_vpc_filter("association-id", [eip1.association_id, eip2.association_id])
    check_vpc_filter("instance-id", [inst1.id, inst2.id])
    check_vpc_filter(
        "network-interface-id",
        [
            inst1.network_interfaces_attribute[0].get("NetworkInterfaceId"),
            inst2.network_interfaces_attribute[0].get("NetworkInterfaceId"),
        ],
    )
    check_vpc_filter(
        "private-ip-address",
        [
            inst1.network_interfaces_attribute[0].get("PrivateIpAddress"),
            inst2.network_interfaces_attribute[0].get("PrivateIpAddress"),
        ],
        all_values=False,  # Other ENI's may have the same ip address
    )
    check_vpc_filter("public-ip", [inst1.public_ip_address, inst2.public_ip_address])

    # all the ips are in a VPC
    addresses = list(
        service.vpc_addresses.filter(Filters=[{"Name": "domain", "Values": ["vpc"]}])
    )
    public_ips = [a.public_ip for a in addresses]
    public_ips.should.contain(eip1.public_ip)
    public_ips.should.contain(eip1.public_ip)
    public_ips.should.contain(inst1.public_ip_address)


@mock_ec2
def test_eip_tags():
    service = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    # Allocate one address without tags
    no_tags = client.allocate_address(Domain="vpc")

    # Allocate one address and add tags
    alloc_tags = client.allocate_address(Domain="vpc")
    managed_by = str(uuid4())
    client.create_tags(
        Resources=[alloc_tags["AllocationId"]],
        Tags=[{"Key": "ManagedBy", "Value": managed_by}],
    )
    addresses_with_tags = client.describe_addresses(
        Filters=[
            {"Name": "domain", "Values": ["vpc"]},
            {"Name": "tag:ManagedBy", "Values": [managed_by]},
        ]
    )
    len(addresses_with_tags["Addresses"]).should.equal(1)
    addresses_with_tags = list(
        service.vpc_addresses.filter(
            Filters=[
                {"Name": "domain", "Values": ["vpc"]},
                {"Name": "tag:ManagedBy", "Values": [managed_by]},
            ]
        )
    )
    len(addresses_with_tags).should.equal(1)
    addresses_with_tags = list(
        service.vpc_addresses.filter(
            Filters=[
                {"Name": "domain", "Values": ["vpc"]},
                {"Name": "tag:ManagedBy", "Values": ["SomethingOther"]},
            ]
        )
    )
    len(addresses_with_tags).should.equal(0)
    addresses = list(
        service.vpc_addresses.filter(Filters=[{"Name": "domain", "Values": ["vpc"]}])
    )
    # Expected at least 2, one with and one without tags
    assert len(addresses) >= 2, "Should find our two created addresses"
    [a.allocation_id for a in addresses].should.contain(no_tags["AllocationId"])
    [a.allocation_id for a in addresses].should.contain(alloc_tags["AllocationId"])


@mock_ec2
def test_describe_addresses_tags():
    client = boto3.client("ec2", region_name="us-west-1")

    alloc_tags = client.allocate_address(Domain="vpc")
    client.create_tags(
        Resources=[alloc_tags["AllocationId"]],
        Tags=[{"Key": "ManagedBy", "Value": "MyCode"}],
    )

    addresses_with_tags = client.describe_addresses(
        AllocationIds=[alloc_tags["AllocationId"]]
    )
    assert addresses_with_tags.get("Addresses")[0].get("Tags") == [
        {"Key": "ManagedBy", "Value": "MyCode"}
    ]
