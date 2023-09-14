"""Unit tests for acmpca-supported APIs."""
import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_acmpca
from moto.core import DEFAULT_ACCOUNT_ID
from moto.core.utils import utcnow

import datetime
import cryptography.x509
from cryptography.x509 import NameOID
import cryptography.hazmat.primitives.asymmetric.rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_acmpca
def test_create_certificate_authority():
    client = boto3.client("acm-pca", region_name="eu-west-1")
    resp = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "yscb41lw.test"},
        },
        CertificateAuthorityType="SUBORDINATE",
        IdempotencyToken="terraform-20221125230308947400000001",
    )

    assert (
        f"arn:aws:acm-pca:eu-west-1:{DEFAULT_ACCOUNT_ID}:certificate-authority/"
        in resp["CertificateAuthorityArn"]
    )


@mock_acmpca
def test_describe_certificate_authority():
    client = boto3.client("acm-pca", region_name="ap-southeast-1")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "yscb41lw.test"},
        },
        CertificateAuthorityType="SUBORDINATE",
        IdempotencyToken="terraform-20221125230308947400000001",
    )["CertificateAuthorityArn"]
    ca = client.describe_certificate_authority(CertificateAuthorityArn=ca_arn)[
        "CertificateAuthority"
    ]

    assert ca["Arn"] == ca_arn
    assert ca["OwnerAccount"] == DEFAULT_ACCOUNT_ID
    assert "CreatedAt" in ca
    assert ca["Type"] == "SUBORDINATE"
    assert ca["Status"] == "PENDING_CERTIFICATE"
    assert ca["CertificateAuthorityConfiguration"] == {
        "KeyAlgorithm": "RSA_4096",
        "SigningAlgorithm": "SHA512WITHRSA",
        "Subject": {"CommonName": "yscb41lw.test"},
    }
    assert ca["KeyStorageSecurityStandard"] == "FIPS_140_2_LEVEL_3_OR_HIGHER"


@mock_acmpca
def test_describe_certificate_authority_with_security_standard():
    client = boto3.client("acm-pca", region_name="ap-southeast-1")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "yscb41lw.test"},
        },
        CertificateAuthorityType="SUBORDINATE",
        KeyStorageSecurityStandard="FIPS_140_2_LEVEL_2_OR_HIGHER",
        IdempotencyToken="terraform-20221125230308947400000001",
    )["CertificateAuthorityArn"]
    ca = client.describe_certificate_authority(CertificateAuthorityArn=ca_arn)[
        "CertificateAuthority"
    ]

    assert ca["Arn"] == ca_arn
    assert ca["OwnerAccount"] == DEFAULT_ACCOUNT_ID
    assert "CreatedAt" in ca
    assert ca["Type"] == "SUBORDINATE"
    assert ca["Status"] == "PENDING_CERTIFICATE"
    assert ca["CertificateAuthorityConfiguration"] == {
        "KeyAlgorithm": "RSA_4096",
        "SigningAlgorithm": "SHA512WITHRSA",
        "Subject": {"CommonName": "yscb41lw.test"},
    }
    assert ca["KeyStorageSecurityStandard"] == "FIPS_140_2_LEVEL_2_OR_HIGHER"


@mock_acmpca
def test_describe_unknown_certificate_authority():
    client = boto3.client("acm-pca", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.describe_certificate_authority(CertificateAuthorityArn="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_acmpca
def test_get_certificate_authority_certificate():
    client = boto3.client("acm-pca", region_name="ap-southeast-1")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "yscb41lw.test"},
        },
        CertificateAuthorityType="SUBORDINATE",
        IdempotencyToken="terraform-20221125230308947400000001",
    )["CertificateAuthorityArn"]

    resp = client.get_certificate_authority_certificate(CertificateAuthorityArn=ca_arn)

    # Certificate is empty for now,  until we call import_certificate_authority_certificate
    assert resp["Certificate"] == ""


@mock_acmpca
def test_get_certificate_authority_csr():
    client = boto3.client("acm-pca", region_name="us-east-2")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "yscb41lw.test"},
        },
        CertificateAuthorityType="SUBORDINATE",
        IdempotencyToken="terraform-20221125230308947400000001",
    )["CertificateAuthorityArn"]

    resp = client.get_certificate_authority_csr(CertificateAuthorityArn=ca_arn)

    assert "Csr" in resp


@mock_acmpca
def test_list_tags_when_ca_has_no_tags():
    client = boto3.client("acm-pca", region_name="us-east-2")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "yscb41lw.test"},
        },
        CertificateAuthorityType="SUBORDINATE",
        IdempotencyToken="terraform-20221125230308947400000001",
    )["CertificateAuthorityArn"]

    resp = client.list_tags(CertificateAuthorityArn=ca_arn)
    assert resp["Tags"] == []


@mock_acmpca
def test_list_tags():
    client = boto3.client("acm-pca", region_name="us-east-2")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "yscb41lw.test"},
        },
        CertificateAuthorityType="SUBORDINATE",
        IdempotencyToken="terraform-20221125230308947400000001",
        Tags=[{"Key": "t1", "Value": "v1"}, {"Key": "t2", "Value": "v2"}],
    )["CertificateAuthorityArn"]

    resp = client.list_tags(CertificateAuthorityArn=ca_arn)
    assert resp["Tags"] == [{"Key": "t1", "Value": "v1"}, {"Key": "t2", "Value": "v2"}]


@mock_acmpca
def test_update_certificate_authority():
    client = boto3.client("acm-pca", region_name="eu-west-1")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "yscb41lw.test"},
        },
        CertificateAuthorityType="SUBORDINATE",
    )["CertificateAuthorityArn"]

    client.update_certificate_authority(
        CertificateAuthorityArn=ca_arn,
        Status="DISABLED",
    )

    ca = client.describe_certificate_authority(CertificateAuthorityArn=ca_arn)[
        "CertificateAuthority"
    ]
    assert ca["Status"] == "DISABLED"
    assert "LastStateChangeAt" in ca


@mock_acmpca
def test_delete_certificate_authority():
    client = boto3.client("acm-pca", region_name="ap-southeast-1")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "yscb41lw.test"},
        },
        CertificateAuthorityType="SUBORDINATE",
    )["CertificateAuthorityArn"]

    client.delete_certificate_authority(CertificateAuthorityArn=ca_arn)

    ca = client.describe_certificate_authority(CertificateAuthorityArn=ca_arn)[
        "CertificateAuthority"
    ]
    assert ca["Status"] == "DELETED"


@mock_acmpca
def test_issue_certificate():
    client = boto3.client("acm-pca", region_name="ap-southeast-1")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "t8fzth32.test"},
        },
        CertificateAuthorityType="ROOT",
    )["CertificateAuthorityArn"]

    csr = client.get_certificate_authority_csr(CertificateAuthorityArn=ca_arn)["Csr"]

    resp = client.issue_certificate(
        CertificateAuthorityArn=ca_arn,
        Csr=csr,
        SigningAlgorithm="SHA512WITHRSA",
        Validity={"Type": "YEARS", "Value": 10},
    )

    assert "CertificateArn" in resp


@mock_acmpca
def test_get_certificate():
    client = boto3.client("acm-pca", region_name="us-east-2")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "t8fzth32.test"},
        },
        CertificateAuthorityType="ROOT",
    )["CertificateAuthorityArn"]

    csr = client.get_certificate_authority_csr(CertificateAuthorityArn=ca_arn)["Csr"]

    certificate_arn = client.issue_certificate(
        CertificateAuthorityArn=ca_arn,
        Csr=csr,
        SigningAlgorithm="SHA512WITHRSA",
        Validity={"Type": "YEARS", "Value": 10},
    )["CertificateArn"]

    resp = client.get_certificate(
        CertificateAuthorityArn=ca_arn, CertificateArn=certificate_arn
    )
    assert "Certificate" in resp


@mock_acmpca
def test_import_certificate_authority_certificate():
    client = boto3.client("acm-pca", region_name="eu-west-1")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "yscb41lw.test"},
        },
        CertificateAuthorityType="SUBORDINATE",
    )["CertificateAuthorityArn"]

    cert = create_cert()

    client.import_certificate_authority_certificate(
        CertificateAuthorityArn=ca_arn,
        Certificate=cert,
    )

    ca = client.describe_certificate_authority(CertificateAuthorityArn=ca_arn)[
        "CertificateAuthority"
    ]
    assert ca["Status"] == "ACTIVE"
    assert "NotBefore" in ca
    assert "NotAfter" in ca

    resp = client.get_certificate_authority_certificate(CertificateAuthorityArn=ca_arn)
    assert "-----BEGIN CERTIFICATE-----" in resp["Certificate"]


@mock_acmpca
def test_tag_certificate_authority():
    client = boto3.client("acm-pca", region_name="eu-west-1")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "yscb41lw.test"},
        },
        CertificateAuthorityType="SUBORDINATE",
    )["CertificateAuthorityArn"]

    client.tag_certificate_authority(
        CertificateAuthorityArn=ca_arn,
        Tags=[{"Key": "t1", "Value": "v1"}, {"Key": "t2", "Value": "v2"}],
    )

    resp = client.list_tags(CertificateAuthorityArn=ca_arn)
    assert resp["Tags"] == [{"Key": "t1", "Value": "v1"}, {"Key": "t2", "Value": "v2"}]


@mock_acmpca
def test_untag_certificate_authority():
    client = boto3.client("acm-pca", region_name="eu-west-1")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "yscb41lw.test"},
        },
        CertificateAuthorityType="SUBORDINATE",
    )["CertificateAuthorityArn"]

    client.tag_certificate_authority(
        CertificateAuthorityArn=ca_arn,
        Tags=[{"Key": "t1", "Value": "v1"}, {"Key": "t2", "Value": "v2"}],
    )

    client.untag_certificate_authority(
        CertificateAuthorityArn=ca_arn, Tags=[{"Key": "t1", "Value": "v1"}]
    )

    resp = client.list_tags(CertificateAuthorityArn=ca_arn)
    assert resp["Tags"] == [{"Key": "t2", "Value": "v2"}]


def create_cert():
    serial_number = cryptography.x509.random_serial_number()
    subject = cryptography.x509.Name(
        [
            cryptography.x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            cryptography.x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            cryptography.x509.NameAttribute(NameOID.LOCALITY_NAME, "Test Francisco"),
            cryptography.x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TestCompany"),
            cryptography.x509.NameAttribute(NameOID.COMMON_NAME, "testcert.io"),
        ]
    )
    issuer = cryptography.x509.Name(
        [  # C = US, O = Amazon, OU = Server CA 1B, CN = Amazon
            cryptography.x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            cryptography.x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Amazon"),
            cryptography.x509.NameAttribute(
                NameOID.ORGANIZATIONAL_UNIT_NAME, "Server CA 1B"
            ),
            cryptography.x509.NameAttribute(NameOID.COMMON_NAME, "TestCert"),
        ]
    )
    key = cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key(
        public_exponent=65537, key_size=2048
    )
    cert = (
        cryptography.x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(serial_number)
        .not_valid_before(utcnow() - datetime.timedelta(days=10))
        .not_valid_after(utcnow() + datetime.timedelta(days=10))
        .sign(key, hashes.SHA512(), default_backend())
    )

    return cert.public_bytes(serialization.Encoding.PEM)
