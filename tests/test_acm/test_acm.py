import os
import uuid
from time import sleep
from unittest import SkipTest, mock

import boto3
import pytest
from botocore.exceptions import ClientError
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from freezegun import freeze_time

from moto import mock_aws, settings
from moto.acm.models import AWS_ROOT_CA
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

RESOURCE_FOLDER = os.path.join(os.path.dirname(__file__), "resources")


def get_resource(filename):
    return open(os.path.join(RESOURCE_FOLDER, filename), "rb").read()


CA_CRT = get_resource("ca.pem")
CA_KEY = get_resource("ca.key")
SERVER_CRT = get_resource("star_moto_com.pem")
SERVER_COMMON_NAME = "*.moto.com"
SERVER_CRT_BAD = get_resource("star_moto_com-bad.pem")
SERVER_KEY = get_resource("star_moto_com.key")
BAD_ARN = f"arn:aws:acm:us-east-2:{ACCOUNT_ID}:certificate/_0000000-0000-0000-0000-000000000000"


def _import_cert(client):
    response = client.import_certificate(
        Certificate=SERVER_CRT, PrivateKey=SERVER_KEY, CertificateChain=CA_CRT
    )
    return response["CertificateArn"]


# Also tests GetCertificate
@mock_aws
def test_import_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    resp = client.import_certificate(
        Certificate=SERVER_CRT, PrivateKey=SERVER_KEY, CertificateChain=CA_CRT
    )
    resp = client.get_certificate(CertificateArn=resp["CertificateArn"])

    assert resp["Certificate"] == SERVER_CRT.decode()
    assert "CertificateChain" in resp


@mock_aws
def test_import_certificate_with_tags():
    client = boto3.client("acm", region_name="eu-central-1")

    resp = client.import_certificate(
        Certificate=SERVER_CRT,
        PrivateKey=SERVER_KEY,
        CertificateChain=CA_CRT,
        Tags=[{"Key": "Environment", "Value": "QA"}, {"Key": "KeyOnly"}],
    )
    arn = resp["CertificateArn"]

    resp = client.get_certificate(CertificateArn=arn)
    assert resp["Certificate"] == SERVER_CRT.decode()
    assert "CertificateChain" in resp

    resp = client.list_tags_for_certificate(CertificateArn=arn)
    tags = {item["Key"]: item.get("Value", "__NONE__") for item in resp["Tags"]}
    assert "Environment" in tags
    assert "KeyOnly" in tags
    assert tags["Environment"] == "QA"
    assert tags["KeyOnly"] == "__NONE__"


@mock_aws
def test_import_bad_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    try:
        client.import_certificate(Certificate=SERVER_CRT_BAD, PrivateKey=SERVER_KEY)
    except ClientError as err:
        assert err.response["Error"]["Code"] == "ValidationException"
    else:
        raise RuntimeError("Should have raised ValidationException")


@mock_aws
def test_list_certificates():
    client = boto3.client("acm", region_name="eu-central-1")
    issued_arn = _import_cert(client)
    pending_arn = client.request_certificate(DomainName="google.com")["CertificateArn"]

    try:
        certs = client.list_certificates()["CertificateSummaryList"]
    except OverflowError:
        pytest.skip("This test requires 64-bit time_t")
    assert issued_arn in [c["CertificateArn"] for c in certs]
    assert pending_arn in [c["CertificateArn"] for c in certs]
    for cert in certs:
        assert "CertificateArn" in cert
        assert "DomainName" in cert
        assert "Status" in cert
        assert "Type" in cert
        assert "KeyAlgorithm" in cert
        assert "RenewalEligibility" in cert
        assert "NotBefore" in cert
        assert "NotAfter" in cert

    resp = client.list_certificates(CertificateStatuses=["EXPIRED", "INACTIVE"])
    assert len(resp["CertificateSummaryList"]) == 0

    certs = client.list_certificates(CertificateStatuses=["PENDING_VALIDATION"])[
        "CertificateSummaryList"
    ]
    assert issued_arn not in [c["CertificateArn"] for c in certs]
    assert pending_arn in [c["CertificateArn"] for c in certs]

    certs = client.list_certificates(CertificateStatuses=["ISSUED"])[
        "CertificateSummaryList"
    ]
    assert issued_arn in [c["CertificateArn"] for c in certs]
    assert pending_arn not in [c["CertificateArn"] for c in certs]

    certs = client.list_certificates(
        CertificateStatuses=["ISSUED", "PENDING_VALIDATION"]
    )["CertificateSummaryList"]
    assert issued_arn in [c["CertificateArn"] for c in certs]
    assert pending_arn in [c["CertificateArn"] for c in certs]


@mock_aws
def test_get_invalid_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    try:
        client.get_certificate(CertificateArn=BAD_ARN)
    except ClientError as err:
        assert err.response["Error"]["Code"] == "ResourceNotFoundException"
    else:
        raise RuntimeError("Should have raised ResourceNotFoundException")


# Also tests deleting invalid certificate
@mock_aws
def test_delete_certificate():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    # If it does not raise an error and the next call does, all is fine
    client.delete_certificate(CertificateArn=arn)

    try:
        client.delete_certificate(CertificateArn=arn)
    except ClientError as err:
        assert err.response["Error"]["Code"] == "ResourceNotFoundException"
    else:
        raise RuntimeError("Should have raised ResourceNotFoundException")


@mock_aws
def test_describe_certificate():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    try:
        resp = client.describe_certificate(CertificateArn=arn)
    except OverflowError:
        pytest.skip("This test requires 64-bit time_t")
    assert resp["Certificate"]["CertificateArn"] == arn
    assert resp["Certificate"]["DomainName"] == SERVER_COMMON_NAME
    assert resp["Certificate"]["Issuer"] == "Moto"
    assert resp["Certificate"]["KeyAlgorithm"] == "RSA_2048"
    assert resp["Certificate"]["Status"] == "ISSUED"
    assert resp["Certificate"]["Type"] == "IMPORTED"
    assert resp["Certificate"]["RenewalEligibility"] == "INELIGIBLE"
    assert "Options" in resp["Certificate"]

    assert len(resp["Certificate"]["DomainValidationOptions"]) == 1
    validation_option = resp["Certificate"]["DomainValidationOptions"][0]
    assert validation_option["DomainName"] == SERVER_COMMON_NAME


@mock_aws
def test_describe_certificate_with_bad_arn():
    client = boto3.client("acm", region_name="eu-central-1")

    with pytest.raises(ClientError) as err:
        client.describe_certificate(CertificateArn=BAD_ARN)

    assert err.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_export_certificate():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    resp = client.export_certificate(CertificateArn=arn, Passphrase="pass")
    assert resp["Certificate"] == SERVER_CRT.decode()
    assert resp["CertificateChain"] == CA_CRT.decode() + "\n" + AWS_ROOT_CA.decode()
    assert "PrivateKey" in resp

    key = serialization.load_pem_private_key(
        bytes(resp["PrivateKey"], "utf-8"), password=b"pass", backend=default_backend()
    )

    private_key = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    assert private_key == SERVER_KEY


@mock_aws
def test_export_certificate_with_bad_arn():
    client = boto3.client("acm", region_name="eu-central-1")

    with pytest.raises(ClientError) as err:
        client.export_certificate(CertificateArn=BAD_ARN, Passphrase="pass")

    assert err.value.response["Error"]["Code"] == "ResourceNotFoundException"


# Also tests ListTagsForCertificate
@mock_aws
def test_add_tags_to_certificate():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    client.add_tags_to_certificate(
        CertificateArn=arn, Tags=[{"Key": "key1", "Value": "value1"}, {"Key": "key2"}]
    )

    resp = client.list_tags_for_certificate(CertificateArn=arn)
    tags = {item["Key"]: item.get("Value", "__NONE__") for item in resp["Tags"]}

    assert "key1" in tags
    assert "key2" in tags
    assert tags["key1"] == "value1"

    # This way, it ensures that we can detect if None is passed back when it shouldnt,
    # as we store keys without values with a value of None, but it shouldnt be passed back
    assert tags["key2"] == "__NONE__"


@mock_aws
def test_add_tags_to_invalid_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    try:
        client.add_tags_to_certificate(
            CertificateArn=BAD_ARN,
            Tags=[{"Key": "key1", "Value": "value1"}, {"Key": "key2"}],
        )
    except ClientError as err:
        assert err.response["Error"]["Code"] == "ResourceNotFoundException"
    else:
        raise RuntimeError("Should have raised ResourceNotFoundException")


@mock_aws
def test_list_tags_for_invalid_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    try:
        client.list_tags_for_certificate(CertificateArn=BAD_ARN)
    except ClientError as err:
        assert err.response["Error"]["Code"] == "ResourceNotFoundException"
    else:
        raise RuntimeError("Should have raised ResourceNotFoundException")


@mock_aws
def test_remove_tags_from_certificate():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    client.add_tags_to_certificate(
        CertificateArn=arn,
        Tags=[
            {"Key": "key1", "Value": "value1"},
            {"Key": "key2"},
            {"Key": "key3", "Value": "value3"},
            {"Key": "key4", "Value": "value4"},
        ],
    )

    client.remove_tags_from_certificate(
        CertificateArn=arn,
        Tags=[
            {"Key": "key1", "Value": "value2"},  # Should not remove as doesnt match
            {"Key": "key2"},  # Single key removal
            {"Key": "key3", "Value": "value3"},  # Exact match removal
            {"Key": "key4"},  # Partial match removal
        ],
    )

    resp = client.list_tags_for_certificate(CertificateArn=arn)
    tags = {item["Key"]: item.get("Value", "__NONE__") for item in resp["Tags"]}

    for key in ("key2", "key3", "key4"):
        assert key not in tags

    assert "key1" in tags


@mock_aws
def test_remove_tags_from_invalid_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    try:
        client.remove_tags_from_certificate(
            CertificateArn=BAD_ARN,
            Tags=[{"Key": "key1", "Value": "value1"}, {"Key": "key2"}],
        )
    except ClientError as err:
        assert err.response["Error"]["Code"] == "ResourceNotFoundException"
    else:
        raise RuntimeError("Should have raised ResourceNotFoundException")


@mock_aws
def test_resend_validation_email():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    client.resend_validation_email(
        CertificateArn=arn, Domain="*.moto.com", ValidationDomain="NOTUSEDYET"
    )
    # Returns nothing, boto would raise Exceptions otherwise


@mock_aws
def test_resend_validation_email_invalid():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    try:
        client.resend_validation_email(
            CertificateArn=arn,
            Domain="no-match.moto.com",
            ValidationDomain="NOTUSEDYET",
        )
    except ClientError as err:
        assert (
            err.response["Error"]["Code"] == "InvalidDomainValidationOptionsException"
        )
    else:
        raise RuntimeError("Should have raised InvalidDomainValidationOptionsException")

    try:
        client.resend_validation_email(
            CertificateArn=BAD_ARN,
            Domain="no-match.moto.com",
            ValidationDomain="NOTUSEDYET",
        )
    except ClientError as err:
        assert err.response["Error"]["Code"] == "ResourceNotFoundException"
    else:
        raise RuntimeError("Should have raised ResourceNotFoundException")


@mock_aws
def test_request_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    token = str(uuid.uuid4())

    resp = client.request_certificate(
        DomainName="google.com",
        IdempotencyToken=token,
        SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
    )
    assert "CertificateArn" in resp
    arn = resp["CertificateArn"]
    assert f"arn:aws:acm:eu-central-1:{ACCOUNT_ID}:certificate/" in arn

    resp = client.request_certificate(
        DomainName="google.com",
        IdempotencyToken=token,
        SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
    )
    assert resp["CertificateArn"] == arn


@mock_aws
@mock.patch("moto.settings.ACM_VALIDATION_WAIT", 1)
def test_request_certificate_with_optional_arguments():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only change setting in DecoratorMode")
    client = boto3.client("acm", region_name="eu-central-1")

    token = str(uuid.uuid4())

    resp = client.request_certificate(
        DomainName="google.com",
        IdempotencyToken=token,
        SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
        Tags=[
            {"Key": "Environment", "Value": "QA"},
            {"Key": "WithEmptyStr", "Value": ""},
        ],
    )
    assert "CertificateArn" in resp
    arn_1 = resp["CertificateArn"]

    cert = client.describe_certificate(CertificateArn=arn_1)["Certificate"]
    assert cert["Status"] == "PENDING_VALIDATION"
    assert len(cert["SubjectAlternativeNames"]) == 3
    validation_options = cert["DomainValidationOptions"].copy()
    assert len(validation_options) == 3
    assert {option["DomainName"] for option in validation_options} == set(
        cert["SubjectAlternativeNames"]
    )

    # Verify SAN's are still the same, even after the Certificate is validated
    sleep(2)
    for opt in validation_options:
        opt["ValidationStatus"] = "ISSUED"
    cert = client.describe_certificate(CertificateArn=arn_1)["Certificate"]
    assert cert["DomainValidationOptions"] == validation_options

    resp = client.list_tags_for_certificate(CertificateArn=arn_1)
    tags = {item["Key"]: item.get("Value", "__NONE__") for item in resp["Tags"]}
    assert len(tags) == 2
    assert tags["Environment"] == "QA"
    assert tags["WithEmptyStr"] == ""

    # Request certificate for "google.com" with same IdempotencyToken but with different Tags
    resp = client.request_certificate(
        DomainName="google.com",
        IdempotencyToken=token,
        SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
        Tags=[{"Key": "Environment", "Value": "Prod"}, {"Key": "KeyOnly"}],
    )
    arn_2 = resp["CertificateArn"]

    assert arn_1 != arn_2  # if tags are matched, ACM would have returned same arn

    resp = client.list_tags_for_certificate(CertificateArn=arn_2)
    tags = {item["Key"]: item.get("Value", "__NONE__") for item in resp["Tags"]}
    assert len(tags) == 2
    assert tags["Environment"] == "Prod"
    assert tags["KeyOnly"] == "__NONE__"

    resp = client.request_certificate(
        DomainName="google.com",
        IdempotencyToken=token,
        SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
        Tags=[
            {"Key": "Environment", "Value": "QA"},
            {"Key": "WithEmptyStr", "Value": ""},
        ],
    )
    arn_3 = resp["CertificateArn"]

    assert arn_1 != arn_3  # if tags are matched, ACM would have returned same arn

    resp = client.request_certificate(
        DomainName="google.com",
        IdempotencyToken=token,
        SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
    )
    arn_4 = resp["CertificateArn"]

    assert arn_1 != arn_4  # if tags are matched, ACM would have returned same arn


@mock_aws
def test_operations_with_invalid_tags():
    client = boto3.client("acm", region_name="eu-central-1")

    # request certificate with invalid tags
    with pytest.raises(ClientError) as ex:
        client.request_certificate(
            DomainName="example.com", Tags=[{"Key": "X" * 200, "Value": "Valid"}]
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "Member must have length less than or equal to 128" in err["Message"]

    # import certificate with invalid tags
    with pytest.raises(ClientError) as ex:
        client.import_certificate(
            Certificate=SERVER_CRT,
            PrivateKey=SERVER_KEY,
            CertificateChain=CA_CRT,
            Tags=[
                {"Key": "Valid", "Value": "X" * 300},
                {"Key": "aws:xx", "Value": "Valid"},
            ],
        )

    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "Member must have length less than or equal to 256" in err["Message"]

    arn = _import_cert(client)

    # add invalid tags to existing certificate
    with pytest.raises(ClientError) as ex:
        client.add_tags_to_certificate(
            CertificateArn=arn,
            Tags=[{"Key": "aws:xxx", "Value": "Valid"}, {"Key": "key2"}],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "AWS internal tags cannot be changed with this API" in err["Message"]

    # try removing invalid tags from existing certificate
    with pytest.raises(ClientError) as ex:
        client.remove_tags_from_certificate(
            CertificateArn=arn, Tags=[{"Key": "aws:xxx", "Value": "Valid"}]
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "AWS internal tags cannot be changed with this API" in err["Message"]


@mock_aws
def test_add_too_many_tags():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    # Add 51 tags
    with pytest.raises(ClientError) as ex:
        client.add_tags_to_certificate(
            CertificateArn=arn,
            Tags=[{"Key": f"a-{i}", "Value": "abcd"} for i in range(1, 52)],
        )
    assert ex.value.response["Error"]["Code"] == "TooManyTagsException"
    assert "contains too many Tags" in ex.value.response["Error"]["Message"]
    assert client.list_tags_for_certificate(CertificateArn=arn)["Tags"] == []

    # Add 49 tags first, then try to add 2 more.
    client.add_tags_to_certificate(
        CertificateArn=arn,
        Tags=[{"Key": f"p-{i}", "Value": "pqrs"} for i in range(1, 50)],
    )
    assert len(client.list_tags_for_certificate(CertificateArn=arn)["Tags"]) == 49
    with pytest.raises(ClientError) as ex:
        client.add_tags_to_certificate(
            CertificateArn=arn,
            Tags=[{"Key": "x-1", "Value": "xyz"}, {"Key": "x-2", "Value": "xyz"}],
        )
    assert ex.value.response["Error"]["Code"] == "TooManyTagsException"
    assert "contains too many Tags" in ex.value.response["Error"]["Message"]
    assert ex.value.response["Error"]["Message"].count("pqrs") == 49
    assert ex.value.response["Error"]["Message"].count("xyz") == 2
    assert len(client.list_tags_for_certificate(CertificateArn=arn)["Tags"]) == 49


@mock_aws
def test_request_certificate_no_san():
    client = boto3.client("acm", region_name="eu-central-1")

    resp = client.request_certificate(DomainName="google.com")
    assert "CertificateArn" in resp

    resp2 = client.describe_certificate(CertificateArn=resp["CertificateArn"])
    assert "Certificate" in resp2

    assert resp2["Certificate"]["RenewalEligibility"] == "INELIGIBLE"
    assert "Options" in resp2["Certificate"]
    assert len(resp2["Certificate"]["DomainValidationOptions"]) == 1

    validation_option = resp2["Certificate"]["DomainValidationOptions"][0]
    assert validation_option["DomainName"] == "google.com"
    assert validation_option["ValidationDomain"] == "google.com"


# Also tests the SAN code
@mock_aws
def test_request_certificate_issued_status():
    # After requesting a certificate, it should then auto-validate after 1 minute
    # Some sneaky programming for that ;-)
    client = boto3.client("acm", region_name="eu-central-1")

    with freeze_time("2012-01-01 12:00:00"):
        resp = client.request_certificate(
            DomainName="google.com",
            SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
        )
    arn = resp["CertificateArn"]

    with freeze_time("2012-01-01 12:00:00"):
        resp = client.describe_certificate(CertificateArn=arn)
    assert resp["Certificate"]["CertificateArn"] == arn
    assert resp["Certificate"]["DomainName"] == "google.com"
    assert resp["Certificate"]["Issuer"] == "Amazon"
    assert resp["Certificate"]["KeyAlgorithm"] == "RSA_2048"
    assert resp["Certificate"]["Status"] == "PENDING_VALIDATION"
    assert resp["Certificate"]["Type"] == "AMAZON_ISSUED"
    assert len(resp["Certificate"]["SubjectAlternativeNames"]) == 3

    # validation will be pending for 1 minute.
    with freeze_time("2012-01-01 12:00:00"):
        resp = client.describe_certificate(CertificateArn=arn)
    assert resp["Certificate"]["CertificateArn"] == arn
    assert resp["Certificate"]["Status"] == "PENDING_VALIDATION"

    if settings.TEST_DECORATOR_MODE:
        # Move time to get it issued.
        with freeze_time("2012-01-01 12:02:00"):
            resp = client.describe_certificate(CertificateArn=arn)
        assert resp["Certificate"]["CertificateArn"] == arn
        assert resp["Certificate"]["Status"] == "ISSUED"


@mock.patch("moto.settings.ACM_VALIDATION_WAIT", 3)
@mock_aws
def test_request_certificate_issued_status_with_wait_in_envvar():
    # After requesting a certificate, it should then auto-validate after 3 seconds
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    client = boto3.client("acm", region_name="eu-central-1")

    with freeze_time("2012-01-01 12:00:00"):
        resp = client.request_certificate(DomainName="google.com")
    arn = resp["CertificateArn"]

    with freeze_time("2012-01-01 12:00:00"):
        resp = client.describe_certificate(CertificateArn=arn)
    assert resp["Certificate"]["CertificateArn"] == arn
    assert resp["Certificate"]["Status"] == "PENDING_VALIDATION"

    # validation will be pending for 3 seconds.
    with freeze_time("2012-01-01 12:00:02"):
        resp = client.describe_certificate(CertificateArn=arn)
    assert resp["Certificate"]["CertificateArn"] == arn
    assert resp["Certificate"]["Status"] == "PENDING_VALIDATION"

    with freeze_time("2012-01-01 12:00:04"):
        resp = client.describe_certificate(CertificateArn=arn)
    assert resp["Certificate"]["CertificateArn"] == arn
    assert resp["Certificate"]["Status"] == "ISSUED"


@mock_aws
def test_request_certificate_with_mutiple_times():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    # After requesting a certificate, it should then auto-validate after 1 minute
    # Some sneaky programming for that ;-)
    client = boto3.client("acm", region_name="eu-central-1")

    with freeze_time("2012-01-01 12:00:00"):
        resp = client.request_certificate(
            IdempotencyToken="test_token",
            DomainName="google.com",
            SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
        )
    original_arn = resp["CertificateArn"]

    # Should be able to request a certificate multiple times in an hour
    # after that it makes a new one
    for time_intervals in (
        "2012-01-01 12:15:00",
        "2012-01-01 12:30:00",
        "2012-01-01 12:45:00",
    ):
        with freeze_time(time_intervals):
            resp = client.request_certificate(
                IdempotencyToken="test_token",
                DomainName="google.com",
                SubjectAlternativeNames=[
                    "google.com",
                    "www.google.com",
                    "mail.google.com",
                ],
            )
        arn = resp["CertificateArn"]
        assert arn == original_arn

    # Move time
    with freeze_time("2012-01-01 13:01:00"):
        resp = client.request_certificate(
            IdempotencyToken="test_token",
            DomainName="google.com",
            SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
        )
    arn = resp["CertificateArn"]
    assert arn != original_arn


@mock_aws
def test_elb_acm_in_use_by():
    acm_client = boto3.client("acm", region_name="us-west-2")
    elb_client = boto3.client("elb", region_name="us-west-2")

    acm_request_response = acm_client.request_certificate(
        DomainName="fake.domain.com",
        DomainValidationOptions=[
            {"DomainName": "fake.domain.com", "ValidationDomain": "domain.com"}
        ],
    )

    certificate_arn = acm_request_response["CertificateArn"]

    create_load_balancer_request = elb_client.create_load_balancer(
        LoadBalancerName=str(uuid.uuid4()),
        Listeners=[
            {
                "Protocol": "https",
                "LoadBalancerPort": 443,
                "InstanceProtocol": "http",
                "InstancePort": 80,
                "SSLCertificateId": certificate_arn,
            }
        ],
    )

    response = acm_client.describe_certificate(CertificateArn=certificate_arn)

    assert response["Certificate"]["InUseBy"] == [
        create_load_balancer_request["DNSName"]
    ]
