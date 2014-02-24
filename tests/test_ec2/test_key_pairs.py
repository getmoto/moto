import boto
import sure  # noqa

from boto.exception import EC2ResponseError
from moto import mock_ec2


@mock_ec2
def test_key_pairs_empty():
    conn = boto.connect_ec2('the_key', 'the_secret')
    assert len(conn.get_all_key_pairs()) == 0


@mock_ec2
def test_key_pairs_create():
    conn = boto.connect_ec2('the_key', 'the_secret')
    kp = conn.create_key_pair('foo')
    assert kp.material.startswith('---- BEGIN RSA PRIVATE KEY ----')


@mock_ec2
def test_key_pairs_create_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    kp = conn.create_key_pair('foo')
    assert kp.material.startswith('---- BEGIN RSA PRIVATE KEY ----')
    # Call get_all_instances with a bad id should raise an error
    conn.create_key_pair.when.called_with('foo').should.throw(
        EC2ResponseError,
        "The keypair 'foo' already exists."
    )
