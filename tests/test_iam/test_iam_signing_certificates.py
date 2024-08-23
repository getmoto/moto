from datetime import timedelta

import boto3
import cryptography
import pytest
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import Name, NameAttribute
from cryptography.x509.oid import NameOID

from moto.core.utils import utcnow
from tests.test_iam import iam_aws_verified


@iam_aws_verified(create_user=True)
@pytest.mark.aws_verified
def test_signing_certs(user_name=None):
    client = boto3.client("iam", region_name="us-east-1")
    certificate = create_certificate()

    # Upload the cert:
    resp = client.upload_signing_certificate(
        UserName=user_name, CertificateBody=certificate
    )["Certificate"]
    cert_id = resp["CertificateId"]

    assert resp["UserName"] == user_name
    assert resp["Status"] == "Active"
    assert resp["CertificateBody"] == certificate
    assert resp["CertificateId"]

    # Update:
    client.update_signing_certificate(
        UserName=user_name, CertificateId=cert_id, Status="Inactive"
    )

    # List the certs:
    resp = client.list_signing_certificates(UserName=user_name)["Certificates"]
    assert len(resp) == 1
    assert resp[0]["CertificateBody"] == certificate
    assert resp[0]["Status"] == "Inactive"  # Changed with the update call above.

    # Delete:
    client.delete_signing_certificate(UserName=user_name, CertificateId=cert_id)


@iam_aws_verified(create_user=True)
@pytest.mark.aws_verified
def test_create_too_many_certificates(user_name=None):
    client = boto3.client("iam", region_name="us-east-1")
    certificate1 = create_certificate()
    certificate2 = create_certificate()
    certificate3 = create_certificate()

    # Upload two certs
    cert_id1 = client.upload_signing_certificate(
        UserName=user_name, CertificateBody=certificate1
    )["Certificate"]["CertificateId"]
    cert_id2 = client.upload_signing_certificate(
        UserName=user_name, CertificateBody=certificate2
    )["Certificate"]["CertificateId"]
    assert cert_id1 != cert_id2

    # Verify that a third certificate exceeds the limit
    with pytest.raises(ClientError) as exc:
        client.upload_signing_certificate(
            UserName=user_name, CertificateBody=certificate3
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "LimitExceeded"
    assert err["Message"] == "Cannot exceed quota for CertificatesPerUser: 2"


@iam_aws_verified(create_user=True)
def test_retrieve_cert_details_using_credentials_report(user_name=None):
    """
    AWS caches the Credentials Report for 4 hours
    Once you generate the report, you can request the report over and over again, but you'll always get that same report back in the next 4 hours
    # That makes it slightly impossible to verify this against AWS - that's why there is no `aws_verified`-marker
    """
    client = boto3.client("iam", region_name="us-east-1")
    certificate1 = create_certificate()
    certificate2 = create_certificate()

    # Upload the cert:
    cert_id1 = client.upload_signing_certificate(
        UserName=user_name, CertificateBody=certificate1
    )["Certificate"]["CertificateId"]

    result = client.generate_credential_report()
    while result["State"] != "COMPLETE":
        result = client.generate_credential_report()
    report = client.get_credential_report()["Content"].decode("utf-8")

    our_line = next(line for line in report.split("\n") if line.startswith(user_name))
    cert1_active = our_line.split(",")[-4]
    assert cert1_active == "true"
    cert2_active = our_line.split(",")[-2]
    assert cert2_active == "false"

    client.upload_signing_certificate(UserName=user_name, CertificateBody=certificate2)

    result = client.generate_credential_report()
    while result["State"] != "COMPLETE":
        result = client.generate_credential_report()
    report = client.get_credential_report()["Content"].decode("utf-8")
    our_line = next(line for line in report.split("\n") if line.startswith(user_name))

    cert1_active = our_line.split(",")[-4]
    assert cert1_active == "true"
    cert2_active = our_line.split(",")[-2]
    assert cert2_active == "true"

    # Set Certificate to Inactive
    client.update_signing_certificate(
        UserName=user_name, CertificateId=cert_id1, Status="Inactive"
    )

    # Verify the credential report is updated
    result = client.generate_credential_report()
    while result["State"] != "COMPLETE":
        result = client.generate_credential_report()
    report = client.get_credential_report()["Content"].decode("utf-8")
    our_line = next(line for line in report.split("\n") if line.startswith(user_name))

    cert1_active = our_line.split(",")[-4]
    assert cert1_active == "false"
    cert2_active = our_line.split(",")[-2]
    assert cert2_active == "true"


@iam_aws_verified()
@pytest.mark.aws_verified
def test_upload_cert_for_unknown_user(user_name=None):
    client = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.upload_signing_certificate(
            UserName="notauser", CertificateBody=create_certificate()
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == "The user with name notauser cannot be found."

    with pytest.raises(ClientError) as exc:
        client.update_signing_certificate(
            UserName="notauser",
            CertificateId="asdfasdfasdfasdfasdfasdfasdasdf",
            Status="Inactive",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == "The user with name notauser cannot be found."

    with pytest.raises(ClientError) as exc:
        client.list_signing_certificates(UserName="notauser")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == "The user with name notauser cannot be found."

    with pytest.raises(ClientError):
        client.delete_signing_certificate(UserName="notauser", CertificateId="x" * 32)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == "The user with name notauser cannot be found."


@iam_aws_verified(create_user=True)
@pytest.mark.aws_verified
def test_upload_invalid_certificate(user_name=None):
    client = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as ce:
        client.upload_signing_certificate(
            UserName=user_name, CertificateBody="notacert"
        )
    assert ce.value.response["Error"]["Code"] == "MalformedCertificate"


@iam_aws_verified(create_user=True)
@pytest.mark.aws_verified
def test_update_unknown_certificate(user_name=None):
    client = boto3.client("iam", region_name="us-east-1")
    fake_id_name = "x" * 32
    with pytest.raises(ClientError) as ce:
        client.update_signing_certificate(
            UserName=user_name, CertificateId=fake_id_name, Status="Inactive"
        )
    err = ce.value.response["Error"]

    assert err["Message"] == f"The Certificate with id {fake_id_name} cannot be found."


def create_certificate():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2028)
    cert_subject = [NameAttribute(NameOID.COMMON_NAME, "iam.amazonaws.com")]
    issuer = [
        NameAttribute(NameOID.COUNTRY_NAME, "US"),
        NameAttribute(NameOID.ORGANIZATION_NAME, "Amazon"),
        NameAttribute(NameOID.COMMON_NAME, "Amazon RSA 2048 M01"),
    ]
    cert = (
        cryptography.x509.CertificateBuilder()
        .subject_name(Name(cert_subject))
        .issuer_name(Name(issuer))
        .public_key(key.public_key())
        .serial_number(cryptography.x509.random_serial_number())
        .not_valid_before(utcnow())
        .not_valid_after(utcnow() + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
