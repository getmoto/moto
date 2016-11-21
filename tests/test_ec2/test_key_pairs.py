from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
import six
import sure  # noqa

from boto.exception import EC2ResponseError, JSONResponseError
from moto import mock_ec2


@mock_ec2
def test_key_pairs_empty():
    conn = boto.connect_ec2('the_key', 'the_secret')
    assert len(conn.get_all_key_pairs()) == 0


@mock_ec2
def test_key_pairs_invalid_id():
    conn = boto.connect_ec2('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_key_pairs('foo')
    cm.exception.code.should.equal('InvalidKeyPair.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_key_pairs_create():
    conn = boto.connect_ec2('the_key', 'the_secret')

    with assert_raises(JSONResponseError) as ex:
        kp = conn.create_key_pair('foo', dry_run=True)
    ex.exception.reason.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal('An error occurred (DryRunOperation) when calling the CreateKeyPair operation: Request would have succeeded, but DryRun flag is set')

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
    # on Python 3, these are reversed for some reason
    if six.PY3:
        return
    assert kps[0].name == 'foo'
    assert kps[1].name == 'bar'
    kps = conn.get_all_key_pairs('foo')
    assert len(kps) == 1
    assert kps[0].name == 'foo'


@mock_ec2
def test_key_pairs_create_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    kp = conn.create_key_pair('foo')
    assert kp.material.startswith('---- BEGIN RSA PRIVATE KEY ----')
    assert len(conn.get_all_key_pairs()) == 1

    with assert_raises(EC2ResponseError) as cm:
        conn.create_key_pair('foo')
    cm.exception.code.should.equal('InvalidKeyPair.Duplicate')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_key_pairs_delete_no_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    assert len(conn.get_all_key_pairs()) == 0
    r = conn.delete_key_pair('foo')
    r.should.be.ok


@mock_ec2
def test_key_pairs_delete_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.create_key_pair('foo')

    with assert_raises(JSONResponseError) as ex:
        r = conn.delete_key_pair('foo', dry_run=True)
    ex.exception.reason.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal('An error occurred (DryRunOperation) when calling the DeleteKeyPair operation: Request would have succeeded, but DryRun flag is set')

    r = conn.delete_key_pair('foo')
    r.should.be.ok
    assert len(conn.get_all_key_pairs()) == 0


@mock_ec2
def test_key_pairs_import():
    conn = boto.connect_ec2('the_key', 'the_secret')

    with assert_raises(JSONResponseError) as ex:
        kp = conn.import_key_pair('foo', b'content', dry_run=True)
    ex.exception.reason.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal('An error occurred (DryRunOperation) when calling the ImportKeyPair operation: Request would have succeeded, but DryRun flag is set')

    kp = conn.import_key_pair('foo', b'content')
    assert kp.name == 'foo'
    kps = conn.get_all_key_pairs()
    assert len(kps) == 1
    assert kps[0].name == 'foo'


@mock_ec2
def test_key_pairs_import_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    kp = conn.import_key_pair('foo', b'content')
    assert kp.name == 'foo'
    assert len(conn.get_all_key_pairs()) == 1

    with assert_raises(EC2ResponseError) as cm:
        conn.create_key_pair('foo')
    cm.exception.code.should.equal('InvalidKeyPair.Duplicate')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none
