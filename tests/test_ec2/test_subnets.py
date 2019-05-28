from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises  # noqa
from nose.tools import assert_raises

import boto3
import boto
import boto.vpc
from boto.exception import EC2ResponseError
from botocore.exceptions import ParamValidationError, ClientError
import json
import sure  # noqa

from moto import mock_cloudformation_deprecated, mock_ec2, mock_ec2_deprecated


@mock_ec2_deprecated
def test_subnets():
    ec2 = boto.connect_ec2('the_key', 'the_secret')
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(1 + len(ec2.get_all_zones()))

    conn.delete_subnet(subnet.id)

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(0 + len(ec2.get_all_zones()))

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_subnet(subnet.id)
    cm.exception.code.should.equal('InvalidSubnetID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_subnet_create_vpc_validation():
    conn = boto.connect_vpc('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as cm:
        conn.create_subnet("vpc-abcd1234", "10.0.0.0/18")
    cm.exception.code.should.equal('InvalidVpcID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_subnet_tagging():
    conn = boto.connect_vpc('the_key', 'the_secret')
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


@mock_ec2_deprecated
def test_subnet_should_have_proper_availability_zone_set():
    conn = boto.vpc.connect_to_region('us-west-1')
    vpcA = conn.create_vpc("10.0.0.0/16")
    subnetA = conn.create_subnet(
        vpcA.id, "10.0.0.0/24", availability_zone='us-west-1b')
    subnetA.availability_zone.should.equal('us-west-1b')


@mock_ec2
def test_default_subnet():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    default_vpc = list(ec2.vpcs.all())[0]
    default_vpc.cidr_block.should.equal('172.31.0.0/16')
    default_vpc.reload()
    default_vpc.is_default.should.be.ok

    subnet = ec2.create_subnet(
        VpcId=default_vpc.id, CidrBlock='172.31.48.0/20', AvailabilityZone='us-west-1a')
    subnet.reload()
    subnet.map_public_ip_on_launch.shouldnt.be.ok


@mock_ec2_deprecated
def test_non_default_subnet():
    vpc_cli = boto.vpc.connect_to_region('us-west-1')

    # Create the non default VPC
    vpc = vpc_cli.create_vpc("10.0.0.0/16")
    vpc.is_default.shouldnt.be.ok

    subnet = vpc_cli.create_subnet(vpc.id, "10.0.0.0/24")
    subnet = vpc_cli.get_all_subnets(subnet_ids=[subnet.id])[0]
    subnet.mapPublicIpOnLaunch.should.equal('false')


@mock_ec2
def test_boto3_non_default_subnet():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Create the non default VPC
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock='10.0.0.0/24', AvailabilityZone='us-west-1a')
    subnet.reload()
    subnet.map_public_ip_on_launch.shouldnt.be.ok


@mock_ec2
def test_modify_subnet_attribute_public_ip_on_launch():
    ec2 = boto3.resource('ec2', region_name='us-west-1')
    client = boto3.client('ec2', region_name='us-west-1')

    # Get the default VPC
    vpc = list(ec2.vpcs.all())[0]

    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.31.48.0/20", AvailabilityZone='us-west-1a')

    # 'map_public_ip_on_launch' is set when calling 'DescribeSubnets' action
    subnet.reload()

    # For non default subnet, attribute value should be 'False'
    subnet.map_public_ip_on_launch.shouldnt.be.ok

    client.modify_subnet_attribute(
        SubnetId=subnet.id, MapPublicIpOnLaunch={'Value': False})
    subnet.reload()
    subnet.map_public_ip_on_launch.shouldnt.be.ok

    client.modify_subnet_attribute(
        SubnetId=subnet.id, MapPublicIpOnLaunch={'Value': True})
    subnet.reload()
    subnet.map_public_ip_on_launch.should.be.ok


@mock_ec2
def test_modify_subnet_attribute_assign_ipv6_address_on_creation():
    ec2 = boto3.resource('ec2', region_name='us-west-1')
    client = boto3.client('ec2', region_name='us-west-1')

    # Get the default VPC
    vpc = list(ec2.vpcs.all())[0]

    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock='172.31.112.0/20', AvailabilityZone='us-west-1a')

    # 'map_public_ip_on_launch' is set when calling 'DescribeSubnets' action
    subnet.reload()

    # For non default subnet, attribute value should be 'False'
    subnet.assign_ipv6_address_on_creation.shouldnt.be.ok

    client.modify_subnet_attribute(
        SubnetId=subnet.id, AssignIpv6AddressOnCreation={'Value': False})
    subnet.reload()
    subnet.assign_ipv6_address_on_creation.shouldnt.be.ok

    client.modify_subnet_attribute(
        SubnetId=subnet.id, AssignIpv6AddressOnCreation={'Value': True})
    subnet.reload()
    subnet.assign_ipv6_address_on_creation.should.be.ok


@mock_ec2
def test_modify_subnet_attribute_validation():
    ec2 = boto3.resource('ec2', region_name='us-west-1')
    client = boto3.client('ec2', region_name='us-west-1')
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock='10.0.0.0/24', AvailabilityZone='us-west-1a')

    with assert_raises(ParamValidationError):
        client.modify_subnet_attribute(
            SubnetId=subnet.id, MapPublicIpOnLaunch={'Value': 'invalid'})


@mock_ec2_deprecated
def test_subnet_get_by_id():
    ec2 = boto.ec2.connect_to_region('us-west-1')
    conn = boto.vpc.connect_to_region('us-west-1')
    vpcA = conn.create_vpc("10.0.0.0/16")
    subnetA = conn.create_subnet(
        vpcA.id, "10.0.0.0/24", availability_zone='us-west-1a')
    vpcB = conn.create_vpc("10.0.0.0/16")
    subnetB1 = conn.create_subnet(
        vpcB.id, "10.0.0.0/24", availability_zone='us-west-1a')
    subnetB2 = conn.create_subnet(
        vpcB.id, "10.0.1.0/24", availability_zone='us-west-1b')

    subnets_by_id = conn.get_all_subnets(subnet_ids=[subnetA.id, subnetB1.id])
    subnets_by_id.should.have.length_of(2)
    subnets_by_id = tuple(map(lambda s: s.id, subnets_by_id))
    subnetA.id.should.be.within(subnets_by_id)
    subnetB1.id.should.be.within(subnets_by_id)

    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_subnets(subnet_ids=['subnet-does_not_exist'])
    cm.exception.code.should.equal('InvalidSubnetID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_get_subnets_filtering():
    ec2 = boto.ec2.connect_to_region('us-west-1')
    conn = boto.vpc.connect_to_region('us-west-1')
    vpcA = conn.create_vpc("10.0.0.0/16")
    subnetA = conn.create_subnet(
        vpcA.id, "10.0.0.0/24", availability_zone='us-west-1a')
    vpcB = conn.create_vpc("10.0.0.0/16")
    subnetB1 = conn.create_subnet(
        vpcB.id, "10.0.0.0/24", availability_zone='us-west-1a')
    subnetB2 = conn.create_subnet(
        vpcB.id, "10.0.1.0/24", availability_zone='us-west-1b')

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(3 + len(ec2.get_all_zones()))

    # Filter by VPC ID
    subnets_by_vpc = conn.get_all_subnets(filters={'vpc-id': vpcB.id})
    subnets_by_vpc.should.have.length_of(2)
    set([subnet.id for subnet in subnets_by_vpc]).should.equal(
        set([subnetB1.id, subnetB2.id]))

    # Filter by CIDR variations
    subnets_by_cidr1 = conn.get_all_subnets(filters={'cidr': "10.0.0.0/24"})
    subnets_by_cidr1.should.have.length_of(2)
    set([subnet.id for subnet in subnets_by_cidr1]
        ).should.equal(set([subnetA.id, subnetB1.id]))

    subnets_by_cidr2 = conn.get_all_subnets(
        filters={'cidr-block': "10.0.0.0/24"})
    subnets_by_cidr2.should.have.length_of(2)
    set([subnet.id for subnet in subnets_by_cidr2]
        ).should.equal(set([subnetA.id, subnetB1.id]))

    subnets_by_cidr3 = conn.get_all_subnets(
        filters={'cidrBlock': "10.0.0.0/24"})
    subnets_by_cidr3.should.have.length_of(2)
    set([subnet.id for subnet in subnets_by_cidr3]
        ).should.equal(set([subnetA.id, subnetB1.id]))

    # Filter by VPC ID and CIDR
    subnets_by_vpc_and_cidr = conn.get_all_subnets(
        filters={'vpc-id': vpcB.id, 'cidr': "10.0.0.0/24"})
    subnets_by_vpc_and_cidr.should.have.length_of(1)
    set([subnet.id for subnet in subnets_by_vpc_and_cidr]
        ).should.equal(set([subnetB1.id]))

    # Filter by subnet ID
    subnets_by_id = conn.get_all_subnets(filters={'subnet-id': subnetA.id})
    subnets_by_id.should.have.length_of(1)
    set([subnet.id for subnet in subnets_by_id]).should.equal(set([subnetA.id]))

    # Filter by availabilityZone
    subnets_by_az = conn.get_all_subnets(
        filters={'availabilityZone': 'us-west-1a', 'vpc-id': vpcB.id})
    subnets_by_az.should.have.length_of(1)
    set([subnet.id for subnet in subnets_by_az]
        ).should.equal(set([subnetB1.id]))

    # Filter by defaultForAz

    subnets_by_az = conn.get_all_subnets(filters={'defaultForAz': "true"})
    subnets_by_az.should.have.length_of(len(conn.get_all_zones()))

    # Unsupported filter
    conn.get_all_subnets.when.called_with(
        filters={'not-implemented-filter': 'foobar'}).should.throw(NotImplementedError)


@mock_ec2_deprecated
@mock_cloudformation_deprecated
def test_subnet_tags_through_cloudformation():
    vpc_conn = boto.vpc.connect_to_region('us-west-1')
    vpc = vpc_conn.create_vpc("10.0.0.0/16")

    subnet_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "testSubnet": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {
                    "VpcId": vpc.id,
                    "CidrBlock": "10.0.0.0/24",
                    "AvailabilityZone": "us-west-1b",
                    "Tags": [{
                        "Key": "foo",
                        "Value": "bar",
                    }, {
                        "Key": "blah",
                        "Value": "baz",
                    }]
                }
            }
        }
    }
    cf_conn = boto.cloudformation.connect_to_region("us-west-1")
    template_json = json.dumps(subnet_template)
    cf_conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    subnet = vpc_conn.get_all_subnets(filters={'cidrBlock': '10.0.0.0/24'})[0]
    subnet.tags["foo"].should.equal("bar")
    subnet.tags["blah"].should.equal("baz")


@mock_ec2
def test_create_subnet_response_fields():
    ec2 = boto3.resource('ec2', region_name='us-west-1')
    client = boto3.client('ec2', region_name='us-west-1')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    subnet = client.create_subnet(
        VpcId=vpc.id, CidrBlock='10.0.0.0/24', AvailabilityZone='us-west-1a')['Subnet']

    subnet.should.have.key('AvailabilityZone')
    subnet.should.have.key('AvailabilityZoneId')
    subnet.should.have.key('AvailableIpAddressCount')
    subnet.should.have.key('CidrBlock')
    subnet.should.have.key('State')
    subnet.should.have.key('SubnetId')
    subnet.should.have.key('VpcId')
    subnet.shouldnt.have.key('Tags')
    subnet.should.have.key('DefaultForAz').which.should.equal(False)
    subnet.should.have.key('MapPublicIpOnLaunch').which.should.equal(False)
    subnet.should.have.key('OwnerId')
    subnet.should.have.key('AssignIpv6AddressOnCreation').which.should.equal(False)

    subnet_arn = "arn:aws:ec2:{region}:{owner_id}:subnet/{subnet_id}".format(region=subnet['AvailabilityZone'][0:-1],
                                                                             owner_id=subnet['OwnerId'],
                                                                             subnet_id=subnet['SubnetId'])
    subnet.should.have.key('SubnetArn').which.should.equal(subnet_arn)
    subnet.should.have.key('Ipv6CidrBlockAssociationSet').which.should.equal([])


@mock_ec2
def test_describe_subnet_response_fields():
    ec2 = boto3.resource('ec2', region_name='us-west-1')
    client = boto3.client('ec2', region_name='us-west-1')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    subnet_object = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock='10.0.0.0/24', AvailabilityZone='us-west-1a')

    subnets = client.describe_subnets(SubnetIds=[subnet_object.id])['Subnets']
    subnets.should.have.length_of(1)
    subnet = subnets[0]

    subnet.should.have.key('AvailabilityZone')
    subnet.should.have.key('AvailabilityZoneId')
    subnet.should.have.key('AvailableIpAddressCount')
    subnet.should.have.key('CidrBlock')
    subnet.should.have.key('State')
    subnet.should.have.key('SubnetId')
    subnet.should.have.key('VpcId')
    subnet.shouldnt.have.key('Tags')
    subnet.should.have.key('DefaultForAz').which.should.equal(False)
    subnet.should.have.key('MapPublicIpOnLaunch').which.should.equal(False)
    subnet.should.have.key('OwnerId')
    subnet.should.have.key('AssignIpv6AddressOnCreation').which.should.equal(False)

    subnet_arn = "arn:aws:ec2:{region}:{owner_id}:subnet/{subnet_id}".format(region=subnet['AvailabilityZone'][0:-1],
                                                                             owner_id=subnet['OwnerId'],
                                                                             subnet_id=subnet['SubnetId'])
    subnet.should.have.key('SubnetArn').which.should.equal(subnet_arn)
    subnet.should.have.key('Ipv6CidrBlockAssociationSet').which.should.equal([])


@mock_ec2
def test_create_subnet_with_invalid_availability_zone():
    ec2 = boto3.resource('ec2', region_name='us-west-1')
    client = boto3.client('ec2', region_name='us-west-1')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')

    subnet_availability_zone = 'asfasfas'
    with assert_raises(ClientError) as ex:
        subnet = client.create_subnet(
            VpcId=vpc.id, CidrBlock='10.0.0.0/24', AvailabilityZone=subnet_availability_zone)
    assert str(ex.exception).startswith(
        "An error occurred (InvalidParameterValue) when calling the CreateSubnet "
        "operation: Value ({}) for parameter availabilityZone is invalid. Subnets can currently only be created in the following availability zones: ".format(subnet_availability_zone))


@mock_ec2
def test_create_subnet_with_invalid_cidr_range():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    subnet_cidr_block = '10.1.0.0/20'
    with assert_raises(ClientError) as ex:
        subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
    str(ex.exception).should.equal(
        "An error occurred (InvalidSubnet.Range) when calling the CreateSubnet "
        "operation: The CIDR '{}' is invalid.".format(subnet_cidr_block))


@mock_ec2
def test_create_subnet_with_invalid_cidr_block_parameter():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    subnet_cidr_block = '1000.1.0.0/20'
    with assert_raises(ClientError) as ex:
        subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
    str(ex.exception).should.equal(
        "An error occurred (InvalidParameterValue) when calling the CreateSubnet "
        "operation: Value ({}) for parameter cidrBlock is invalid. This is not a valid CIDR block.".format(subnet_cidr_block))


@mock_ec2
def test_create_subnets_with_overlapping_cidr_blocks():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    subnet_cidr_block = '10.0.0.0/24'
    with assert_raises(ClientError) as ex:
        subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
        subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock=subnet_cidr_block)
    str(ex.exception).should.equal(
        "An error occurred (InvalidSubnet.Conflict) when calling the CreateSubnet "
        "operation: The CIDR '{}' conflicts with another subnet".format(subnet_cidr_block))
