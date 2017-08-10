from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises  # flake8: noqa
from nose.tools import assert_raises

import boto3
import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2, mock_ec2_deprecated

SAMPLE_DOMAIN_NAME = u'example.com'
SAMPLE_NAME_SERVERS = [u'10.0.0.6', u'10.0.0.7']


@mock_ec2_deprecated
def test_vpcs():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    vpc.cidr_block.should.equal('10.0.0.0/16')

    all_vpcs = conn.get_all_vpcs()
    all_vpcs.should.have.length_of(2)

    vpc.delete()

    all_vpcs = conn.get_all_vpcs()
    all_vpcs.should.have.length_of(1)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_vpc("vpc-1234abcd")
    cm.exception.code.should.equal('InvalidVpcID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_vpc_defaults():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")

    conn.get_all_vpcs().should.have.length_of(2)
    conn.get_all_route_tables().should.have.length_of(2)
    conn.get_all_security_groups(
        filters={'vpc-id': [vpc.id]}).should.have.length_of(1)

    vpc.delete()

    conn.get_all_vpcs().should.have.length_of(1)
    conn.get_all_route_tables().should.have.length_of(1)
    conn.get_all_security_groups(
        filters={'vpc-id': [vpc.id]}).should.have.length_of(0)


@mock_ec2_deprecated
def test_vpc_isdefault_filter():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    conn.get_all_vpcs(filters={'isDefault': 'true'}).should.have.length_of(1)
    vpc.delete()
    conn.get_all_vpcs(filters={'isDefault': 'true'}).should.have.length_of(1)


@mock_ec2_deprecated
def test_multiple_vpcs_default_filter():
    conn = boto.connect_vpc('the_key', 'the_secret')
    conn.create_vpc("10.8.0.0/16")
    conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("192.168.0.0/16")
    conn.get_all_vpcs().should.have.length_of(4)
    vpc = conn.get_all_vpcs(filters={'isDefault': 'true'})
    vpc.should.have.length_of(1)
    vpc[0].cidr_block.should.equal('172.31.0.0/16')


@mock_ec2_deprecated
def test_vpc_state_available_filter():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.1.0.0/16")
    conn.get_all_vpcs(filters={'state': 'available'}).should.have.length_of(3)
    vpc.delete()
    conn.get_all_vpcs(filters={'state': 'available'}).should.have.length_of(2)


@mock_ec2_deprecated
def test_vpc_tagging():
    conn = boto.connect_vpc()
    vpc = conn.create_vpc("10.0.0.0/16")

    vpc.add_tag("a key", "some value")
    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the vpc
    vpc = conn.get_all_vpcs(vpc_ids=[vpc.id])[0]
    vpc.tags.should.have.length_of(1)
    vpc.tags["a key"].should.equal("some value")


@mock_ec2_deprecated
def test_vpc_get_by_id():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.0.0.0/16")

    vpcs = conn.get_all_vpcs(vpc_ids=[vpc1.id, vpc2.id])
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_cidr_block():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.0.0.0/24")

    vpcs = conn.get_all_vpcs(filters={'cidr': '10.0.0.0/16'})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_dhcp_options_id():
    conn = boto.connect_vpc()
    dhcp_options = conn.create_dhcp_options(
        SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.0.0.0/24")

    conn.associate_dhcp_options(dhcp_options.id, vpc1.id)
    conn.associate_dhcp_options(dhcp_options.id, vpc2.id)

    vpcs = conn.get_all_vpcs(filters={'dhcp-options-id': dhcp_options.id})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_tag():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    vpc3 = conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag('Name', 'TestVPC')
    vpc2.add_tag('Name', 'TestVPC')
    vpc3.add_tag('Name', 'TestVPC2')

    vpcs = conn.get_all_vpcs(filters={'tag:Name': 'TestVPC'})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_tag_key_superset():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    vpc3 = conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag('Name', 'TestVPC')
    vpc1.add_tag('Key', 'TestVPC2')
    vpc2.add_tag('Name', 'TestVPC')
    vpc2.add_tag('Key', 'TestVPC2')
    vpc3.add_tag('Key', 'TestVPC2')

    vpcs = conn.get_all_vpcs(filters={'tag-key': 'Name'})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_tag_key_subset():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    vpc3 = conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag('Name', 'TestVPC')
    vpc1.add_tag('Key', 'TestVPC2')
    vpc2.add_tag('Name', 'TestVPC')
    vpc2.add_tag('Key', 'TestVPC2')
    vpc3.add_tag('Test', 'TestVPC2')

    vpcs = conn.get_all_vpcs(filters={'tag-key': ['Name', 'Key']})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_tag_value_superset():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    vpc3 = conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag('Name', 'TestVPC')
    vpc1.add_tag('Key', 'TestVPC2')
    vpc2.add_tag('Name', 'TestVPC')
    vpc2.add_tag('Key', 'TestVPC2')
    vpc3.add_tag('Key', 'TestVPC2')

    vpcs = conn.get_all_vpcs(filters={'tag-value': 'TestVPC'})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_tag_value_subset():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag('Name', 'TestVPC')
    vpc1.add_tag('Key', 'TestVPC2')
    vpc2.add_tag('Name', 'TestVPC')
    vpc2.add_tag('Key', 'TestVPC2')

    vpcs = conn.get_all_vpcs(filters={'tag-value': ['TestVPC', 'TestVPC2']})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2
def test_default_vpc():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Create the default VPC
    default_vpc = list(ec2.vpcs.all())[0]
    default_vpc.cidr_block.should.equal('172.31.0.0/16')
    default_vpc.instance_tenancy.should.equal('default')
    default_vpc.reload()
    default_vpc.is_default.should.be.ok

    # Test default values for VPC attributes
    response = default_vpc.describe_attribute(Attribute='enableDnsSupport')
    attr = response.get('EnableDnsSupport')
    attr.get('Value').should.be.ok

    response = default_vpc.describe_attribute(Attribute='enableDnsHostnames')
    attr = response.get('EnableDnsHostnames')
    attr.get('Value').should.be.ok


@mock_ec2
def test_non_default_vpc():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Create the default VPC
    ec2.create_vpc(CidrBlock='172.31.0.0/16')

    # Create the non default VPC
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    # Test default instance_tenancy
    vpc.instance_tenancy.should.equal('default')

    # Test default values for VPC attributes
    response = vpc.describe_attribute(Attribute='enableDnsSupport')
    attr = response.get('EnableDnsSupport')
    attr.get('Value').should.be.ok

    response = vpc.describe_attribute(Attribute='enableDnsHostnames')
    attr = response.get('EnableDnsHostnames')
    attr.get('Value').shouldnt.be.ok


@mock_ec2
def test_vpc_dedicated_tenancy():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Create the default VPC
    ec2.create_vpc(CidrBlock='172.31.0.0/16')

    # Create the non default VPC
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16', InstanceTenancy='dedicated')
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    vpc.instance_tenancy.should.equal('dedicated')


@mock_ec2
def test_vpc_modify_enable_dns_support():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Create the default VPC
    ec2.create_vpc(CidrBlock='172.31.0.0/16')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')

    # Test default values for VPC attributes
    response = vpc.describe_attribute(Attribute='enableDnsSupport')
    attr = response.get('EnableDnsSupport')
    attr.get('Value').should.be.ok

    vpc.modify_attribute(EnableDnsSupport={'Value': False})

    response = vpc.describe_attribute(Attribute='enableDnsSupport')
    attr = response.get('EnableDnsSupport')
    attr.get('Value').shouldnt.be.ok


@mock_ec2
def test_vpc_modify_enable_dns_hostnames():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Create the default VPC
    ec2.create_vpc(CidrBlock='172.31.0.0/16')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')

    # Test default values for VPC attributes
    response = vpc.describe_attribute(Attribute='enableDnsHostnames')
    attr = response.get('EnableDnsHostnames')
    attr.get('Value').shouldnt.be.ok

    vpc.modify_attribute(EnableDnsHostnames={'Value': True})

    response = vpc.describe_attribute(Attribute='enableDnsHostnames')
    attr = response.get('EnableDnsHostnames')
    attr.get('Value').should.be.ok


@mock_ec2_deprecated
def test_vpc_associate_dhcp_options():
    conn = boto.connect_vpc()
    dhcp_options = conn.create_dhcp_options(
        SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    vpc = conn.create_vpc("10.0.0.0/16")

    conn.associate_dhcp_options(dhcp_options.id, vpc.id)

    vpc.update()
    dhcp_options.id.should.equal(vpc.dhcp_options_id)
