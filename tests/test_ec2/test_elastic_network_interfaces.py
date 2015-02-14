from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
import boto.cloudformation
import boto.ec2
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2, mock_cloudformation
from tests.helpers import requires_boto_gte
from tests.test_cloudformation.fixtures import vpc_eni
import json


@mock_ec2
def test_elastic_network_interfaces():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    eni = conn.create_network_interface(subnet.id)

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)
    eni = all_enis[0]
    eni.groups.should.have.length_of(0)
    eni.private_ip_addresses.should.have.length_of(0)

    conn.delete_network_interface(eni.id)

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(0)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_network_interface(eni.id)
    cm.exception.code.should.equal('InvalidNetworkInterfaceID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_elastic_network_interfaces_subnet_validation():
    conn = boto.connect_vpc('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as cm:
        conn.create_network_interface("subnet-abcd1234")
    cm.exception.code.should.equal('InvalidSubnetID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_elastic_network_interfaces_with_private_ip():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    private_ip = "54.0.0.1"
    eni = conn.create_network_interface(subnet.id, private_ip)

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)

    eni = all_enis[0]
    eni.groups.should.have.length_of(0)

    eni.private_ip_addresses.should.have.length_of(1)
    eni.private_ip_addresses[0].private_ip_address.should.equal(private_ip)


@mock_ec2
def test_elastic_network_interfaces_with_groups():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    security_group1 = conn.create_security_group('test security group #1', 'this is a test security group')
    security_group2 = conn.create_security_group('test security group #2', 'this is a test security group')
    conn.create_network_interface(subnet.id, groups=[security_group1.id, security_group2.id])

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)

    eni = all_enis[0]
    eni.groups.should.have.length_of(2)
    set([group.id for group in eni.groups]).should.equal(set([security_group1.id, security_group2.id]))


@requires_boto_gte("2.12.0")
@mock_ec2
def test_elastic_network_interfaces_modify_attribute():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    security_group1 = conn.create_security_group('test security group #1', 'this is a test security group')
    security_group2 = conn.create_security_group('test security group #2', 'this is a test security group')
    conn.create_network_interface(subnet.id, groups=[security_group1.id])

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)

    eni = all_enis[0]
    eni.groups.should.have.length_of(1)
    eni.groups[0].id.should.equal(security_group1.id)

    conn.modify_network_interface_attribute(eni.id, 'groupset', [security_group2.id])

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)

    eni = all_enis[0]
    eni.groups.should.have.length_of(1)
    eni.groups[0].id.should.equal(security_group2.id)


@mock_ec2
def test_elastic_network_interfaces_filtering():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    security_group1 = conn.create_security_group('test security group #1', 'this is a test security group')
    security_group2 = conn.create_security_group('test security group #2', 'this is a test security group')

    eni1 = conn.create_network_interface(subnet.id, groups=[security_group1.id, security_group2.id])
    eni2 = conn.create_network_interface(subnet.id, groups=[security_group1.id])
    eni3 = conn.create_network_interface(subnet.id)

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(3)

    # Filter by NetworkInterfaceId
    enis_by_id = conn.get_all_network_interfaces([eni1.id])
    enis_by_id.should.have.length_of(1)
    set([eni.id for eni in enis_by_id]).should.equal(set([eni1.id]))

    # Filter by ENI ID
    enis_by_id = conn.get_all_network_interfaces(filters={'network-interface-id': eni1.id})
    enis_by_id.should.have.length_of(1)
    set([eni.id for eni in enis_by_id]).should.equal(set([eni1.id]))

    # Filter by Security Group
    enis_by_group = conn.get_all_network_interfaces(filters={'group-id':security_group1.id})
    enis_by_group.should.have.length_of(2)
    set([eni.id for eni in enis_by_group]).should.equal(set([eni1.id, eni2.id]))

    # Filter by ENI ID and Security Group
    enis_by_group = conn.get_all_network_interfaces(filters={'network-interface-id': eni1.id, 'group-id': security_group1.id})
    enis_by_group.should.have.length_of(1)
    set([eni.id for eni in enis_by_group]).should.equal(set([eni1.id]))

    # Unsupported filter
    conn.get_all_network_interfaces.when.called_with(filters={'not-implemented-filter': 'foobar'}).should.throw(NotImplementedError)


@mock_ec2
@mock_cloudformation
def test_elastic_network_interfaces_cloudformation():
    template = vpc_eni.template
    template_json = json.dumps(template)
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack(
        "test_stack",
        template_body=template_json,
    )
    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    eni = ec2_conn.get_all_network_interfaces()[0]

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    cfn_eni = [resource for resource in resources if resource.resource_type == 'AWS::EC2::NetworkInterface'][0]
    cfn_eni.physical_resource_id.should.equal(eni.id)
