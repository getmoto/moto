import random
import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_ec2, settings
from tests import EXAMPLE_AMI_ID
from uuid import uuid4
from unittest import SkipTest


@mock_ec2
def test_subnets():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    ours = client.describe_subnets(SubnetIds=[subnet.id])["Subnets"]
    assert len(ours) == 1

    client.delete_subnet(SubnetId=subnet.id)

    with pytest.raises(ClientError) as ex:
        client.describe_subnets(SubnetIds=[subnet.id])
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidSubnetID.NotFound"

    with pytest.raises(ClientError) as ex:
        client.delete_subnet(SubnetId=subnet.id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidSubnetID.NotFound"


@mock_ec2
def test_subnet_create_vpc_validation():
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        ec2.create_subnet(VpcId="vpc-abcd1234", CidrBlock="10.0.0.0/18")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidVpcID.NotFound"


@mock_ec2
def test_subnet_tagging():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    subnet.create_tags(Tags=[{"Key": "a key", "Value": "some value"}])

    tag = client.describe_tags(
        Filters=[{"Name": "resource-id", "Values": [subnet.id]}]
    )["Tags"][0]
    assert tag["Key"] == "a key"
    assert tag["Value"] == "some value"

    # Refresh the subnet
    subnet = client.describe_subnets(SubnetIds=[subnet.id])["Subnets"][0]
    assert subnet["Tags"] == [{"Key": "a key", "Value": "some value"}]


@mock_ec2
def test_subnet_should_have_proper_availability_zone_set():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    vpcA = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnetA = ec2.create_subnet(
        VpcId=vpcA.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1b"
    )
    assert subnetA.availability_zone == "us-west-1b"


@mock_ec2
def test_availability_zone_in_create_subnet():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="172.31.0.0/16")

    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.31.48.0/20", AvailabilityZoneId="use1-az6"
    )
    assert subnet.availability_zone_id == "use1-az6"


@mock_ec2
def test_default_subnet():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode will have conflicting CidrBlocks")
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    default_vpc = list(ec2.vpcs.all())[0]
    assert default_vpc.cidr_block == "172.31.0.0/16"
    default_vpc.reload()
    assert default_vpc.is_default is True

    subnet = ec2.create_subnet(
        VpcId=default_vpc.id, CidrBlock="172.31.48.0/20", AvailabilityZone="us-west-1a"
    )
    subnet.reload()
    assert subnet.map_public_ip_on_launch is False


@mock_ec2
def test_non_default_subnet():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create the non default VPC
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.reload()
    assert vpc.is_default is False

    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )
    subnet.reload()
    assert subnet.map_public_ip_on_launch is False


@mock_ec2
def test_modify_subnet_attribute_public_ip_on_launch():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    random_ip = ".".join(map(str, (random.randint(0, 99) for _ in range(4))))
    vpc = ec2.create_vpc(CidrBlock=f"{random_ip}/16")

    random_subnet_cidr = f"{random_ip}/20"  # Same block as the VPC

    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock=random_subnet_cidr, AvailabilityZone="us-west-1a"
    )

    # 'map_public_ip_on_launch' is set when calling 'DescribeSubnets' action
    subnet.reload()

    # For non default subnet, attribute value should be 'False'
    assert subnet.map_public_ip_on_launch is False

    client.modify_subnet_attribute(
        SubnetId=subnet.id, MapPublicIpOnLaunch={"Value": False}
    )
    subnet.reload()
    assert subnet.map_public_ip_on_launch is False

    client.modify_subnet_attribute(
        SubnetId=subnet.id, MapPublicIpOnLaunch={"Value": True}
    )
    subnet.reload()
    assert subnet.map_public_ip_on_launch is True


@mock_ec2
def test_modify_subnet_attribute_assign_ipv6_address_on_creation():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    random_ip = ".".join(map(str, (random.randint(0, 99) for _ in range(4))))
    vpc = ec2.create_vpc(CidrBlock=f"{random_ip}/16")

    random_subnet_cidr = f"{random_ip}/20"  # Same block as the VPC

    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock=random_subnet_cidr, AvailabilityZone="us-west-1a"
    )

    # 'map_public_ip_on_launch' is set when calling 'DescribeSubnets' action
    subnet.reload()
    client.describe_subnets()

    # For non default subnet, attribute value should be 'False'
    assert subnet.assign_ipv6_address_on_creation is False

    client.modify_subnet_attribute(
        SubnetId=subnet.id, AssignIpv6AddressOnCreation={"Value": False}
    )
    subnet.reload()
    assert subnet.assign_ipv6_address_on_creation is False

    client.modify_subnet_attribute(
        SubnetId=subnet.id, AssignIpv6AddressOnCreation={"Value": True}
    )
    subnet.reload()
    assert subnet.assign_ipv6_address_on_creation is True


@mock_ec2
def test_modify_subnet_attribute_validation():
    # TODO: implement some actual logic
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )


@mock_ec2
def test_subnet_get_by_id():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpcA = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnetA = ec2.create_subnet(
        VpcId=vpcA.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )
    vpcB = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnetB1 = ec2.create_subnet(
        VpcId=vpcB.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )
    ec2.create_subnet(
        VpcId=vpcB.id, CidrBlock="10.0.1.0/24", AvailabilityZone="us-west-1b"
    )

    subnets_by_id = client.describe_subnets(SubnetIds=[subnetA.id, subnetB1.id])[
        "Subnets"
    ]
    assert len(subnets_by_id) == 2
    subnets_by_id = tuple(map(lambda s: s["SubnetId"], subnets_by_id))
    assert subnetA.id in subnets_by_id
    assert subnetB1.id in subnets_by_id

    with pytest.raises(ClientError) as ex:
        client.describe_subnets(SubnetIds=["subnet-does_not_exist"])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidSubnetID.NotFound"


@mock_ec2
def test_get_subnets_filtering():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpcA = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnetA = ec2.create_subnet(
        VpcId=vpcA.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )
    vpcB = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnetB1 = ec2.create_subnet(
        VpcId=vpcB.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )
    subnetB2 = ec2.create_subnet(
        VpcId=vpcB.id, CidrBlock="10.0.1.0/24", AvailabilityZone="us-west-1b"
    )

    nr_of_a_zones = len(client.describe_availability_zones()["AvailabilityZones"])
    all_subnets = client.describe_subnets()["Subnets"]
    if settings.TEST_SERVER_MODE:
        # ServerMode may have other tests running that are creating subnets
        all_subnet_ids = [s["SubnetId"] for s in all_subnets]
        assert subnetA.id in all_subnet_ids
        assert subnetB1.id in all_subnet_ids
        assert subnetB2.id in all_subnet_ids
    else:
        assert len(all_subnets) == 3 + nr_of_a_zones

    # Filter by VPC ID
    subnets_by_vpc = client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpcB.id]}]
    )["Subnets"]
    assert len(subnets_by_vpc) == 2
    assert set([subnet["SubnetId"] for subnet in subnets_by_vpc]) == {
        subnetB1.id,
        subnetB2.id,
    }

    # Filter by CIDR variations
    subnets_by_cidr1 = client.describe_subnets(
        Filters=[{"Name": "cidr", "Values": ["10.0.0.0/24"]}]
    )["Subnets"]
    subnets_by_cidr1 = [s["SubnetId"] for s in subnets_by_cidr1]
    assert subnetA.id in subnets_by_cidr1
    assert subnetB1.id in subnets_by_cidr1
    assert subnetB2.id not in subnets_by_cidr1

    subnets_by_cidr2 = client.describe_subnets(
        Filters=[{"Name": "cidr-block", "Values": ["10.0.0.0/24"]}]
    )["Subnets"]
    subnets_by_cidr2 = [s["SubnetId"] for s in subnets_by_cidr2]
    assert subnetA.id in subnets_by_cidr2
    assert subnetB1.id in subnets_by_cidr2
    assert subnetB2.id not in subnets_by_cidr2

    subnets_by_cidr3 = client.describe_subnets(
        Filters=[{"Name": "cidrBlock", "Values": ["10.0.0.0/24"]}]
    )["Subnets"]
    subnets_by_cidr3 = [s["SubnetId"] for s in subnets_by_cidr3]
    assert subnetA.id in subnets_by_cidr3
    assert subnetB1.id in subnets_by_cidr3
    assert subnetB2.id not in subnets_by_cidr3

    # Filter by VPC ID and CIDR
    subnets_by_vpc_and_cidr = client.describe_subnets(
        Filters=[
            {"Name": "vpc-id", "Values": [vpcB.id]},
            {"Name": "cidr", "Values": ["10.0.0.0/24"]},
        ]
    )["Subnets"]
    assert len(subnets_by_vpc_and_cidr) == 1
    assert subnets_by_vpc_and_cidr[0]["SubnetId"] == subnetB1.id

    # Filter by subnet ID
    subnets_by_id = client.describe_subnets(
        Filters=[{"Name": "subnet-id", "Values": [subnetA.id]}]
    )["Subnets"]
    assert len(subnets_by_id) == 1
    assert subnets_by_id[0]["SubnetId"] == subnetA.id

    # Filter by availabilityZone
    subnets_by_az = client.describe_subnets(
        Filters=[
            {"Name": "availabilityZone", "Values": ["us-west-1a"]},
            {"Name": "vpc-id", "Values": [vpcB.id]},
        ]
    )["Subnets"]
    assert len(subnets_by_az) == 1
    assert subnets_by_az[0]["SubnetId"] == subnetB1.id

    if not settings.TEST_SERVER_MODE:
        # Filter by defaultForAz
        subnets_by_az = client.describe_subnets(
            Filters=[{"Name": "defaultForAz", "Values": ["true"]}]
        )["Subnets"]
        assert len(subnets_by_az) == nr_of_a_zones

        # Unsupported filter
        filters = [{"Name": "not-implemented-filter", "Values": ["foobar"]}]
        with pytest.raises(NotImplementedError):
            client.describe_subnets(Filters=filters)


@mock_ec2
def test_create_subnet_response_fields():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = client.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )["Subnet"]

    assert "AvailabilityZone" in subnet
    assert "AvailabilityZoneId" in subnet
    assert "AvailableIpAddressCount" in subnet
    assert "CidrBlock" in subnet
    assert "State" in subnet
    assert "SubnetId" in subnet
    assert "VpcId" in subnet
    assert "Tags" in subnet
    assert subnet["DefaultForAz"] is False
    assert subnet["MapPublicIpOnLaunch"] is False
    assert "OwnerId" in subnet
    assert subnet["AssignIpv6AddressOnCreation"] is False
    assert subnet["Ipv6Native"] is False

    subnet_arn = f"arn:aws:ec2:{subnet['AvailabilityZone'][0:-1]}:{subnet['OwnerId']}:subnet/{subnet['SubnetId']}"
    assert subnet["SubnetArn"] == subnet_arn
    assert subnet["Ipv6CidrBlockAssociationSet"] == []


@mock_ec2
def test_describe_subnet_response_fields():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet_object = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )

    subnets = client.describe_subnets(SubnetIds=[subnet_object.id])["Subnets"]
    assert len(subnets) == 1
    subnet = subnets[0]

    assert "AvailabilityZone" in subnet
    assert "AvailabilityZoneId" in subnet
    assert "AvailableIpAddressCount" in subnet
    assert "CidrBlock" in subnet
    assert "State" in subnet
    assert "SubnetId" in subnet
    assert "VpcId" in subnet
    assert "Tags" not in subnet
    assert subnet["DefaultForAz"] is False
    assert subnet["MapPublicIpOnLaunch"] is False
    assert "OwnerId" in subnet
    assert subnet["AssignIpv6AddressOnCreation"] is False
    assert subnet["Ipv6Native"] is False

    subnet_arn = f"arn:aws:ec2:{subnet['AvailabilityZone'][0:-1]}:{subnet['OwnerId']}:subnet/{subnet['SubnetId']}"
    assert subnet["SubnetArn"] == subnet_arn
    assert subnet["Ipv6CidrBlockAssociationSet"] == []


@mock_ec2
def test_create_subnet_with_invalid_availability_zone():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    subnet_availability_zone = "asfasfas"
    with pytest.raises(ClientError) as ex:
        client.create_subnet(
            VpcId=vpc.id,
            CidrBlock="10.0.0.0/24",
            AvailabilityZone=subnet_availability_zone,
        )
    assert str(ex.value).startswith(
        "An error occurred (InvalidParameterValue) when calling the CreateSubnet "
        f"operation: Value ({subnet_availability_zone}) for parameter availabilityZone is invalid. Subnets can currently only be created in the following availability zones: "
    )


@mock_ec2
def test_create_subnet_with_invalid_cidr_range():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.reload()
    assert vpc.is_default is False

    subnet_cidr_block = "10.1.0.0/20"
    with pytest.raises(ClientError) as ex:
        ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
    assert (
        str(ex.value)
        == f"An error occurred (InvalidSubnet.Range) when calling the CreateSubnet operation: The CIDR '{subnet_cidr_block}' is invalid."
    )


@mock_ec2
def test_create_subnet_with_invalid_cidr_range_multiple_vpc_cidr_blocks():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.meta.client.associate_vpc_cidr_block(CidrBlock="10.1.0.0/16", VpcId=vpc.id)
    vpc.reload()
    assert vpc.is_default is False

    subnet_cidr_block = "10.2.0.0/20"
    with pytest.raises(ClientError) as ex:
        ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
    assert (
        str(ex.value)
        == f"An error occurred (InvalidSubnet.Range) when calling the CreateSubnet operation: The CIDR '{subnet_cidr_block}' is invalid."
    )


@mock_ec2
def test_create_subnet_with_invalid_cidr_block_parameter():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.reload()
    assert vpc.is_default is False

    subnet_cidr_block = "1000.1.0.0/20"
    with pytest.raises(ClientError) as ex:
        ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
    assert (
        str(ex.value)
        == f"An error occurred (InvalidParameterValue) when calling the CreateSubnet operation: Value ({subnet_cidr_block}) for parameter cidrBlock is invalid. This is not a valid CIDR block."
    )


@mock_ec2
def test_create_subnets_with_multiple_vpc_cidr_blocks():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.meta.client.associate_vpc_cidr_block(CidrBlock="10.1.0.0/16", VpcId=vpc.id)
    vpc.reload()
    assert vpc.is_default is False

    subnet_cidr_block_primary = "10.0.0.0/24"
    subnet_primary = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock=subnet_cidr_block_primary
    )

    subnet_cidr_block_secondary = "10.1.0.0/24"
    subnet_secondary = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock=subnet_cidr_block_secondary
    )

    subnets = client.describe_subnets(
        SubnetIds=[subnet_primary.id, subnet_secondary.id]
    )["Subnets"]
    assert len(subnets) == 2

    for subnet in subnets:
        assert "AvailabilityZone" in subnet
        assert "AvailabilityZoneId" in subnet
        assert "AvailableIpAddressCount" in subnet
        assert "CidrBlock" in subnet
        assert "State" in subnet
        assert "SubnetId" in subnet
        assert "VpcId" in subnet
        assert "Tags" not in subnet
        assert subnet["DefaultForAz"] is False
        assert subnet["MapPublicIpOnLaunch"] is False
        assert "OwnerId" in subnet
        assert subnet["AssignIpv6AddressOnCreation"] is False


@mock_ec2
def test_create_subnets_with_overlapping_cidr_blocks():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.reload()
    assert vpc.is_default is False

    subnet_cidr_block = "10.0.0.0/24"
    with pytest.raises(ClientError) as ex:
        ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
        ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
    assert (
        str(ex.value)
        == f"An error occurred (InvalidSubnet.Conflict) when calling the CreateSubnet operation: The CIDR '{subnet_cidr_block}' conflicts with another subnet"
    )


@mock_ec2
def test_create_subnet_with_tags():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="172.31.0.0/16")

    random_ip = "172.31." + ".".join(
        map(str, (random.randint(10, 40) for _ in range(2)))
    )
    random_cidr = f"{random_ip}/20"

    subnet = ec2.create_subnet(
        VpcId=vpc.id,
        CidrBlock=random_cidr,
        AvailabilityZoneId="use1-az6",
        TagSpecifications=[
            {"ResourceType": "subnet", "Tags": [{"Key": "name", "Value": "some-vpc"}]}
        ],
    )

    assert subnet.tags == [{"Key": "name", "Value": "some-vpc"}]


@mock_ec2
def test_available_ip_addresses_in_subnet():
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "ServerMode is not guaranteed to be empty - other subnets will affect the count"
        )
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    cidr_range_addresses = [
        ("10.0.0.0/16", 65531),
        ("10.0.0.0/17", 32763),
        ("10.0.0.0/18", 16379),
        ("10.0.0.0/19", 8187),
        ("10.0.0.0/20", 4091),
        ("10.0.0.0/21", 2043),
        ("10.0.0.0/22", 1019),
        ("10.0.0.0/23", 507),
        ("10.0.0.0/24", 251),
        ("10.0.0.0/25", 123),
        ("10.0.0.0/26", 59),
        ("10.0.0.0/27", 27),
        ("10.0.0.0/28", 11),
    ]
    for cidr, expected_count in cidr_range_addresses:
        validate_subnet_details(client, vpc, cidr, expected_count)


@mock_ec2
def test_available_ip_addresses_in_subnet_with_enis():
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "ServerMode is not guaranteed to be empty - other ENI's will affect the count"
        )
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    # Verify behaviour for various CIDR ranges (...)
    # Don't try to assign ENIs to /27 and /28, as there are not a lot of IP addresses to go around
    cidr_range_addresses = [
        ("10.0.0.0/16", 65531),
        ("10.0.0.0/17", 32763),
        ("10.0.0.0/18", 16379),
        ("10.0.0.0/19", 8187),
        ("10.0.0.0/20", 4091),
        ("10.0.0.0/21", 2043),
        ("10.0.0.0/22", 1019),
        ("10.0.0.0/23", 507),
        ("10.0.0.0/24", 251),
        ("10.0.0.0/25", 123),
        ("10.0.0.0/26", 59),
    ]
    for cidr, expected_count in cidr_range_addresses:
        validate_subnet_details_after_creating_eni(client, vpc, cidr, expected_count)


def validate_subnet_details(client, vpc, cidr, expected_ip_address_count):
    subnet = client.create_subnet(
        VpcId=vpc.id, CidrBlock=cidr, AvailabilityZone="us-west-1b"
    )["Subnet"]
    assert subnet["AvailableIpAddressCount"] == expected_ip_address_count
    client.delete_subnet(SubnetId=subnet["SubnetId"])


def validate_subnet_details_after_creating_eni(
    client, vpc, cidr, expected_ip_address_count
):
    subnet = client.create_subnet(
        VpcId=vpc.id, CidrBlock=cidr, AvailabilityZone="us-west-1b"
    )["Subnet"]
    # Create a random number of Elastic Network Interfaces
    nr_of_eni_to_create = random.randint(0, 5)
    ip_addresses_assigned = 0
    enis_created = []
    for _ in range(0, nr_of_eni_to_create):
        # Create a random number of IP addresses per ENI
        nr_of_ip_addresses = random.randint(1, 5)
        if nr_of_ip_addresses == 1:
            # Pick the first available IP address (First 4 are reserved by AWS)
            private_address = "10.0.0." + str(ip_addresses_assigned + 4)
            eni = client.create_network_interface(
                SubnetId=subnet["SubnetId"], PrivateIpAddress=private_address
            )["NetworkInterface"]
            enis_created.append(eni)
            ip_addresses_assigned = ip_addresses_assigned + 1
        else:
            # Assign a list of IP addresses
            private_addresses = [
                "10.0.0." + str(4 + ip_addresses_assigned + i)
                for i in range(0, nr_of_ip_addresses)
            ]
            eni = client.create_network_interface(
                SubnetId=subnet["SubnetId"],
                PrivateIpAddresses=[
                    {"PrivateIpAddress": address} for address in private_addresses
                ],
            )["NetworkInterface"]
            enis_created.append(eni)
            ip_addresses_assigned = ip_addresses_assigned + nr_of_ip_addresses  #

    # Verify that the nr of available IP addresses takes these ENIs into account
    updated_subnet = client.describe_subnets(SubnetIds=[subnet["SubnetId"]])["Subnets"][
        0
    ]

    private_addresses = []
    for eni in enis_created:
        private_addresses.extend(
            [address["PrivateIpAddress"] for address in eni["PrivateIpAddresses"]]
        )
    error_msg = f"Nr of IP addresses for Subnet with CIDR {cidr} is incorrect. Expected: {expected_ip_address_count}, Actual: {updated_subnet['AvailableIpAddressCount']}. Addresses: {private_addresses}"
    assert (
        updated_subnet["AvailableIpAddressCount"]
        == expected_ip_address_count - ip_addresses_assigned
    ), error_msg
    # Clean up, as we have to create a few more subnets that shouldn't interfere with each other
    for eni in enis_created:
        client.delete_network_interface(NetworkInterfaceId=eni["NetworkInterfaceId"])
    client.delete_subnet(SubnetId=subnet["SubnetId"])


@mock_ec2
def test_run_instances_should_attach_to_default_subnet():
    # https://github.com/getmoto/moto/issues/2877
    ec2 = boto3.resource("ec2", region_name="sa-east-1")
    client = boto3.client("ec2", region_name="sa-east-1")
    sec_group_name = str(uuid4())[0:6]
    ec2.create_security_group(
        GroupName=sec_group_name, Description="Test security group sg01"
    )
    # run_instances
    instances = client.run_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SecurityGroups=[sec_group_name]
    )
    # Assert subnet is created appropriately
    subnets = client.describe_subnets(
        Filters=[{"Name": "defaultForAz", "Values": ["true"]}]
    )["Subnets"]
    default_subnet_id = subnets[0]["SubnetId"]
    if len(subnets) > 1:
        default_subnet_id1 = subnets[1]["SubnetId"]
    assert (
        instances["Instances"][0]["NetworkInterfaces"][0]["SubnetId"]
        == default_subnet_id
        or instances["Instances"][0]["NetworkInterfaces"][0]["SubnetId"]
        == default_subnet_id1
    )

    if not settings.TEST_SERVER_MODE:
        # Available IP addresses will depend on other resources that might be created in parallel
        assert (
            subnets[0]["AvailableIpAddressCount"] == 4090
            or subnets[1]["AvailableIpAddressCount"] == 4090
        )


@mock_ec2
def test_describe_subnets_by_vpc_id():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet1 = ec2.create_subnet(
        VpcId=vpc1.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )
    vpc2 = ec2.create_vpc(CidrBlock="172.31.0.0/16")
    subnet2 = ec2.create_subnet(
        VpcId=vpc2.id, CidrBlock="172.31.48.0/20", AvailabilityZone="us-west-1b"
    )

    subnets = client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc1.id]}]
    ).get("Subnets", [])
    assert len(subnets) == 1
    assert subnets[0]["SubnetId"] == subnet1.id

    subnets = client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc2.id]}]
    ).get("Subnets", [])
    assert len(subnets) == 1
    assert subnets[0]["SubnetId"] == subnet2.id

    # Specify multiple VPCs in Filter.
    subnets = client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc1.id, vpc2.id]}]
    ).get("Subnets", [])
    assert len(subnets) == 2

    # Specify mismatched SubnetIds/Filters.
    subnets = client.describe_subnets(
        SubnetIds=[subnet1.id], Filters=[{"Name": "vpc-id", "Values": [vpc2.id]}]
    ).get("Subnets", [])
    assert len(subnets) == 0


@mock_ec2
def test_describe_subnets_by_state():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )

    subnets = client.describe_subnets(
        Filters=[{"Name": "state", "Values": ["available"]}]
    ).get("Subnets", [])
    for subnet in subnets:
        assert subnet["State"] == "available"


@mock_ec2
def test_associate_subnet_cidr_block():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet_object = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )

    subnets = client.describe_subnets(SubnetIds=[subnet_object.id])["Subnets"]
    association_set = subnets[0]["Ipv6CidrBlockAssociationSet"]
    assert association_set == []

    res = client.associate_subnet_cidr_block(
        Ipv6CidrBlock="1080::1:200C:417A/112", SubnetId=subnet_object.id
    )
    assert "Ipv6CidrBlockAssociation" in res
    association = res["Ipv6CidrBlockAssociation"]
    assert association["AssociationId"].startswith("subnet-cidr-assoc-")
    assert association["Ipv6CidrBlock"] == "1080::1:200C:417A/112"
    assert association["Ipv6CidrBlockState"] == {"State": "associated"}

    subnets = client.describe_subnets(SubnetIds=[subnet_object.id])["Subnets"]
    association_set = subnets[0]["Ipv6CidrBlockAssociationSet"]
    assert len(association_set) == 1
    assert association_set[0]["AssociationId"] == association["AssociationId"]
    assert association_set[0]["Ipv6CidrBlock"] == "1080::1:200C:417A/112"


@mock_ec2
def test_disassociate_subnet_cidr_block():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet_object = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )

    client.associate_subnet_cidr_block(
        Ipv6CidrBlock="1080::1:200C:417A/111", SubnetId=subnet_object.id
    )
    association_id = client.associate_subnet_cidr_block(
        Ipv6CidrBlock="1080::1:200C:417A/999", SubnetId=subnet_object.id
    )["Ipv6CidrBlockAssociation"]["AssociationId"]

    subnets = client.describe_subnets(SubnetIds=[subnet_object.id])["Subnets"]
    association_set = subnets[0]["Ipv6CidrBlockAssociationSet"]
    assert len(association_set) == 2

    client.disassociate_subnet_cidr_block(AssociationId=association_id)

    subnets = client.describe_subnets(SubnetIds=[subnet_object.id])["Subnets"]
    association_set = subnets[0]["Ipv6CidrBlockAssociationSet"]
    assert len(association_set) == 1
    assert association_set[0]["Ipv6CidrBlock"] == "1080::1:200C:417A/111"


@mock_ec2
def test_describe_subnets_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_subnets(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DescribeSubnets operation: Request would have succeeded, but DryRun flag is set"
    )
