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
    kps = conn.get_all_key_pairs()
    assert len(kps) == 1
    assert kps[0].name == 'foo'


@mock_ec2
def test_key_pairs_create_two():
    conn = boto.connect_ec2('the_key', 'the_secret')
    kp = conn.create_key_pair('foo')
    kp = conn.create_key_pair('bar')
    assert kp.material.startswith('---- BEGIN RSA PRIVATE KEY ----')
    kps = conn.get_all_key_pairs()
    assert len(kps) == 2
    assert kps[0].name == 'foo'
    assert kps[1].name == 'bar'


@mock_ec2
def test_key_pairs_create_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    kp = conn.create_key_pair('foo')
    assert kp.material.startswith('---- BEGIN RSA PRIVATE KEY ----')
    assert len(conn.get_all_key_pairs()) == 1
    conn.create_key_pair.when.called_with('foo').should.throw(
        EC2ResponseError,
        "The keypair 'foo' already exists."
    )


@mock_ec2
def test_key_pairs_delete_no_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    assert len(conn.get_all_key_pairs()) == 0
    r = conn.delete_key_pair('foo')
    r.should.be.ok
