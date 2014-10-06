from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_create_and_describe_security_group():
    conn = boto.connect_ec2('the_key', 'the_secret')
    security_group = conn.create_security_group('test security group', 'this is a test security group')

    security_group.name.should.equal('test security group')
    security_group.description.should.equal('this is a test security group')

    # Trying to create another group with the same name should throw an error
    with assert_raises(EC2ResponseError) as cm:
        conn.create_security_group('test security group', 'this is a test security group')
    cm.exception.code.should.equal('InvalidGroup.Duplicate')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    all_groups = conn.get_all_security_groups()
    all_groups.should.have.length_of(1)
    all_groups[0].name.should.equal('test security group')


@mock_ec2
def test_create_security_group_without_description_raises_error():
    conn = boto.connect_ec2('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as cm:
        conn.create_security_group('test security group', '')
    cm.exception.code.should.equal('MissingParameter')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_create_and_describe_vpc_security_group():
    conn = boto.connect_ec2('the_key', 'the_secret')
    vpc_id = 'vpc-5300000c'
    security_group = conn.create_security_group('test security group', 'this is a test security group', vpc_id=vpc_id)

    security_group.vpc_id.should.equal(vpc_id)

    security_group.name.should.equal('test security group')
    security_group.description.should.equal('this is a test security group')

    # Trying to create another group with the same name in the same VPC should throw an error
    with assert_raises(EC2ResponseError) as cm:
        conn.create_security_group('test security group', 'this is a test security group', vpc_id)
    cm.exception.code.should.equal('InvalidGroup.Duplicate')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    all_groups = conn.get_all_security_groups()

    all_groups[0].vpc_id.should.equal(vpc_id)

    all_groups.should.have.length_of(1)
    all_groups[0].name.should.equal('test security group')


@mock_ec2
def test_create_two_security_groups_with_same_name_in_different_vpc():
    conn = boto.connect_ec2('the_key', 'the_secret')
    vpc_id = 'vpc-5300000c'
    vpc_id2 = 'vpc-5300000d'

    conn.create_security_group('test security group', 'this is a test security group', vpc_id)
    conn.create_security_group('test security group', 'this is a test security group', vpc_id2)

    all_groups = conn.get_all_security_groups()

    all_groups.should.have.length_of(2)
    all_groups[0].name.should.equal('test security group')
    all_groups[1].name.should.equal('test security group')


@mock_ec2
def test_deleting_security_groups():
    conn = boto.connect_ec2('the_key', 'the_secret')
    security_group1 = conn.create_security_group('test1', 'test1')
    conn.create_security_group('test2', 'test2')

    conn.get_all_security_groups().should.have.length_of(2)

    # Deleting a group that doesn't exist should throw an error
    with assert_raises(EC2ResponseError) as cm:
        conn.delete_security_group('foobar')
    cm.exception.code.should.equal('InvalidGroup.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Delete by name
    conn.delete_security_group('test2')
    conn.get_all_security_groups().should.have.length_of(1)

    # Delete by group id
    conn.delete_security_group(group_id=security_group1.id)
    conn.get_all_security_groups().should.have.length_of(0)


@mock_ec2
def test_delete_security_group_in_vpc():
    conn = boto.connect_ec2('the_key', 'the_secret')
    vpc_id = "vpc-12345"
    security_group1 = conn.create_security_group('test1', 'test1', vpc_id)

    # this should not throw an exception
    conn.delete_security_group(group_id=security_group1.id)


@mock_ec2
def test_authorize_ip_range_and_revoke():
    conn = boto.connect_ec2('the_key', 'the_secret')
    security_group = conn.create_security_group('test', 'test')

    success = security_group.authorize(ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.123/32")
    assert success.should.be.true

    security_group = conn.get_all_security_groups()[0]
    int(security_group.rules[0].to_port).should.equal(2222)
    security_group.rules[0].grants[0].cidr_ip.should.equal("123.123.123.123/32")

    # Wrong Cidr should throw error
    with assert_raises(EC2ResponseError) as cm:
        security_group.revoke(ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.122/32")
    cm.exception.code.should.equal('InvalidPermission.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Actually revoke
    security_group.revoke(ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.123/32")

    security_group = conn.get_all_security_groups()[0]
    security_group.rules.should.have.length_of(0)


@mock_ec2
def test_authorize_other_group_and_revoke():
    conn = boto.connect_ec2('the_key', 'the_secret')
    security_group = conn.create_security_group('test', 'test')
    other_security_group = conn.create_security_group('other', 'other')
    wrong_group = conn.create_security_group('wrong', 'wrong')

    success = security_group.authorize(ip_protocol="tcp", from_port="22", to_port="2222", src_group=other_security_group)
    assert success.should.be.true

    security_group = [group for group in conn.get_all_security_groups() if group.name == 'test'][0]
    int(security_group.rules[0].to_port).should.equal(2222)
    security_group.rules[0].grants[0].group_id.should.equal(other_security_group.id)

    # Wrong source group should throw error
    with assert_raises(EC2ResponseError) as cm:
        security_group.revoke(ip_protocol="tcp", from_port="22", to_port="2222", src_group=wrong_group)
    cm.exception.code.should.equal('InvalidPermission.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none

    # Actually revoke
    security_group.revoke(ip_protocol="tcp", from_port="22", to_port="2222", src_group=other_security_group)

    security_group = [group for group in conn.get_all_security_groups() if group.name == 'test'][0]
    security_group.rules.should.have.length_of(0)


@mock_ec2
def test_authorize_group_in_vpc():
    conn = boto.connect_ec2('the_key', 'the_secret')
    vpc_id = "vpc-12345"

    # create 2 groups in a vpc
    security_group = conn.create_security_group('test1', 'test1', vpc_id)
    other_security_group = conn.create_security_group('test2', 'test2', vpc_id)

    success = security_group.authorize(ip_protocol="tcp", from_port="22", to_port="2222", src_group=other_security_group)
    success.should.be.true

    # Check that the rule is accurate
    security_group = [group for group in conn.get_all_security_groups() if group.name == 'test1'][0]
    int(security_group.rules[0].to_port).should.equal(2222)
    security_group.rules[0].grants[0].group_id.should.equal(other_security_group.id)

    # Now revome the rule
    success = security_group.revoke(ip_protocol="tcp", from_port="22", to_port="2222", src_group=other_security_group)
    success.should.be.true

    # And check that it gets revoked
    security_group = [group for group in conn.get_all_security_groups() if group.name == 'test1'][0]
    security_group.rules.should.have.length_of(0)


@mock_ec2
def test_get_all_security_groups():
    conn = boto.connect_ec2()
    sg1 = conn.create_security_group(name='test1', description='test1', vpc_id='vpc-mjm05d27')
    sg2 = conn.create_security_group(name='test2', description='test2')

    resp = conn.get_all_security_groups(groupnames=['test1'])
    resp.should.have.length_of(1)
    resp[0].id.should.equal(sg1.id)

    resp = conn.get_all_security_groups(filters={'vpc-id': ['vpc-mjm05d27']})
    resp.should.have.length_of(1)
    resp[0].id.should.equal(sg1.id)

    resp = conn.get_all_security_groups(filters={'vpc_id': ['vpc-mjm05d27']})
    resp.should.have.length_of(1)
    resp[0].id.should.equal(sg1.id)

    resp = conn.get_all_security_groups(filters={'description': ['test1']})
    resp.should.have.length_of(1)
    resp[0].id.should.equal(sg1.id)

    resp = conn.get_all_security_groups()
    resp.should.have.length_of(2)


@mock_ec2
def test_authorize_bad_cidr_throws_invalid_parameter_value():
    conn = boto.connect_ec2('the_key', 'the_secret')
    security_group = conn.create_security_group('test', 'test')
    with assert_raises(EC2ResponseError) as cm:
        security_group.authorize(ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.123")
    cm.exception.code.should.equal('InvalidParameterValue')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none
