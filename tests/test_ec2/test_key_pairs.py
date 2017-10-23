from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
import six
import sure  # noqa

from boto.exception import EC2ResponseError
from moto import mock_ec2_deprecated


@mock_ec2_deprecated
def test_key_pairs_empty():
    conn = boto.connect_ec2('the_key', 'the_secret')
    assert len(conn.get_all_key_pairs()) == 0


@mock_ec2_deprecated
def test_key_pairs_invalid_id():
    conn = boto.connect_ec2('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_key_pairs('foo')
    cm.exception.code.should.equal('InvalidKeyPair.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_key_pairs_create():
    conn = boto.connect_ec2('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as ex:
        kp = conn.create_key_pair('foo', dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the CreateKeyPair operation: Request would have succeeded, but DryRun flag is set')

    kp = conn.create_key_pair('foo')
    assert kp.material.startswith('---- BEGIN RSA PRIVATE KEY ----')
    kps = conn.get_all_key_pairs()
    assert len(kps) == 1
    assert kps[0].name == 'foo'


@mock_ec2_deprecated
def test_key_pairs_create_two():
    conn = boto.connect_ec2('the_key', 'the_secret')
    kp = conn.create_key_pair('foo')
    kp = conn.create_key_pair('bar')
    assert kp.material.startswith('---- BEGIN RSA PRIVATE KEY ----')
    kps = conn.get_all_key_pairs()
    kps.should.have.length_of(2)
    [i.name for i in kps].should.contain('foo')
    [i.name for i in kps].should.contain('bar')
    kps = conn.get_all_key_pairs('foo')
    kps.should.have.length_of(1)
    kps[0].name.should.equal('foo')


@mock_ec2_deprecated
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


@mock_ec2_deprecated
def test_key_pairs_delete_no_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    assert len(conn.get_all_key_pairs()) == 0
    r = conn.delete_key_pair('foo')
    r.should.be.ok


@mock_ec2_deprecated
def test_key_pairs_delete_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.create_key_pair('foo')

    with assert_raises(EC2ResponseError) as ex:
        r = conn.delete_key_pair('foo', dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the DeleteKeyPair operation: Request would have succeeded, but DryRun flag is set')

    r = conn.delete_key_pair('foo')
    r.should.be.ok
    assert len(conn.get_all_key_pairs()) == 0


@mock_ec2_deprecated
def test_key_pairs_import():
    conn = boto.connect_ec2('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as ex:
        kp = conn.import_key_pair('foo', b'content', dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the ImportKeyPair operation: Request would have succeeded, but DryRun flag is set')

    kp = conn.import_key_pair('foo', b'content')
    assert kp.name == 'foo'
    kps = conn.get_all_key_pairs()
    assert len(kps) == 1
    assert kps[0].name == 'foo'


@mock_ec2_deprecated
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


@mock_ec2_deprecated
def test_key_pair_filters():
    conn = boto.connect_ec2('the_key', 'the_secret')

    _ = conn.create_key_pair('kpfltr1')
    kp2 = conn.create_key_pair('kpfltr2')
    kp3 = conn.create_key_pair('kpfltr3')

    kp_by_name = conn.get_all_key_pairs(
        filters={'key-name': 'kpfltr2'})
    set([kp.name for kp in kp_by_name]
        ).should.equal(set([kp2.name]))

    kp_by_name = conn.get_all_key_pairs(
        filters={'fingerprint': kp3.fingerprint})
    set([kp.name for kp in kp_by_name]
        ).should.equal(set([kp3.name]))
