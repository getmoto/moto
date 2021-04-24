from __future__ import unicode_literals

import pytest

import boto
import boto3
import sure  # noqa

from boto.exception import EC2ResponseError
from botocore.exceptions import ClientError
from moto import mock_ec2, mock_ec2_deprecated

from .helpers import rsa_check_private_key


RSA_PUBLIC_KEY_OPENSSH = b"""\
ssh-rsa \
AAAAB3NzaC1yc2EAAAADAQABAAABAQDusXfgTE4eBP50NglSzCSEGnIL6+cr6m3H\
6cZANOQ+P1o/W4BdtcAL3sor4iGi7SOeJgo\\8kweyMQrhrt6HaKGgromRiz37LQx\
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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_key_pairs_empty():
    conn = boto.connect_ec2("the_key", "the_secret")
    assert len(conn.get_all_key_pairs()) == 0


@mock_ec2
def test_key_pairs_empty_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    client.describe_key_pairs()["KeyPairs"].should.be.empty


# Has boto3 equivalent
@mock_ec2_deprecated
def test_key_pairs_invalid_id():
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_key_pairs("foo")
    cm.value.code.should.equal("InvalidKeyPair.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_key_pairs_invalid_id_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    with pytest.raises(ClientError) as ex:
        client.describe_key_pairs(KeyNames=["foo"])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidKeyPair.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_key_pairs_create():
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as ex:
        conn.create_key_pair("foo", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateKeyPair operation: Request would have succeeded, but DryRun flag is set"
    )

    kp = conn.create_key_pair("foo")
    rsa_check_private_key(kp.material)

    kps = conn.get_all_key_pairs()
    assert len(kps) == 1
    assert kps[0].name == "foo"


# Has boto3 equivalent
@mock_ec2_deprecated
def test_key_pairs_create_two():
    conn = boto.connect_ec2("the_key", "the_secret")

    kp1 = conn.create_key_pair("foo")
    rsa_check_private_key(kp1.material)

    kp2 = conn.create_key_pair("bar")
    rsa_check_private_key(kp2.material)

    assert kp1.material != kp2.material

    kps = conn.get_all_key_pairs()
    kps.should.have.length_of(2)
    assert {i.name for i in kps} == {"foo", "bar"}

    kps = conn.get_all_key_pairs("foo")
    kps.should.have.length_of(1)
    kps[0].name.should.equal("foo")


@mock_ec2
def test_key_pairs_create_dryrun_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")

    with pytest.raises(ClientError) as ex:
        ec2.create_key_pair(KeyName="foo", DryRun=True)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateKeyPair operation: Request would have succeeded, but DryRun flag is set"
    )


@mock_ec2
def test_key_pairs_create_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    kp = ec2.create_key_pair(KeyName="foo")
    rsa_check_private_key(kp.key_material)
    # Verify the client can create a key_pair as well - should behave the same
    kp2 = client.create_key_pair(KeyName="foo2")
    rsa_check_private_key(kp2["KeyMaterial"])

    kp.key_material.shouldnt.equal(kp2["KeyMaterial"])

    kps = client.describe_key_pairs()["KeyPairs"]
    kps.should.have.length_of(2)
    set([k["KeyName"] for k in kps]).should.equal(set(["foo", "foo2"]))

    kps = client.describe_key_pairs(KeyNames=["foo"])["KeyPairs"]
    kps.should.have.length_of(1)
    kps[0].should.have.key("KeyName").equal("foo")
    kps[0].should.have.key("KeyFingerprint")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_key_pairs_create_exist():
    conn = boto.connect_ec2("the_key", "the_secret")
    conn.create_key_pair("foo")
    assert len(conn.get_all_key_pairs()) == 1

    with pytest.raises(EC2ResponseError) as cm:
        conn.create_key_pair("foo")
    cm.value.code.should.equal("InvalidKeyPair.Duplicate")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_key_pairs_create_exist_boto3():
    client = boto3.client("ec2", "us-west-1")
    client.create_key_pair(KeyName="foo")

    with pytest.raises(ClientError) as ex:
        client.create_key_pair(KeyName="foo")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidKeyPair.Duplicate")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_key_pairs_delete_no_exist():
    conn = boto.connect_ec2("the_key", "the_secret")
    assert len(conn.get_all_key_pairs()) == 0
    r = conn.delete_key_pair("foo")
    r.should.be.ok


@mock_ec2
def test_key_pairs_delete_no_exist_boto3():
    client = boto3.client("ec2", "us-west-1")
    client.describe_key_pairs()["KeyPairs"].should.have.length_of(0)
    client.delete_key_pair(KeyName="non-existing")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_key_pairs_delete_exist():
    conn = boto.connect_ec2("the_key", "the_secret")
    conn.create_key_pair("foo")

    with pytest.raises(EC2ResponseError) as ex:
        r = conn.delete_key_pair("foo", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteKeyPair operation: Request would have succeeded, but DryRun flag is set"
    )

    r = conn.delete_key_pair("foo")
    r.should.be.ok
    assert len(conn.get_all_key_pairs()) == 0


@mock_ec2
def test_key_pairs_delete_exist_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    client.create_key_pair(KeyName="foo")

    with pytest.raises(ClientError) as ex:
        client.delete_key_pair(KeyName="foo", DryRun=True)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteKeyPair operation: Request would have succeeded, but DryRun flag is set"
    )

    client.delete_key_pair(KeyName="foo")
    client.describe_key_pairs()["KeyPairs"].should.equal([])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_key_pairs_import():
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as ex:
        conn.import_key_pair("foo", RSA_PUBLIC_KEY_OPENSSH, dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the ImportKeyPair operation: Request would have succeeded, but DryRun flag is set"
    )

    kp1 = conn.import_key_pair("foo", RSA_PUBLIC_KEY_OPENSSH)
    assert kp1.name == "foo"
    assert kp1.fingerprint == RSA_PUBLIC_KEY_FINGERPRINT

    kp2 = conn.import_key_pair("foo2", RSA_PUBLIC_KEY_RFC4716)
    assert kp2.name == "foo2"
    assert kp2.fingerprint == RSA_PUBLIC_KEY_FINGERPRINT

    kps = conn.get_all_key_pairs()
    assert len(kps) == 2
    assert kps[0].name == kp1.name
    assert kps[1].name == kp2.name


@mock_ec2
def test_key_pairs_import_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    with pytest.raises(ClientError) as ex:
        client.import_key_pair(
            KeyName="foo", PublicKeyMaterial=RSA_PUBLIC_KEY_OPENSSH, DryRun=True
        )
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the ImportKeyPair operation: Request would have succeeded, but DryRun flag is set"
    )

    kp1 = client.import_key_pair(
        KeyName="foo", PublicKeyMaterial=RSA_PUBLIC_KEY_OPENSSH
    )
    print(kp1)
    kp1.should.have.key("KeyName").equal("foo")
    kp1.should.have.key("KeyFingerprint").equal(RSA_PUBLIC_KEY_FINGERPRINT)

    kp2 = client.import_key_pair(
        KeyName="foo2", PublicKeyMaterial=RSA_PUBLIC_KEY_RFC4716
    )
    kp2.should.have.key("KeyName").equal("foo2")
    kp2.should.have.key("KeyFingerprint").equal(RSA_PUBLIC_KEY_FINGERPRINT)

    kps = client.describe_key_pairs()["KeyPairs"]
    kps.should.have.length_of(2)
    kps[0]["KeyName"].should.equal(kp1["KeyName"])
    kps[1]["KeyName"].should.equal(kp2["KeyName"])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_key_pairs_import_exist():
    conn = boto.connect_ec2("the_key", "the_secret")
    kp = conn.import_key_pair("foo", RSA_PUBLIC_KEY_OPENSSH)
    assert kp.name == "foo"
    assert len(conn.get_all_key_pairs()) == 1

    with pytest.raises(EC2ResponseError) as cm:
        conn.create_key_pair("foo")
    cm.value.code.should.equal("InvalidKeyPair.Duplicate")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_key_pairs_import_exist_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    kp = client.import_key_pair(KeyName="foo", PublicKeyMaterial=RSA_PUBLIC_KEY_OPENSSH)
    kp["KeyName"].should.equal("foo")
    client.describe_key_pairs()["KeyPairs"].should.have.length_of(1)

    with pytest.raises(ClientError) as ex:
        client.create_key_pair(KeyName="foo")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidKeyPair.Duplicate")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_key_pairs_invalid():
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as ex:
        conn.import_key_pair("foo", b"")
    ex.value.error_code.should.equal("InvalidKeyPair.Format")
    ex.value.status.should.equal(400)
    ex.value.message.should.equal("Key is not in valid OpenSSH public key format")

    with pytest.raises(EC2ResponseError) as ex:
        conn.import_key_pair("foo", b"garbage")
    ex.value.error_code.should.equal("InvalidKeyPair.Format")
    ex.value.status.should.equal(400)
    ex.value.message.should.equal("Key is not in valid OpenSSH public key format")

    with pytest.raises(EC2ResponseError) as ex:
        conn.import_key_pair("foo", DSA_PUBLIC_KEY_OPENSSH)
    ex.value.error_code.should.equal("InvalidKeyPair.Format")
    ex.value.status.should.equal(400)
    ex.value.message.should.equal("Key is not in valid OpenSSH public key format")


@mock_ec2
def test_key_pairs_invalid_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    with pytest.raises(ClientError) as ex:
        client.import_key_pair(KeyName="foo", PublicKeyMaterial=b"")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidKeyPair.Format")
    err["Message"].should.equal("Key is not in valid OpenSSH public key format")

    with pytest.raises(ClientError) as ex:
        client.import_key_pair(KeyName="foo", PublicKeyMaterial=b"garbage")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidKeyPair.Format")
    err["Message"].should.equal("Key is not in valid OpenSSH public key format")

    with pytest.raises(ClientError) as ex:
        client.import_key_pair(KeyName="foo", PublicKeyMaterial=DSA_PUBLIC_KEY_OPENSSH)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidKeyPair.Format")
    err["Message"].should.equal("Key is not in valid OpenSSH public key format")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_key_pair_filters():
    conn = boto.connect_ec2("the_key", "the_secret")

    _ = conn.create_key_pair("kpfltr1")
    kp2 = conn.create_key_pair("kpfltr2")
    kp3 = conn.create_key_pair("kpfltr3")

    kp_by_name = conn.get_all_key_pairs(filters={"key-name": "kpfltr2"})
    set([kp.name for kp in kp_by_name]).should.equal(set([kp2.name]))

    kp_by_name = conn.get_all_key_pairs(filters={"fingerprint": kp3.fingerprint})
    set([kp.name for kp in kp_by_name]).should.equal(set([kp3.name]))


@mock_ec2
def test_key_pair_filters_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    _ = ec2.create_key_pair(KeyName="kpfltr1")
    kp2 = ec2.create_key_pair(KeyName="kpfltr2")
    kp3 = ec2.create_key_pair(KeyName="kpfltr3")

    kp_by_name = client.describe_key_pairs(
        Filters=[{"Name": "key-name", "Values": ["kpfltr2"]}]
    )["KeyPairs"]
    set([kp["KeyName"] for kp in kp_by_name]).should.equal(set([kp2.name]))

    kp_by_name = client.describe_key_pairs(
        Filters=[{"Name": "fingerprint", "Values": [kp3.key_fingerprint]}]
    )["KeyPairs"]
    set([kp["KeyName"] for kp in kp_by_name]).should.equal(set([kp3.name]))
