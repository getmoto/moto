import pytest

import boto3
from botocore.exceptions import ClientError
from uuid import uuid4

from moto import mock_ec2
from tests import EXAMPLE_AMI_ID


@mock_ec2
def test_eip_allocate_classic():
    """Allocate/release Classic EIP"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.allocate_address(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the AllocateAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    standard = client.allocate_address(Domain="standard")
    assert "PublicIp" in standard
    assert standard["Domain"] == "standard"

    public_ip = standard["PublicIp"]

    standard = ec2.ClassicAddress(public_ip)
    standard.load()

    with pytest.raises(ClientError) as ex:
        standard.release(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the ReleaseAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    standard.release()

    all_addresses = client.describe_addresses()["Addresses"]
    assert public_ip not in [a["PublicIp"] for a in all_addresses]


@mock_ec2
def test_describe_addresses_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_addresses(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DescribeAddresses operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
def test_eip_allocate_vpc():
    """Allocate/release VPC EIP"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.allocate_address(Domain="vpc", DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the AllocateAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    vpc = client.allocate_address(Domain="vpc")
    assert "AllocationId" in vpc
    assert vpc["Domain"] == "vpc"

    # Ensure that correct fallback is used for the optional attribute `Domain` contains an empty or invalid value
    vpc2 = client.allocate_address(Domain="")
    vpc3 = client.allocate_address(Domain="xyz")

    assert vpc2["Domain"] == "vpc"
    assert vpc3["Domain"] == "vpc"

    allocation_id = vpc["AllocationId"]
    allocation_id2 = vpc["AllocationId"]
    allocation_id3 = vpc["AllocationId"]

    all_addresses = client.describe_addresses()["Addresses"]
    allocation_ids = [a["AllocationId"] for a in all_addresses if "AllocationId" in a]
    assert allocation_id in allocation_ids
    assert allocation_id2 in allocation_ids
    assert allocation_id3 in allocation_ids

    vpc = ec2.VpcAddress(allocation_id)
    vpc.release()

    all_addresses = client.describe_addresses()["Addresses"]
    assert allocation_id not in [
        a["AllocationId"] for a in all_addresses if "AllocationId" in a
    ]


@mock_ec2
def test_specific_eip_allocate_vpc():
    """Allocate VPC EIP with specific address"""
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = client.allocate_address(Domain="vpc", Address="127.38.43.222")
    assert vpc["Domain"] == "vpc"
    assert vpc["PublicIp"] == "127.38.43.222"


@mock_ec2
def test_eip_associate_classic():
    """Associate/Disassociate EIP to classic instance"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = ec2.Instance(reservation["Instances"][0]["InstanceId"])

    eip = client.allocate_address()
    eip = ec2.ClassicAddress(eip["PublicIp"])
    assert eip.instance_id == ""

    with pytest.raises(ClientError) as ex:
        client.associate_address(PublicIp=eip.public_ip)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "MissingParameter"
    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid request, expect InstanceId/NetworkId parameter."
    )

    with pytest.raises(ClientError) as ex:
        client.associate_address(
            InstanceId=instance.id, PublicIp=eip.public_ip, DryRun=True
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the AssociateAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    client.associate_address(InstanceId=instance.id, PublicIp=eip.public_ip)
    eip.reload()
    assert eip.instance_id == instance.id

    with pytest.raises(ClientError) as ex:
        client.disassociate_address(PublicIp=eip.public_ip, DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DisassociateAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    client.disassociate_address(PublicIp=eip.public_ip)
    eip.reload()
    assert eip.instance_id == ""
    eip.release()

    with pytest.raises(ClientError) as ex:
        client.describe_addresses(PublicIps=[eip.public_ip])
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidAddress.NotFound"
    assert err["Message"] == "Address '{'" + eip.public_ip + "'}' not found."

    instance.terminate()


@mock_ec2
def test_eip_associate_vpc():
    """Associate/Disassociate EIP to VPC instance"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = ec2.Instance(reservation["Instances"][0]["InstanceId"])

    eip = client.allocate_address(Domain="vpc")
    assert "InstanceId" not in eip
    eip = ec2.VpcAddress(eip["AllocationId"])

    with pytest.raises(ClientError) as ex:
        client.associate_address(AllocationId=eip.allocation_id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "MissingParameter"
    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid request, expect InstanceId/NetworkId parameter."
    )

    client.associate_address(InstanceId=instance.id, AllocationId=eip.allocation_id)

    eip.reload()
    assert eip.instance_id == instance.id
    client.disassociate_address(AssociationId=eip.association_id)

    eip.reload()
    assert eip.instance_id == ""
    assert eip.association_id is None

    with pytest.raises(ClientError) as ex:
        eip.release(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the ReleaseAddress operation: Request would have succeeded, but DryRun flag is set"
    )

    eip.release()
    instance.terminate()


@mock_ec2
def test_eip_vpc_association():
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
    assert address.association_id is None
    assert address.instance_id == ""
    assert address.network_interface_id == ""
    client.associate_address(
        InstanceId=instance.id, AllocationId=allocation_id, AllowReassociation=False
    )
    instance.load()
    address.reload()
    assert address.association_id is not None
    assert instance.public_ip_address is not None
    assert instance.public_dns_name is not None
    assert address.network_interface_id == instance.network_interfaces_attribute[0].get(
        "NetworkInterfaceId"
    )
    assert address.public_ip == instance.public_ip_address
    assert address.instance_id == instance.id

    client.disassociate_address(AssociationId=address.association_id)
    instance.reload()
    address.reload()
    assert instance.public_ip_address is None
    assert address.network_interface_id == ""
    assert address.association_id is None
    assert address.instance_id == ""


@mock_ec2
def test_eip_associate_network_interface():
    """Associate/Disassociate EIP to NIC"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    eni = ec2.create_network_interface(SubnetId=subnet.id)

    eip = client.allocate_address(Domain="vpc")
    eip = ec2.ClassicAddress(eip["PublicIp"])
    assert eip.network_interface_id == ""

    with pytest.raises(ClientError) as ex:
        client.associate_address(NetworkInterfaceId=eni.id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "MissingParameter"
    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid request, expect PublicIp/AllocationId parameter."
    )

    client.associate_address(NetworkInterfaceId=eni.id, AllocationId=eip.allocation_id)

    eip.reload()
    assert eip.network_interface_id == eni.id

    client.disassociate_address(AssociationId=eip.association_id)

    eip.reload()
    assert eip.network_interface_id == ""
    assert eip.association_id is None
    eip.release()


@mock_ec2
def test_eip_reassociate():
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
    assert eip.instance_id == instance1.id

    # Different ID detects resource association
    with pytest.raises(ClientError) as ex:
        client.associate_address(
            InstanceId=instance2.id, PublicIp=eip.public_ip, AllowReassociation=False
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "Resource.AlreadyAssociated"

    client.associate_address(
        InstanceId=instance2.id, PublicIp=eip.public_ip, AllowReassociation=True
    )

    eip.reload()
    assert eip.instance_id == instance2.id

    eip.release()
    instance1.terminate()
    instance2.terminate()


@mock_ec2
def test_eip_reassociate_nic():
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
    assert eip.network_interface_id == eni1.id

    # Different ID detects resource association
    with pytest.raises(ClientError) as ex:
        client.associate_address(NetworkInterfaceId=eni2.id, PublicIp=eip.public_ip)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "Resource.AlreadyAssociated"

    client.associate_address(
        NetworkInterfaceId=eni2.id, PublicIp=eip.public_ip, AllowReassociation=True
    )

    eip.reload()
    assert eip.network_interface_id == eni2.id

    eip.release()


@mock_ec2
def test_eip_associate_invalid_args():
    """Associate EIP, invalid args"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = ec2.Instance(reservation["Instances"][0]["InstanceId"])

    client.allocate_address()

    with pytest.raises(ClientError) as ex:
        client.associate_address(InstanceId=instance.id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "MissingParameter"

    instance.terminate()


@mock_ec2
def test_eip_disassociate_bogus_association():
    """Disassociate bogus EIP"""
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.disassociate_address(AssociationId="bogus")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "InvalidAssociationID.NotFound"


@mock_ec2
def test_eip_release_bogus_eip():
    """Release bogus EIP"""
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.release_address(AllocationId="bogus")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "InvalidAllocationID.NotFound"


@mock_ec2
def test_eip_disassociate_arg_error():
    """Invalid arguments disassociate address"""
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.disassociate_address()
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "MissingParameter"


@mock_ec2
def test_eip_release_arg_error():
    """Invalid arguments release address"""
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.release_address()
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "MissingParameter"


@mock_ec2
def test_eip_describe():
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
    assert len(eips) == number_of_classic_ips + number_of_vpc_ips

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
        assert len(lookup_addresses) == 1
        assert lookup_addresses[0]["PublicIp"] == eip.public_ip

    # Can we find first two when we search for them?
    lookup_addresses = client.describe_addresses(
        PublicIps=[eips[0].public_ip, eips[1].public_ip]
    )["Addresses"]
    assert len(lookup_addresses) == 2
    assert lookup_addresses[0]["PublicIp"] == eips[0].public_ip
    assert lookup_addresses[1]["PublicIp"] == eips[1].public_ip

    # Release all IPs
    for eip in eips:
        eip.release()
    all_addresses = client.describe_addresses()["Addresses"]
    assert eips[0].public_ip not in [a["PublicIp"] for a in all_addresses]
    assert eips[1].public_ip not in [a["PublicIp"] for a in all_addresses]


@mock_ec2
def test_eip_describe_none():
    """Error when search for bogus IP"""
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_addresses(PublicIps=["256.256.256.256"])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["ResponseMetadata"]["RequestId"] is not None
    assert ex.value.response["Error"]["Code"] == "InvalidAddress.NotFound"


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
    assert len(addresses) == 1
    assert addresses[0].public_ip == eip2.public_ip
    assert inst2.public_ip_address == addresses[0].public_ip

    # Param search by PublicIp
    addresses = list(service.vpc_addresses.filter(PublicIps=[eip3.public_ip]))
    assert len(addresses) == 1
    assert addresses[0].public_ip == eip3.public_ip
    assert inst3.public_ip_address == addresses[0].public_ip

    # Param search by Filter
    def check_vpc_filter_valid(filter_name, filter_values, all_values=True):
        addresses = list(
            service.vpc_addresses.filter(
                Filters=[{"Name": filter_name, "Values": filter_values}]
            )
        )
        if all_values:
            assert len(addresses) == 2
            ips = [addr.public_ip for addr in addresses]
            assert set(ips) == set([eip1.public_ip, eip2.public_ip])
            assert inst1.public_ip_address in ips
        else:
            ips = [addr.public_ip for addr in addresses]
            assert eip1.public_ip in ips
            assert eip2.public_ip in ips

    def check_vpc_filter_invalid(filter_name):
        addresses = list(
            service.vpc_addresses.filter(
                Filters=[{"Name": filter_name, "Values": ["dummy1", "dummy2"]}]
            )
        )
        assert len(addresses) == 0

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
    assert eip1.public_ip in public_ips
    assert eip1.public_ip in public_ips
    assert inst1.public_ip_address in public_ips


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
    assert len(addresses_with_tags["Addresses"]) == 1
    addresses_with_tags = list(
        service.vpc_addresses.filter(
            Filters=[
                {"Name": "domain", "Values": ["vpc"]},
                {"Name": "tag:ManagedBy", "Values": [managed_by]},
            ]
        )
    )
    assert len(addresses_with_tags) == 1
    addresses_with_tags = list(
        service.vpc_addresses.filter(
            Filters=[
                {"Name": "domain", "Values": ["vpc"]},
                {"Name": "tag:ManagedBy", "Values": ["SomethingOther"]},
            ]
        )
    )
    assert len(addresses_with_tags) == 0
    addresses = list(
        service.vpc_addresses.filter(Filters=[{"Name": "domain", "Values": ["vpc"]}])
    )
    # Expected at least 2, one with and one without tags
    assert len(addresses) >= 2, "Should find our two created addresses"
    assert no_tags["AllocationId"] in [a.allocation_id for a in addresses]
    assert alloc_tags["AllocationId"] in [a.allocation_id for a in addresses]


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


@mock_ec2
def test_describe_addresses_with_vpc_associated_eni():
    """Extra attributes for EIP associated with a ENI inside a VPC"""
    client = boto3.client("ec2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")
    eni = ec2.create_network_interface(SubnetId=subnet.id)

    eip = client.allocate_address(Domain="vpc")
    association_id = client.associate_address(
        NetworkInterfaceId=eni.id, PublicIp=eip["PublicIp"]
    )["AssociationId"]

    result = client.describe_addresses(
        Filters=[{"Name": "association-id", "Values": [association_id]}]
    )

    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(result["Addresses"]) == 1

    address = result["Addresses"][0]

    assert address["NetworkInterfaceId"] == eni.id
    assert address["PrivateIpAddress"] == eni.private_ip_address
    assert address["AssociationId"] == association_id
    assert address["NetworkInterfaceOwnerId"] == eni.owner_id
