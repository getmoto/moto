import boto
import sure  # noqa

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
