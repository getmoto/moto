import boto
from boto.exception import EC2ResponseError
from sure import expect

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
    security_group2 = conn.create_security_group('test2', 'test2')

    conn.get_all_security_groups().should.have.length_of(2)

    # Deleting a group that doesn't exist should throw an error
    conn.delete_security_group.when.called_with('foobar').should.throw(EC2ResponseError)

    # Delete by name
    conn.delete_security_group('test2')
    conn.get_all_security_groups().should.have.length_of(1)

    # Delete by group id
    conn.delete_security_group(security_group1.id)
    conn.get_all_security_groups().should.have.length_of(0)
