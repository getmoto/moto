from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
import sure  # noqa

from boto.exception import EC2ResponseError
from moto import mock_ec2_deprecated

from .helpers import rsa_check_private_key


RSA_PUBLIC_KEY_OPENSSH = b"""\
ssh-rsa \
AAAAB3NzaC1yc2EAAAADAQABAAABAQDusXfgTE4eBP50NglSzCSEGnIL6+cr6m3H\
6cZANOQ+P1o/W4BdtcAL3sor4iGi7SOeJgo\8kweyMQrhrt6HaKGgromRiz37LQx\
4YIAcBi4Zd023mO/V7Rc2Chh18mWgLSmA6ng+j37ip6452zxtv0jHAz9pJolbKBp\
JzbZlPN45ZCTk9ck0fSVHRl6VRSSPQcpqi65XpRf+35zNOCGCc1mAOOTmw59Q2a6\
A3t8mL7r91aM5q6QOQm219lctFM8O7HRJnDgmhGpnjRwE1LyKktWTbgFZ4SNWU2X\
qusUO07jKuSxzPumXBeU+JEtx0J1tqZwJlpGt2R+0qN7nKnPl2+hx \
moto@github.com"""

RSA_PUBLIC_KEY_RFC4716 = b"""\
---- BEGIN SSH2 PUBLIC KEY ----
AAAAB3NzaC1yc2EAAAADAQABAAABAQDusXfgTE4eBP50NglSzCSEGnIL6+cr6m3H6cZANO
Q+P1o/W4BdtcAL3sor4iGi7SOeJgo8kweyMQrhrt6HaKGgromRiz37LQx4YIAcBi4Zd023
mO/V7Rc2Chh18mWgLSmA6ng+j37ip6452zxtv0jHAz9pJolbKBpJzbZlPN45ZCTk9ck0fS
VHRl6VRSSPQcpqi65XpRf+35zNOCGCc1mAOOTmw59Q2a6A3t8mL7r91aM5q6QOQm219lct
FM8O7HRJnDgmhGpnjRwE1LyKktWTbgFZ4SNWU2XqusUO07jKuSxzPumXBeU+JEtx0J1tqZ
wJlpGt2R+0qN7nKnPl2+hx
---- END SSH2 PUBLIC KEY ----
"""

RSA_PUBLIC_KEY_FINGERPRINT = "6a:49:07:1c:7e:bd:d2:bd:96:25:fe:b5:74:83:ae:fd"

DSA_PUBLIC_KEY_OPENSSH = b"""ssh-dss \
AAAAB3NzaC1kc3MAAACBAJ0aXctVwbN6VB81gpo8R7DUk8zXRjZvrkg8Y8vEGt63gklpNJNsLXtEUXkl5D4c0nD2FZO1rJNqFoe\
OQOCoGSfclHvt9w4yPl/lUEtb3Qtj1j80MInETHr19vaSunRk5R+M+8YH+LLcdYdz7MijuGey02mbi0H9K5nUIcuLMArVAAAAFQ\
D0RDvsObRWBlnaW8645obZBM86jwAAAIBNZwf3B4krIzAwVfkMHLDSdAvs7lOWE7o8SJLzr9t4a9HhYp9SLbMzJ815KWfidEYV2\
+s4ZaPCfcZ1GENFRbE8rixz5eMAjEUXEPMJkblDZTHzMsH96z2cOCQZ0vfOmgznsf18Uf725pqo9OqAioEsTJjX8jtI2qNPEBU0\
uhMSZQAAAIBBMGhDu5CWPUlS2QG7vzmzw81XasmHE/s2YPDRbolkriwlunpgwZhCscoQP8HFHY+DLUVvUb+GZwBmFt4l1uHl03b\
ffsm7UIHtCBYERr9Nx0u20ldfhkgB1lhaJb5o0ZJ3pmJ38KChfyHe5EUcqRdEFo89Mp72VI2Z6UHyL175RA== \
moto@github.com"""


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
        conn.create_key_pair('foo', dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the CreateKeyPair operation: Request would have succeeded, but DryRun flag is set')

    kp = conn.create_key_pair('foo')
    rsa_check_private_key(kp.material)

    kps = conn.get_all_key_pairs()
    assert len(kps) == 1
    assert kps[0].name == 'foo'


@mock_ec2_deprecated
def test_key_pairs_create_two():
    conn = boto.connect_ec2('the_key', 'the_secret')

    kp1 = conn.create_key_pair('foo')
    rsa_check_private_key(kp1.material)

    kp2 = conn.create_key_pair('bar')
    rsa_check_private_key(kp2.material)

    assert kp1.material != kp2.material

    kps = conn.get_all_key_pairs()
    kps.should.have.length_of(2)
    assert {i.name for i in kps} == {'foo', 'bar'}

    kps = conn.get_all_key_pairs('foo')
    kps.should.have.length_of(1)
    kps[0].name.should.equal('foo')


@mock_ec2_deprecated
def test_key_pairs_create_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.create_key_pair('foo')
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
        conn.import_key_pair('foo', RSA_PUBLIC_KEY_OPENSSH, dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the ImportKeyPair operation: Request would have succeeded, but DryRun flag is set')

    kp1 = conn.import_key_pair('foo', RSA_PUBLIC_KEY_OPENSSH)
    assert kp1.name == 'foo'
    assert kp1.fingerprint == RSA_PUBLIC_KEY_FINGERPRINT

    kp2 = conn.import_key_pair('foo2', RSA_PUBLIC_KEY_RFC4716)
    assert kp2.name == 'foo2'
    assert kp2.fingerprint == RSA_PUBLIC_KEY_FINGERPRINT

    kps = conn.get_all_key_pairs()
    assert len(kps) == 2
    assert kps[0].name == kp1.name
    assert kps[1].name == kp2.name


@mock_ec2_deprecated
def test_key_pairs_import_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    kp = conn.import_key_pair('foo', RSA_PUBLIC_KEY_OPENSSH)
    assert kp.name == 'foo'
    assert len(conn.get_all_key_pairs()) == 1

    with assert_raises(EC2ResponseError) as cm:
        conn.create_key_pair('foo')
    cm.exception.code.should.equal('InvalidKeyPair.Duplicate')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_key_pairs_invalid():
    conn = boto.connect_ec2('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as ex:
        conn.import_key_pair('foo', b'')
    ex.exception.error_code.should.equal('InvalidKeyPair.Format')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'Key is not in valid OpenSSH public key format')

    with assert_raises(EC2ResponseError) as ex:
        conn.import_key_pair('foo', b'garbage')
    ex.exception.error_code.should.equal('InvalidKeyPair.Format')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'Key is not in valid OpenSSH public key format')

    with assert_raises(EC2ResponseError) as ex:
        conn.import_key_pair('foo', DSA_PUBLIC_KEY_OPENSSH)
    ex.exception.error_code.should.equal('InvalidKeyPair.Format')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'Key is not in valid OpenSSH public key format')


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
