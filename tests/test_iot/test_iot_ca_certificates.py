from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings


@mock_aws
def test_register_ca_certificate_simple_invalid_cert():
    """
    Original test case with invalid cert.
    """
    client = boto3.client("iot", region_name="us-east-1")

    resp = client.register_ca_certificate(
        caCertificate="ca_certificate",
        verificationCertificate="verification_certificate",
    )

    assert "certificateArn" in resp
    assert "certificateId" in resp


@pytest.fixture(name="make_cert")
@mock_aws(config={"iot": {"use_valid_cert": True}})
def fixture_make_cert():
    """
    Create a valid cert for testing
    """
    client = boto3.client("iot", region_name="us-east-1")
    return client.create_keys_and_certificate(setAsActive=False)


@mock_aws(config={"iot": {"use_valid_cert": True}})
def test_register_ca_certificate_simple(make_cert):
    if not settings.TEST_DECORATOR_MODE:
        # Technically it doesn't have to be skipped
        # in ServerMode the config is not set, so we'll compute the cert the old/invalid way
        # But there are no assertions to actually verify the value of the computed cert
        # This is just added here as a warning/reminder if this ever changes
        raise SkipTest("Config cannot be easily set in ServerMode")

    client = boto3.client("iot", region_name="us-east-1")
    certInfo = make_cert

    resp = client.register_ca_certificate(
        caCertificate=certInfo["certificatePem"],
        verificationCertificate="verification_certificate",
    )

    assert "certificateArn" in resp
    assert "certificateId" in resp
    assert resp["certificateId"] == certInfo["certificateId"]


@mock_aws
def test_describe_ca_certificate_unknown():
    client = boto3.client("iot", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.describe_ca_certificate(certificateId="a" * 70)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_describe_ca_certificate_simple():
    client = boto3.client("iot", region_name="us-east-1")

    resp = client.register_ca_certificate(
        caCertificate="ca_certificate",
        verificationCertificate="verification_certificate",
    )

    describe = client.describe_ca_certificate(certificateId=resp["certificateId"])

    assert "certificateDescription" in describe
    description = describe["certificateDescription"]
    assert description["certificateArn"] == resp["certificateArn"]
    assert description["certificateId"] == resp["certificateId"]
    assert description["status"] == "INACTIVE"
    assert description["certificatePem"] == "ca_certificate"


@mock_aws
def test_describe_ca_certificate_advanced():
    client = boto3.client("iot", region_name="us-east-1")

    resp = client.register_ca_certificate(
        caCertificate="ca_certificate",
        verificationCertificate="verification_certificate",
        setAsActive=True,
        registrationConfig={
            "templateBody": "template_b0dy",
            "roleArn": "aws:iot:arn:role/asdfqwerwe",
        },
    )

    describe = client.describe_ca_certificate(certificateId=resp["certificateId"])

    description = describe["certificateDescription"]
    assert description["certificateArn"] == resp["certificateArn"]
    assert description["certificateId"] == resp["certificateId"]
    assert description["status"] == "ACTIVE"
    assert description["certificatePem"] == "ca_certificate"

    config = describe["registrationConfig"]
    assert config["templateBody"] == "template_b0dy"
    assert config["roleArn"] == "aws:iot:arn:role/asdfqwerwe"


@mock_aws
def test_list_certificates_by_ca():
    """
    test listing certificates by CA.  Don't use valid cert to make it simpler
    for the test.
    """
    client = boto3.client("iot", region_name="us-east-1")

    # create ca
    ca_cert = client.register_ca_certificate(
        caCertificate="ca_certificate",
        verificationCertificate="verification_certificate",
    )
    ca_cert_id = ca_cert["certificateId"]

    # list certificates should be empty at first
    certs = client.list_certificates_by_ca(caCertificateId=ca_cert_id)
    assert certs["certificates"] == []

    # create one certificate
    cert1 = client.register_certificate(
        certificatePem="pem" * 20, caCertificatePem="ca_certificate", setAsActive=False
    )

    # list certificates should return this
    certs = client.list_certificates_by_ca(caCertificateId=ca_cert_id)
    assert len(certs["certificates"]) == 1
    assert certs["certificates"][0]["certificateId"] == cert1["certificateId"]

    # create another certificate, without ca
    client.register_certificate(
        certificatePem="pam" * 20,
        caCertificatePem="unknown_ca_certificate",
        setAsActive=False,
    )

    # list certificate should still only return the first certificate
    certs = client.list_certificates_by_ca(caCertificateId=ca_cert_id)
    assert len(certs["certificates"]) == 1


@mock_aws
def test_delete_ca_certificate():
    client = boto3.client("iot", region_name="us-east-1")

    cert_id = client.register_ca_certificate(
        caCertificate="ca_certificate",
        verificationCertificate="verification_certificate",
    )["certificateId"]

    client.delete_ca_certificate(certificateId=cert_id)

    with pytest.raises(ClientError) as exc:
        client.describe_ca_certificate(certificateId=cert_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_update_ca_certificate__status():
    client = boto3.client("iot", region_name="us-east-1")
    cert_id = client.register_ca_certificate(
        caCertificate="ca_certificate",
        verificationCertificate="verification_certificate",
        registrationConfig={"templateBody": "tb", "roleArn": "my:old_and_busted:arn"},
    )["certificateId"]

    client.update_ca_certificate(certificateId=cert_id, newStatus="DISABLE")
    cert = client.describe_ca_certificate(certificateId=cert_id)
    cert_desc = cert["certificateDescription"]
    assert cert_desc["status"] == "DISABLE"
    assert cert["registrationConfig"] == {
        "roleArn": "my:old_and_busted:arn",
        "templateBody": "tb",
    }


@mock_aws
def test_update_ca_certificate__config():
    client = boto3.client("iot", region_name="us-east-1")
    cert_id = client.register_ca_certificate(
        caCertificate="ca_certificate",
        verificationCertificate="verification_certificate",
    )["certificateId"]

    client.update_ca_certificate(
        certificateId=cert_id,
        registrationConfig={"templateBody": "tb", "roleArn": "my:new_and_fancy:arn"},
    )
    cert = client.describe_ca_certificate(certificateId=cert_id)
    cert_desc = cert["certificateDescription"]
    assert cert_desc["status"] == "INACTIVE"
    assert cert["registrationConfig"] == {
        "roleArn": "my:new_and_fancy:arn",
        "templateBody": "tb",
    }


@mock_aws
def test_get_registration_code():
    client = boto3.client("iot", region_name="us-west-1")

    resp = client.get_registration_code()
    assert "registrationCode" in resp
