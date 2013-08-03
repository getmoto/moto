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
    conn.create_security_group.when.called_with('test security group', 'this is a test security group').should.throw(EC2ResponseError)

    all_groups = conn.get_all_security_groups()
    all_groups.should.have.length_of(1)
    all_groups[0].name.should.equal('test security group')


@mock_ec2
def test_deleting_security_groups():
    conn = boto.connect_ec2('the_key', 'the_secret')
    security_group1 = conn.create_security_group('test1', 'test1')
    conn.create_security_group('test2', 'test2')

    conn.get_all_security_groups().should.have.length_of(2)

    # Deleting a group that doesn't exist should throw an error
    conn.delete_security_group.when.called_with('foobar').should.throw(EC2ResponseError)

    # Delete by name
    conn.delete_security_group('test2')
    conn.get_all_security_groups().should.have.length_of(1)

    # Delete by group id
    conn.delete_security_group(security_group1.id)
    conn.get_all_security_groups().should.have.length_of(0)


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
    security_group.revoke.when.called_with(ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.122/32").should.throw(EC2ResponseError)

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
    security_group.revoke.when.called_with(ip_protocol="tcp", from_port="22", to_port="2222", src_group=wrong_group).should.throw(EC2ResponseError)

    # Actually revoke
    security_group.revoke(ip_protocol="tcp", from_port="22", to_port="2222", src_group=other_security_group)

    security_group = [group for group in conn.get_all_security_groups() if group.name == 'test'][0]
    security_group.rules.should.have.length_of(0)
