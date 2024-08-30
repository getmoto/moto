import datetime
import pickle

import boto3
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.x509
import pytest
from botocore.exceptions import ClientError
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509 import DNSName, NameOID

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID
from moto.core.utils import utcnow

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
@pytest.mark.parametrize(
    "region,partition", [("eu-west-1", "aws"), ("us-gov-east-1", "aws-us-gov")]
)
def test_create_certificate_authority(region, partition):
    client = boto3.client("acm-pca", region_name=region)
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
        f"arn:{partition}:acm-pca:{region}:{DEFAULT_ACCOUNT_ID}:certificate-authority/"
        in resp["CertificateAuthorityArn"]
    )


@mock_aws
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


@mock_aws
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


@mock_aws
def test_describe_unknown_certificate_authority():
    client = boto3.client("acm-pca", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.describe_certificate_authority(CertificateAuthorityArn="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
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

    # CA is not usable yet
    with pytest.raises(ClientError) as exc:
        client.get_certificate_authority_certificate(CertificateAuthorityArn=ca_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidStateException"
    assert (
        err["Message"]
        == f"The certificate authority {ca_arn} is not in the correct state to have a certificate signing request."
    )


@mock_aws
def test_get_certificate_authority_csr():
    client = boto3.client("acm-pca", region_name="us-east-2")
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {
                "CommonName": "evilcorp.com",
                "Country": "US",
                "State": "MA",
                "Organization": "Evil Corp",
                "OrganizationalUnit": "Finance",
            },
        },
        CertificateAuthorityType="ROOT",
        IdempotencyToken="terraform-20221125230308947400000001",
    )["CertificateAuthorityArn"]

    resp = client.get_certificate_authority_csr(CertificateAuthorityArn=ca_arn)

    assert "Csr" in resp
    csr = cryptography.x509.load_pem_x509_csr(resp["Csr"].encode("utf-8"))
    assert (
        csr.subject.get_attributes_for_oid(cryptography.x509.NameOID.COMMON_NAME)[
            0
        ].value
        == "evilcorp.com"
    )
    assert (
        csr.subject.get_attributes_for_oid(cryptography.x509.NameOID.COUNTRY_NAME)[
            0
        ].value
        == "US"
    )
    assert (
        csr.subject.get_attributes_for_oid(
            cryptography.x509.NameOID.STATE_OR_PROVINCE_NAME
        )[0].value
        == "MA"
    )
    assert (
        csr.subject.get_attributes_for_oid(cryptography.x509.NameOID.ORGANIZATION_NAME)[
            0
        ].value
        == "Evil Corp"
    )
    assert (
        csr.subject.get_attributes_for_oid(
            cryptography.x509.NameOID.ORGANIZATIONAL_UNIT_NAME
        )[0].value
        == "Finance"
    )


@mock_aws
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


@mock_aws
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


@mock_aws
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

    # test when `RevocationConfiguration` passed to request parameters
    client.update_certificate_authority(
        CertificateAuthorityArn=ca_arn,
        RevocationConfiguration={
            "CrlConfiguration": {
                "Enabled": True,
            }
        },
    )
    ca = client.describe_certificate_authority(CertificateAuthorityArn=ca_arn)[
        "CertificateAuthority"
    ]
    revocation_crl_conf = ca["RevocationConfiguration"]["CrlConfiguration"]
    assert revocation_crl_conf["Enabled"]
    assert (
        revocation_crl_conf["S3ObjectAcl"] == "PUBLIC_READ"
    )  # check if default value is applied.

    client.update_certificate_authority(
        CertificateAuthorityArn=ca_arn,
        RevocationConfiguration={
            "CrlConfiguration": {
                "Enabled": True,
                "S3ObjectAcl": "BUCKET_OWNER_FULL_CONTROL",
            }
        },
    )
    ca = client.describe_certificate_authority(CertificateAuthorityArn=ca_arn)[
        "CertificateAuthority"
    ]
    revocation_crl_conf = ca["RevocationConfiguration"]["CrlConfiguration"]
    assert (
        revocation_crl_conf["S3ObjectAcl"] == "BUCKET_OWNER_FULL_CONTROL"
    )  # check if the passed parameter is applied.

    # test when invald value passed for RevocationConfiguration.CrlConfiguration.S3ObjectAcl
    invalid_s3object_acl = "INVALID_VALUE"
    with pytest.raises(ClientError) as exc:
        client.update_certificate_authority(
            CertificateAuthorityArn=ca_arn,
            RevocationConfiguration={
                "CrlConfiguration": {
                    "Enabled": True,
                    "S3ObjectAcl": invalid_s3object_acl,
                }
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidS3ObjectAclInCrlConfiguration"
    assert (
        err["Message"]
        == f"Invalid value for parameter RevocationConfiguration.CrlConfiguration.S3ObjectAcl, value: {invalid_s3object_acl}, valid values: ['PUBLIC_READ', 'BUCKET_OWNER_FULL_CONTROL']"
    )


@mock_aws
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


@mock_aws
@pytest.mark.parametrize(
    "region,partition", [("ap-southeast-1", "aws"), ("us-gov-east-1", "aws-us-gov")]
)
def test_issue_certificate(region, partition):
    client = boto3.client("acm-pca", region_name=region)
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

    assert resp["CertificateArn"].startswith(
        f"arn:{partition}:acm-pca:{region}:{DEFAULT_ACCOUNT_ID}:certificate-authority"
    )


@mock_aws
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


@mock_aws
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

    with pytest.raises(ClientError) as exc:
        client.import_certificate_authority_certificate(
            CertificateAuthorityArn=ca_arn,
            Certificate="invalid certificate pem",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "MalformedCertificateAuthorityException"
    assert err["Message"] == "Malformed certificate."

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


@mock_aws
def test_end_entity_certificate_issuance():
    client = boto3.client("acm-pca", region_name="us-east-2")

    # Create a CA
    ca_arn = client.create_certificate_authority(
        CertificateAuthorityConfiguration={
            "KeyAlgorithm": "RSA_4096",
            "SigningAlgorithm": "SHA512WITHRSA",
            "Subject": {"CommonName": "evilcorp.com"},
        },
        CertificateAuthorityType="ROOT",
    )["CertificateAuthorityArn"]

    # Create CA certificate
    csr = client.get_certificate_authority_csr(CertificateAuthorityArn=ca_arn)["Csr"]
    certificate_arn = client.issue_certificate(
        CertificateAuthorityArn=ca_arn,
        Csr=csr,
        SigningAlgorithm="SHA256WITHRSA",
        TemplateArn="arn:aws:acm-pca:::template/RootCACertificate/V1",
        Validity={"Type": "YEARS", "Value": 10},
    )["CertificateArn"]

    resp = client.get_certificate(
        CertificateAuthorityArn=ca_arn, CertificateArn=certificate_arn
    )
    ca_cert = resp["Certificate"]

    client.import_certificate_authority_certificate(
        CertificateAuthorityArn=ca_arn,
        Certificate=ca_cert,
    )

    # Create a end-entity certificate and sign it by the CA
    private_key = cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key(
        public_exponent=65537, key_size=2048
    )
    ee_csr = create_csr(private_key, "US", "WA", "BezosCorp", "bezoscorp.com")
    ee_cert_arn = client.issue_certificate(
        CertificateAuthorityArn=ca_arn,
        Csr=ee_csr,
        SigningAlgorithm="SHA256WITHRSA",
        Validity={"Type": "YEARS", "Value": 1},
    )["CertificateArn"]
    ee_cert = client.get_certificate(
        CertificateAuthorityArn=ca_arn, CertificateArn=ee_cert_arn
    )["Certificate"]

    # Ensure that this is a valid single-hierarchy CA and all certificates are valid
    store = cryptography.x509.verification.Store(
        [cryptography.x509.load_pem_x509_certificate(ca_cert.encode("utf-8"))]
    )
    builder = cryptography.x509.verification.PolicyBuilder().store(store)
    verifier = builder.build_server_verifier(DNSName("bezoscorp.com"))
    chain = verifier.verify(
        cryptography.x509.load_pem_x509_certificate(ee_cert.encode("utf-8")), []
    )
    assert len(chain) == 2


@mock_aws
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


@mock_aws
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


@mock_aws
def test_acmpca_backend_is_serialisable():
    # This test ensures that the backend does not store any non-picklable objects (e.g. native OpenSSL objects)
    # This is important for downstream projects like LocalStack

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
    client.update_certificate_authority(
        CertificateAuthorityArn=ca_arn,
        Status="DISABLED",
    )

    csr = client.get_certificate_authority_csr(CertificateAuthorityArn=ca_arn)["Csr"]
    client.issue_certificate(
        CertificateAuthorityArn=ca_arn,
        Csr=csr,
        SigningAlgorithm="SHA512WITHRSA",
        Validity={"Type": "YEARS", "Value": 10},
    )
    client.describe_certificate_authority(CertificateAuthorityArn=ca_arn)

    from moto.acmpca import acmpca_backends

    assert pickle.dumps(acmpca_backends)


def create_csr(private_key, country, state, org, cn):
    csr = (
        cryptography.x509.CertificateSigningRequestBuilder()
        .subject_name(
            cryptography.x509.Name(
                [
                    cryptography.x509.NameAttribute(
                        cryptography.x509.NameOID.COUNTRY_NAME, country
                    ),
                    cryptography.x509.NameAttribute(
                        cryptography.x509.NameOID.STATE_OR_PROVINCE_NAME, state
                    ),
                    cryptography.x509.NameAttribute(
                        cryptography.x509.NameOID.ORGANIZATION_NAME, org
                    ),
                    cryptography.x509.NameAttribute(
                        cryptography.x509.NameOID.COMMON_NAME, cn
                    ),
                ]
            )
        )
        .add_extension(
            cryptography.x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )
    return csr.public_bytes(serialization.Encoding.PEM)


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
