from __future__ import unicode_literals

import random

import boto
import boto3
import boto.vpc

import pytest
import sure  # noqa
from boto.exception import EC2ResponseError
from botocore.exceptions import ClientError
from moto import mock_ec2, mock_ec2_deprecated, settings
from tests import EXAMPLE_AMI_ID
from uuid import uuid4
from unittest import SkipTest


# Has boto3 equivalent
@mock_ec2_deprecated
def test_subnets():
    ec2 = boto.connect_ec2("the_key", "the_secret")
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(1 + len(ec2.get_all_zones()))

    conn.delete_subnet(subnet.id)

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(0 + len(ec2.get_all_zones()))

    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_subnet(subnet.id)
    cm.value.code.should.equal("InvalidSubnetID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_subnets_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    ours = client.describe_subnets(SubnetIds=[subnet.id])["Subnets"]
    ours.should.have.length_of(1)

    client.delete_subnet(SubnetId=subnet.id)

    with pytest.raises(ClientError) as ex:
        client.describe_subnets(SubnetIds=[subnet.id])
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidSubnetID.NotFound")

    with pytest.raises(ClientError) as ex:
        client.delete_subnet(SubnetId=subnet.id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidSubnetID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_subnet_create_vpc_validation():
    conn = boto.connect_vpc("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.create_subnet("vpc-abcd1234", "10.0.0.0/18")
    cm.value.code.should.equal("InvalidVpcID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_subnet_create_vpc_validation_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        ec2.create_subnet(VpcId="vpc-abcd1234", CidrBlock="10.0.0.0/18")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidVpcID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_subnet_tagging():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    subnet.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the subnet
    subnet = conn.get_all_subnets(subnet_ids=[subnet.id])[0]
    subnet.tags.should.have.length_of(1)
    subnet.tags["a key"].should.equal("some value")


@mock_ec2
def test_subnet_tagging_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    subnet.create_tags(Tags=[{"Key": "a key", "Value": "some value"}])

    tag = client.describe_tags(
        Filters=[{"Name": "resource-id", "Values": [subnet.id]}]
    )["Tags"][0]
    tag["Key"].should.equal("a key")
    tag["Value"].should.equal("some value")

    # Refresh the subnet
    subnet = client.describe_subnets(SubnetIds=[subnet.id])["Subnets"][0]
    subnet["Tags"].should.equal([{"Key": "a key", "Value": "some value"}])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_subnet_should_have_proper_availability_zone_set():
    conn = boto.vpc.connect_to_region("us-west-1")
    vpcA = conn.create_vpc("10.0.0.0/16")
    subnetA = conn.create_subnet(vpcA.id, "10.0.0.0/24", availability_zone="us-west-1b")
    subnetA.availability_zone.should.equal("us-west-1b")


@mock_ec2
def test_subnet_should_have_proper_availability_zone_set_boto3():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    vpcA = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnetA = ec2.create_subnet(
        VpcId=vpcA.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1b"
    )
    subnetA.availability_zone.should.equal("us-west-1b")


@mock_ec2
def test_availability_zone_in_create_subnet():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="172.31.0.0/16")

    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.31.48.0/20", AvailabilityZoneId="use1-az6"
    )
    subnet.availability_zone_id.should.equal("use1-az6")


@mock_ec2
def test_default_subnet():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode will have conflicting CidrBlocks")
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    default_vpc = list(ec2.vpcs.all())[0]
    default_vpc.cidr_block.should.equal("172.31.0.0/16")
    default_vpc.reload()
    default_vpc.is_default.should.be.ok

    subnet = ec2.create_subnet(
        VpcId=default_vpc.id, CidrBlock="172.31.48.0/20", AvailabilityZone="us-west-1a"
    )
    subnet.reload()
    subnet.map_public_ip_on_launch.shouldnt.be.ok


# Has boto3 equivalent
@mock_ec2_deprecated
def test_non_default_subnet():
    vpc_cli = boto.vpc.connect_to_region("us-west-1")

    # Create the non default VPC
    vpc = vpc_cli.create_vpc("10.0.0.0/16")
    vpc.is_default.shouldnt.be.ok

    subnet = vpc_cli.create_subnet(vpc.id, "10.0.0.0/24")
    subnet = vpc_cli.get_all_subnets(subnet_ids=[subnet.id])[0]
    subnet.mapPublicIpOnLaunch.should.equal("false")


@mock_ec2
def test_boto3_non_default_subnet():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create the non default VPC
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )
    subnet.reload()
    subnet.map_public_ip_on_launch.shouldnt.be.ok


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
    subnet.map_public_ip_on_launch.shouldnt.be.ok

    client.modify_subnet_attribute(
        SubnetId=subnet.id, MapPublicIpOnLaunch={"Value": False}
    )
    subnet.reload()
    subnet.map_public_ip_on_launch.shouldnt.be.ok

    client.modify_subnet_attribute(
        SubnetId=subnet.id, MapPublicIpOnLaunch={"Value": True}
    )
    subnet.reload()
    subnet.map_public_ip_on_launch.should.be.ok


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
    subnets = client.describe_subnets()

    # For non default subnet, attribute value should be 'False'
    subnet.assign_ipv6_address_on_creation.shouldnt.be.ok

    client.modify_subnet_attribute(
        SubnetId=subnet.id, AssignIpv6AddressOnCreation={"Value": False}
    )
    subnet.reload()
    subnet.assign_ipv6_address_on_creation.shouldnt.be.ok

    client.modify_subnet_attribute(
        SubnetId=subnet.id, AssignIpv6AddressOnCreation={"Value": True}
    )
    subnet.reload()
    subnet.assign_ipv6_address_on_creation.should.be.ok


@mock_ec2
def test_modify_subnet_attribute_validation():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_subnet_get_by_id():
    ec2 = boto.ec2.connect_to_region("us-west-1")
    conn = boto.vpc.connect_to_region("us-west-1")
    vpcA = conn.create_vpc("10.0.0.0/16")
    subnetA = conn.create_subnet(vpcA.id, "10.0.0.0/24", availability_zone="us-west-1a")
    vpcB = conn.create_vpc("10.0.0.0/16")
    subnetB1 = conn.create_subnet(
        vpcB.id, "10.0.0.0/24", availability_zone="us-west-1a"
    )
    subnetB2 = conn.create_subnet(
        vpcB.id, "10.0.1.0/24", availability_zone="us-west-1b"
    )

    subnets_by_id = conn.get_all_subnets(subnet_ids=[subnetA.id, subnetB1.id])
    subnets_by_id.should.have.length_of(2)
    subnets_by_id = tuple(map(lambda s: s.id, subnets_by_id))
    subnetA.id.should.be.within(subnets_by_id)
    subnetB1.id.should.be.within(subnets_by_id)

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_subnets(subnet_ids=["subnet-does_not_exist"])
    cm.value.code.should.equal("InvalidSubnetID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_subnet_get_by_id_boto3():
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

    subnets_by_id = client.describe_subnets(SubnetIds=[subnetA.id, subnetB1.id])[
        "Subnets"
    ]
    subnets_by_id.should.have.length_of(2)
    subnets_by_id = tuple(map(lambda s: s["SubnetId"], subnets_by_id))
    subnetA.id.should.be.within(subnets_by_id)
    subnetB1.id.should.be.within(subnets_by_id)

    with pytest.raises(ClientError) as ex:
        client.describe_subnets(SubnetIds=["subnet-does_not_exist"])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidSubnetID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_subnets_filtering():
    ec2 = boto.ec2.connect_to_region("us-west-1")
    conn = boto.vpc.connect_to_region("us-west-1")
    vpcA = conn.create_vpc("10.0.0.0/16")
    subnetA = conn.create_subnet(vpcA.id, "10.0.0.0/24", availability_zone="us-west-1a")
    vpcB = conn.create_vpc("10.0.0.0/16")
    subnetB1 = conn.create_subnet(
        vpcB.id, "10.0.0.0/24", availability_zone="us-west-1a"
    )
    subnetB2 = conn.create_subnet(
        vpcB.id, "10.0.1.0/24", availability_zone="us-west-1b"
    )

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(3 + len(ec2.get_all_zones()))

    # Filter by VPC ID
    subnets_by_vpc = conn.get_all_subnets(filters={"vpc-id": vpcB.id})
    subnets_by_vpc.should.have.length_of(2)
    set([subnet.id for subnet in subnets_by_vpc]).should.equal(
        set([subnetB1.id, subnetB2.id])
    )

    # Filter by CIDR variations
    subnets_by_cidr1 = conn.get_all_subnets(filters={"cidr": "10.0.0.0/24"})
    subnets_by_cidr1.should.have.length_of(2)
    set([subnet.id for subnet in subnets_by_cidr1]).should.equal(
        set([subnetA.id, subnetB1.id])
    )

    subnets_by_cidr2 = conn.get_all_subnets(filters={"cidr-block": "10.0.0.0/24"})
    subnets_by_cidr2.should.have.length_of(2)
    set([subnet.id for subnet in subnets_by_cidr2]).should.equal(
        set([subnetA.id, subnetB1.id])
    )

    subnets_by_cidr3 = conn.get_all_subnets(filters={"cidrBlock": "10.0.0.0/24"})
    subnets_by_cidr3.should.have.length_of(2)
    set([subnet.id for subnet in subnets_by_cidr3]).should.equal(
        set([subnetA.id, subnetB1.id])
    )

    # Filter by VPC ID and CIDR
    subnets_by_vpc_and_cidr = conn.get_all_subnets(
        filters={"vpc-id": vpcB.id, "cidr": "10.0.0.0/24"}
    )
    subnets_by_vpc_and_cidr.should.have.length_of(1)
    set([subnet.id for subnet in subnets_by_vpc_and_cidr]).should.equal(
        set([subnetB1.id])
    )

    # Filter by subnet ID
    subnets_by_id = conn.get_all_subnets(filters={"subnet-id": subnetA.id})
    subnets_by_id.should.have.length_of(1)
    set([subnet.id for subnet in subnets_by_id]).should.equal(set([subnetA.id]))

    # Filter by availabilityZone
    subnets_by_az = conn.get_all_subnets(
        filters={"availabilityZone": "us-west-1a", "vpc-id": vpcB.id}
    )
    subnets_by_az.should.have.length_of(1)
    set([subnet.id for subnet in subnets_by_az]).should.equal(set([subnetB1.id]))

    # Filter by defaultForAz

    subnets_by_az = conn.get_all_subnets(filters={"defaultForAz": "true"})
    subnets_by_az.should.have.length_of(len(conn.get_all_zones()))

    # Unsupported filter
    conn.get_all_subnets.when.called_with(
        filters={"not-implemented-filter": "foobar"}
    ).should.throw(NotImplementedError)


@mock_ec2
def test_get_subnets_filtering_boto3():
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
        all_subnet_ids.should.contain(subnetA.id)
        all_subnet_ids.should.contain(subnetB1.id)
        all_subnet_ids.should.contain(subnetB2.id)
    else:
        all_subnets.should.have.length_of(3 + nr_of_a_zones)

    # Filter by VPC ID
    subnets_by_vpc = client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpcB.id]}]
    )["Subnets"]
    subnets_by_vpc.should.have.length_of(2)
    set([subnet["SubnetId"] for subnet in subnets_by_vpc]).should.equal(
        set([subnetB1.id, subnetB2.id])
    )

    # Filter by CIDR variations
    subnets_by_cidr1 = client.describe_subnets(
        Filters=[{"Name": "cidr", "Values": ["10.0.0.0/24"]}]
    )["Subnets"]
    subnets_by_cidr1 = [s["SubnetId"] for s in subnets_by_cidr1]
    subnets_by_cidr1.should.contain(subnetA.id)
    subnets_by_cidr1.should.contain(subnetB1.id)
    subnets_by_cidr1.shouldnt.contain(subnetB2.id)

    subnets_by_cidr2 = client.describe_subnets(
        Filters=[{"Name": "cidr-block", "Values": ["10.0.0.0/24"]}]
    )["Subnets"]
    subnets_by_cidr2 = [s["SubnetId"] for s in subnets_by_cidr2]
    subnets_by_cidr2.should.contain(subnetA.id)
    subnets_by_cidr2.should.contain(subnetB1.id)
    subnets_by_cidr2.shouldnt.contain(subnetB2.id)

    subnets_by_cidr3 = client.describe_subnets(
        Filters=[{"Name": "cidrBlock", "Values": ["10.0.0.0/24"]}]
    )["Subnets"]
    subnets_by_cidr3 = [s["SubnetId"] for s in subnets_by_cidr3]
    subnets_by_cidr3.should.contain(subnetA.id)
    subnets_by_cidr3.should.contain(subnetB1.id)
    subnets_by_cidr3.shouldnt.contain(subnetB2.id)

    # Filter by VPC ID and CIDR
    subnets_by_vpc_and_cidr = client.describe_subnets(
        Filters=[
            {"Name": "vpc-id", "Values": [vpcB.id]},
            {"Name": "cidr", "Values": ["10.0.0.0/24"]},
        ]
    )["Subnets"]
    subnets_by_vpc_and_cidr.should.have.length_of(1)
    subnets_by_vpc_and_cidr[0]["SubnetId"].should.equal(subnetB1.id)

    # Filter by subnet ID
    subnets_by_id = client.describe_subnets(
        Filters=[{"Name": "subnet-id", "Values": [subnetA.id]}]
    )["Subnets"]
    subnets_by_id.should.have.length_of(1)
    subnets_by_id[0]["SubnetId"].should.equal(subnetA.id)

    # Filter by availabilityZone
    subnets_by_az = client.describe_subnets(
        Filters=[
            {"Name": "availabilityZone", "Values": ["us-west-1a"]},
            {"Name": "vpc-id", "Values": [vpcB.id]},
        ]
    )["Subnets"]
    subnets_by_az.should.have.length_of(1)
    subnets_by_az[0]["SubnetId"].should.equal(subnetB1.id)

    if not settings.TEST_SERVER_MODE:
        # Filter by defaultForAz
        subnets_by_az = client.describe_subnets(
            Filters=[{"Name": "defaultForAz", "Values": ["true"]}]
        )["Subnets"]
        subnets_by_az.should.have.length_of(nr_of_a_zones)

        # Unsupported filter
        filters = [{"Name": "not-implemented-filter", "Values": ["foobar"]}]
        client.describe_subnets.when.called_with(Filters=filters).should.throw(
            NotImplementedError
        )


@mock_ec2
def test_create_subnet_response_fields():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = client.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )["Subnet"]

    subnet.should.have.key("AvailabilityZone")
    subnet.should.have.key("AvailabilityZoneId")
    subnet.should.have.key("AvailableIpAddressCount")
    subnet.should.have.key("CidrBlock")
    subnet.should.have.key("State")
    subnet.should.have.key("SubnetId")
    subnet.should.have.key("VpcId")
    subnet.should.have.key("Tags")
    subnet.should.have.key("DefaultForAz").which.should.equal(False)
    subnet.should.have.key("MapPublicIpOnLaunch").which.should.equal(False)
    subnet.should.have.key("OwnerId")
    subnet.should.have.key("AssignIpv6AddressOnCreation").which.should.equal(False)

    subnet_arn = "arn:aws:ec2:{region}:{owner_id}:subnet/{subnet_id}".format(
        region=subnet["AvailabilityZone"][0:-1],
        owner_id=subnet["OwnerId"],
        subnet_id=subnet["SubnetId"],
    )
    subnet.should.have.key("SubnetArn").which.should.equal(subnet_arn)
    subnet.should.have.key("Ipv6CidrBlockAssociationSet").which.should.equal([])


@mock_ec2
def test_describe_subnet_response_fields():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet_object = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )

    subnets = client.describe_subnets(SubnetIds=[subnet_object.id])["Subnets"]
    subnets.should.have.length_of(1)
    subnet = subnets[0]

    subnet.should.have.key("AvailabilityZone")
    subnet.should.have.key("AvailabilityZoneId")
    subnet.should.have.key("AvailableIpAddressCount")
    subnet.should.have.key("CidrBlock")
    subnet.should.have.key("State")
    subnet.should.have.key("SubnetId")
    subnet.should.have.key("VpcId")
    subnet.shouldnt.have.key("Tags")
    subnet.should.have.key("DefaultForAz").which.should.equal(False)
    subnet.should.have.key("MapPublicIpOnLaunch").which.should.equal(False)
    subnet.should.have.key("OwnerId")
    subnet.should.have.key("AssignIpv6AddressOnCreation").which.should.equal(False)

    subnet_arn = "arn:aws:ec2:{region}:{owner_id}:subnet/{subnet_id}".format(
        region=subnet["AvailabilityZone"][0:-1],
        owner_id=subnet["OwnerId"],
        subnet_id=subnet["SubnetId"],
    )
    subnet.should.have.key("SubnetArn").which.should.equal(subnet_arn)
    subnet.should.have.key("Ipv6CidrBlockAssociationSet").which.should.equal([])


@mock_ec2
def test_create_subnet_with_invalid_availability_zone():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    subnet_availability_zone = "asfasfas"
    with pytest.raises(ClientError) as ex:
        subnet = client.create_subnet(
            VpcId=vpc.id,
            CidrBlock="10.0.0.0/24",
            AvailabilityZone=subnet_availability_zone,
        )
    assert str(ex.value).startswith(
        "An error occurred (InvalidParameterValue) when calling the CreateSubnet "
        "operation: Value ({}) for parameter availabilityZone is invalid. Subnets can currently only be created in the following availability zones: ".format(
            subnet_availability_zone
        )
    )


@mock_ec2
def test_create_subnet_with_invalid_cidr_range():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    subnet_cidr_block = "10.1.0.0/20"
    with pytest.raises(ClientError) as ex:
        subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
    str(ex.value).should.equal(
        "An error occurred (InvalidSubnet.Range) when calling the CreateSubnet "
        "operation: The CIDR '{}' is invalid.".format(subnet_cidr_block)
    )


@mock_ec2
def test_create_subnet_with_invalid_cidr_range_multiple_vpc_cidr_blocks():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.meta.client.associate_vpc_cidr_block(CidrBlock="10.1.0.0/16", VpcId=vpc.id)
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    subnet_cidr_block = "10.2.0.0/20"
    with pytest.raises(ClientError) as ex:
        subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
    str(ex.value).should.equal(
        "An error occurred (InvalidSubnet.Range) when calling the CreateSubnet "
        "operation: The CIDR '{}' is invalid.".format(subnet_cidr_block)
    )


@mock_ec2
def test_create_subnet_with_invalid_cidr_block_parameter():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    subnet_cidr_block = "1000.1.0.0/20"
    with pytest.raises(ClientError) as ex:
        subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
    str(ex.value).should.equal(
        "An error occurred (InvalidParameterValue) when calling the CreateSubnet "
        "operation: Value ({}) for parameter cidrBlock is invalid. This is not a valid CIDR block.".format(
            subnet_cidr_block
        )
    )


@mock_ec2
def test_create_subnets_with_multiple_vpc_cidr_blocks():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.meta.client.associate_vpc_cidr_block(CidrBlock="10.1.0.0/16", VpcId=vpc.id)
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

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
    subnets.should.have.length_of(2)

    for subnet in subnets:
        subnet.should.have.key("AvailabilityZone")
        subnet.should.have.key("AvailabilityZoneId")
        subnet.should.have.key("AvailableIpAddressCount")
        subnet.should.have.key("CidrBlock")
        subnet.should.have.key("State")
        subnet.should.have.key("SubnetId")
        subnet.should.have.key("VpcId")
        subnet.shouldnt.have.key("Tags")
        subnet.should.have.key("DefaultForAz").which.should.equal(False)
        subnet.should.have.key("MapPublicIpOnLaunch").which.should.equal(False)
        subnet.should.have.key("OwnerId")
        subnet.should.have.key("AssignIpv6AddressOnCreation").which.should.equal(False)


@mock_ec2
def test_create_subnets_with_overlapping_cidr_blocks():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    subnet_cidr_block = "10.0.0.0/24"
    with pytest.raises(ClientError) as ex:
        subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
        subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
    str(ex.value).should.equal(
        "An error occurred (InvalidSubnet.Conflict) when calling the CreateSubnet "
        "operation: The CIDR '{}' conflicts with another subnet".format(
            subnet_cidr_block
        )
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
    for (cidr, expected_count) in cidr_range_addresses:
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
    for (cidr, expected_count) in cidr_range_addresses:
        validate_subnet_details_after_creating_eni(client, vpc, cidr, expected_count)


def validate_subnet_details(client, vpc, cidr, expected_ip_address_count):
    subnet = client.create_subnet(
        VpcId=vpc.id, CidrBlock=cidr, AvailabilityZone="us-west-1b"
    )["Subnet"]
    subnet["AvailableIpAddressCount"].should.equal(expected_ip_address_count)
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
    for i in range(0, nr_of_eni_to_create):
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
    error_msg = (
        "Nr of IP addresses for Subnet with CIDR {0} is incorrect. Expected: {1}, Actual: {2}. "
        "Addresses: {3}"
    )
    with sure.ensure(
        error_msg,
        cidr,
        str(expected_ip_address_count),
        updated_subnet["AvailableIpAddressCount"],
        str(private_addresses),
    ):
        updated_subnet["AvailableIpAddressCount"].should.equal(
            expected_ip_address_count - ip_addresses_assigned
        )
    # Clean up, as we have to create a few more subnets that shouldn't interfere with each other
    for eni in enis_created:
        client.delete_network_interface(NetworkInterfaceId=eni["NetworkInterfaceId"])
    client.delete_subnet(SubnetId=subnet["SubnetId"])


@mock_ec2
def test_run_instances_should_attach_to_default_subnet():
    # https://github.com/spulec/moto/issues/2877
    ec2 = boto3.resource("ec2", region_name="sa-east-1")
    client = boto3.client("ec2", region_name="sa-east-1")
    sec_group_name = str(uuid4())[0:6]
    ec2.create_security_group(
        GroupName=sec_group_name, Description="Test security group sg01"
    )
    # run_instances
    instances = client.run_instances(
        ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1, SecurityGroups=[sec_group_name],
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
    subnets.should.have.length_of(1)
    subnets[0]["SubnetId"].should.equal(subnet1.id)

    subnets = client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc2.id]}]
    ).get("Subnets", [])
    subnets.should.have.length_of(1)
    subnets[0]["SubnetId"].should.equal(subnet2.id)

    # Specify multiple VPCs in Filter.
    subnets = client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc1.id, vpc2.id]}]
    ).get("Subnets", [])
    subnets.should.have.length_of(2)

    # Specify mismatched SubnetIds/Filters.
    subnets = client.describe_subnets(
        SubnetIds=[subnet1.id], Filters=[{"Name": "vpc-id", "Values": [vpc2.id]}]
    ).get("Subnets", [])
    subnets.should.have.length_of(0)


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
        subnet["State"].should.equal("available")


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
    association_set.should.equal([])

    res = client.associate_subnet_cidr_block(
        Ipv6CidrBlock="1080::1:200C:417A/112", SubnetId=subnet_object.id
    )
    res.should.have.key("Ipv6CidrBlockAssociation")
    association = res["Ipv6CidrBlockAssociation"]
    association.should.have.key("AssociationId").match("subnet-cidr-assoc-[a-z0-9]+")
    association.should.have.key("Ipv6CidrBlock").equals("1080::1:200C:417A/112")
    association.should.have.key("Ipv6CidrBlockState").equals({"State": "associated"})

    subnets = client.describe_subnets(SubnetIds=[subnet_object.id])["Subnets"]
    association_set = subnets[0]["Ipv6CidrBlockAssociationSet"]
    association_set.should.have.length_of(1)
    association_set[0].should.have.key("AssociationId").equal(
        association["AssociationId"]
    )
    association_set[0].should.have.key("Ipv6CidrBlock").equals("1080::1:200C:417A/112")


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
    association_set.should.have.length_of(2)

    client.disassociate_subnet_cidr_block(AssociationId=association_id)

    subnets = client.describe_subnets(SubnetIds=[subnet_object.id])["Subnets"]
    association_set = subnets[0]["Ipv6CidrBlockAssociationSet"]
    association_set.should.have.length_of(1)
    association_set[0]["Ipv6CidrBlock"].should.equal("1080::1:200C:417A/111")


@mock_ec2
def test_describe_subnets_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_subnets(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DescribeSubnets operation: Request would have succeeded, but DryRun flag is set"
    )
