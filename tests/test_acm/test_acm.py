from moto.acm.models import AWS_ROOT_CA

import os
import uuid

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from freezegun import freeze_time
from moto import mock_acm, mock_elb, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from unittest import SkipTest, mock


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
@mock_acm
def test_import_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    resp = client.import_certificate(
        Certificate=SERVER_CRT, PrivateKey=SERVER_KEY, CertificateChain=CA_CRT
    )
    resp = client.get_certificate(CertificateArn=resp["CertificateArn"])

    resp["Certificate"].should.equal(SERVER_CRT.decode())
    resp.should.contain("CertificateChain")


@mock_acm
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
    resp["Certificate"].should.equal(SERVER_CRT.decode())
    resp.should.contain("CertificateChain")

    resp = client.list_tags_for_certificate(CertificateArn=arn)
    tags = {item["Key"]: item.get("Value", "__NONE__") for item in resp["Tags"]}
    tags.should.contain("Environment")
    tags.should.contain("KeyOnly")
    tags["Environment"].should.equal("QA")
    tags["KeyOnly"].should.equal("__NONE__")


@mock_acm
def test_import_bad_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    try:
        client.import_certificate(Certificate=SERVER_CRT_BAD, PrivateKey=SERVER_KEY)
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ValidationException")
    else:
        raise RuntimeError("Should of raised ValidationException")


@mock_acm
def test_list_certificates():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    resp = client.list_certificates()
    len(resp["CertificateSummaryList"]).should.equal(1)

    resp["CertificateSummaryList"][0]["CertificateArn"].should.equal(arn)
    resp["CertificateSummaryList"][0]["DomainName"].should.equal(SERVER_COMMON_NAME)


@mock_acm
def test_list_certificates_by_status():
    client = boto3.client("acm", region_name="eu-central-1")
    issued_arn = _import_cert(client)
    pending_arn = client.request_certificate(DomainName="google.com")["CertificateArn"]

    resp = client.list_certificates()
    len(resp["CertificateSummaryList"]).should.equal(2)
    resp = client.list_certificates(CertificateStatuses=["EXPIRED", "INACTIVE"])
    len(resp["CertificateSummaryList"]).should.equal(0)
    resp = client.list_certificates(CertificateStatuses=["PENDING_VALIDATION"])
    len(resp["CertificateSummaryList"]).should.equal(1)
    resp["CertificateSummaryList"][0]["CertificateArn"].should.equal(pending_arn)

    resp = client.list_certificates(CertificateStatuses=["ISSUED"])
    len(resp["CertificateSummaryList"]).should.equal(1)
    resp["CertificateSummaryList"][0]["CertificateArn"].should.equal(issued_arn)
    resp = client.list_certificates(
        CertificateStatuses=["ISSUED", "PENDING_VALIDATION"]
    )
    len(resp["CertificateSummaryList"]).should.equal(2)
    arns = {cert["CertificateArn"] for cert in resp["CertificateSummaryList"]}
    arns.should.contain(issued_arn)
    arns.should.contain(pending_arn)


@mock_acm
def test_get_invalid_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    try:
        client.get_certificate(CertificateArn=BAD_ARN)
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    else:
        raise RuntimeError("Should of raised ResourceNotFoundException")


# Also tests deleting invalid certificate
@mock_acm
def test_delete_certificate():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    # If it does not raise an error and the next call does, all is fine
    client.delete_certificate(CertificateArn=arn)

    try:
        client.delete_certificate(CertificateArn=arn)
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    else:
        raise RuntimeError("Should of raised ResourceNotFoundException")


@mock_acm
def test_describe_certificate():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    try:
        resp = client.describe_certificate(CertificateArn=arn)
    except OverflowError:
        pytest.skip("This test requires 64-bit time_t")
    resp["Certificate"]["CertificateArn"].should.equal(arn)
    resp["Certificate"]["DomainName"].should.equal(SERVER_COMMON_NAME)
    resp["Certificate"]["Issuer"].should.equal("Moto")
    resp["Certificate"]["KeyAlgorithm"].should.equal("RSA_2048")
    resp["Certificate"]["Status"].should.equal("ISSUED")
    resp["Certificate"]["Type"].should.equal("IMPORTED")
    resp["Certificate"].should.have.key("RenewalEligibility").equals("INELIGIBLE")
    resp["Certificate"].should.have.key("Options")
    resp["Certificate"].should.have.key("DomainValidationOptions").length_of(1)

    validation_option = resp["Certificate"]["DomainValidationOptions"][0]
    validation_option.should.have.key("DomainName").equals(SERVER_COMMON_NAME)
    validation_option.shouldnt.have.key("ValidationDomain")


@mock_acm
def test_describe_certificate_with_bad_arn():
    client = boto3.client("acm", region_name="eu-central-1")

    with pytest.raises(ClientError) as err:
        client.describe_certificate(CertificateArn=BAD_ARN)

    err.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_acm
def test_export_certificate():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    resp = client.export_certificate(CertificateArn=arn, Passphrase="pass")
    resp["Certificate"].should.equal(SERVER_CRT.decode())
    resp["CertificateChain"].should.equal(CA_CRT.decode() + "\n" + AWS_ROOT_CA.decode())
    resp.should.have.key("PrivateKey")

    key = serialization.load_pem_private_key(
        bytes(resp["PrivateKey"], "utf-8"), password=b"pass", backend=default_backend()
    )

    private_key = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    private_key.should.equal(SERVER_KEY)


@mock_acm
def test_export_certificate_with_bad_arn():
    client = boto3.client("acm", region_name="eu-central-1")

    with pytest.raises(ClientError) as err:
        client.export_certificate(CertificateArn=BAD_ARN, Passphrase="pass")

    err.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


# Also tests ListTagsForCertificate
@mock_acm
def test_add_tags_to_certificate():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    client.add_tags_to_certificate(
        CertificateArn=arn, Tags=[{"Key": "key1", "Value": "value1"}, {"Key": "key2"}]
    )

    resp = client.list_tags_for_certificate(CertificateArn=arn)
    tags = {item["Key"]: item.get("Value", "__NONE__") for item in resp["Tags"]}

    tags.should.contain("key1")
    tags.should.contain("key2")
    tags["key1"].should.equal("value1")

    # This way, it ensures that we can detect if None is passed back when it shouldnt,
    # as we store keys without values with a value of None, but it shouldnt be passed back
    tags["key2"].should.equal("__NONE__")


@mock_acm
def test_add_tags_to_invalid_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    try:
        client.add_tags_to_certificate(
            CertificateArn=BAD_ARN,
            Tags=[{"Key": "key1", "Value": "value1"}, {"Key": "key2"}],
        )
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    else:
        raise RuntimeError("Should of raised ResourceNotFoundException")


@mock_acm
def test_list_tags_for_invalid_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    try:
        client.list_tags_for_certificate(CertificateArn=BAD_ARN)
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    else:
        raise RuntimeError("Should of raised ResourceNotFoundException")


@mock_acm
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
        tags.should_not.contain(key)

    tags.should.contain("key1")


@mock_acm
def test_remove_tags_from_invalid_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    try:
        client.remove_tags_from_certificate(
            CertificateArn=BAD_ARN,
            Tags=[{"Key": "key1", "Value": "value1"}, {"Key": "key2"}],
        )
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    else:
        raise RuntimeError("Should of raised ResourceNotFoundException")


@mock_acm
def test_resend_validation_email():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    client.resend_validation_email(
        CertificateArn=arn, Domain="*.moto.com", ValidationDomain="NOTUSEDYET"
    )
    # Returns nothing, boto would raise Exceptions otherwise


@mock_acm
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
        err.response["Error"]["Code"].should.equal(
            "InvalidDomainValidationOptionsException"
        )
    else:
        raise RuntimeError("Should of raised InvalidDomainValidationOptionsException")

    try:
        client.resend_validation_email(
            CertificateArn=BAD_ARN,
            Domain="no-match.moto.com",
            ValidationDomain="NOTUSEDYET",
        )
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    else:
        raise RuntimeError("Should of raised ResourceNotFoundException")


@mock_acm
def test_request_certificate():
    client = boto3.client("acm", region_name="eu-central-1")

    token = str(uuid.uuid4())

    resp = client.request_certificate(
        DomainName="google.com",
        IdempotencyToken=token,
        SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
    )
    resp.should.contain("CertificateArn")
    arn = resp["CertificateArn"]
    arn.should.match(r"arn:aws:acm:eu-central-1:\d{12}:certificate/")

    resp = client.request_certificate(
        DomainName="google.com",
        IdempotencyToken=token,
        SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
    )
    resp["CertificateArn"].should.equal(arn)


@mock_acm
def test_request_certificate_with_tags():
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
    resp.should.contain("CertificateArn")
    arn_1 = resp["CertificateArn"]

    resp = client.list_tags_for_certificate(CertificateArn=arn_1)
    tags = {item["Key"]: item.get("Value", "__NONE__") for item in resp["Tags"]}
    tags.should.have.length_of(2)
    tags["Environment"].should.equal("QA")
    tags["WithEmptyStr"].should.equal("")

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
    tags.should.have.length_of(2)
    tags["Environment"].should.equal("Prod")
    tags["KeyOnly"].should.equal("__NONE__")

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


@mock_acm
def test_operations_with_invalid_tags():
    client = boto3.client("acm", region_name="eu-central-1")

    # request certificate with invalid tags
    with pytest.raises(ClientError) as ex:
        client.request_certificate(
            DomainName="example.com", Tags=[{"Key": "X" * 200, "Value": "Valid"}]
        )
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.contain(
        "Member must have length less than or equal to 128"
    )

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

    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.contain(
        "Member must have length less than or equal to 256"
    )

    arn = _import_cert(client)

    # add invalid tags to existing certificate
    with pytest.raises(ClientError) as ex:
        client.add_tags_to_certificate(
            CertificateArn=arn,
            Tags=[{"Key": "aws:xxx", "Value": "Valid"}, {"Key": "key2"}],
        )
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.contain(
        "AWS internal tags cannot be changed with this API"
    )

    # try removing invalid tags from existing certificate
    with pytest.raises(ClientError) as ex:
        client.remove_tags_from_certificate(
            CertificateArn=arn, Tags=[{"Key": "aws:xxx", "Value": "Valid"}]
        )
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.contain(
        "AWS internal tags cannot be changed with this API"
    )


@mock_acm
def test_add_too_many_tags():
    client = boto3.client("acm", region_name="eu-central-1")
    arn = _import_cert(client)

    # Add 51 tags
    with pytest.raises(ClientError) as ex:
        client.add_tags_to_certificate(
            CertificateArn=arn,
            Tags=[{"Key": "a-%d" % i, "Value": "abcd"} for i in range(1, 52)],
        )
    ex.value.response["Error"]["Code"].should.equal("TooManyTagsException")
    ex.value.response["Error"]["Message"].should.contain("contains too many Tags")
    client.list_tags_for_certificate(CertificateArn=arn)["Tags"].should.have.empty

    # Add 49 tags first, then try to add 2 more.
    client.add_tags_to_certificate(
        CertificateArn=arn,
        Tags=[{"Key": "p-%d" % i, "Value": "pqrs"} for i in range(1, 50)],
    )
    client.list_tags_for_certificate(CertificateArn=arn)["Tags"].should.have.length_of(
        49
    )
    with pytest.raises(ClientError) as ex:
        client.add_tags_to_certificate(
            CertificateArn=arn,
            Tags=[{"Key": "x-1", "Value": "xyz"}, {"Key": "x-2", "Value": "xyz"}],
        )
    ex.value.response["Error"]["Code"].should.equal("TooManyTagsException")
    ex.value.response["Error"]["Message"].should.contain("contains too many Tags")
    ex.value.response["Error"]["Message"].count("pqrs").should.equal(49)
    ex.value.response["Error"]["Message"].count("xyz").should.equal(2)
    client.list_tags_for_certificate(CertificateArn=arn)["Tags"].should.have.length_of(
        49
    )


@mock_acm
def test_request_certificate_no_san():
    client = boto3.client("acm", region_name="eu-central-1")

    resp = client.request_certificate(DomainName="google.com")
    resp.should.contain("CertificateArn")

    resp2 = client.describe_certificate(CertificateArn=resp["CertificateArn"])
    resp2.should.contain("Certificate")

    resp2["Certificate"].should.have.key("RenewalEligibility").equals("INELIGIBLE")
    resp2["Certificate"].should.have.key("Options")
    resp2["Certificate"].should.have.key("DomainValidationOptions").length_of(1)

    validation_option = resp2["Certificate"]["DomainValidationOptions"][0]
    validation_option.should.have.key("DomainName").equals("google.com")
    validation_option.should.have.key("ValidationDomain").equals("google.com")


# Also tests the SAN code
@mock_acm
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
    resp["Certificate"]["CertificateArn"].should.equal(arn)
    resp["Certificate"]["DomainName"].should.equal("google.com")
    resp["Certificate"]["Issuer"].should.equal("Amazon")
    resp["Certificate"]["KeyAlgorithm"].should.equal("RSA_2048")
    resp["Certificate"]["Status"].should.equal("PENDING_VALIDATION")
    resp["Certificate"]["Type"].should.equal("AMAZON_ISSUED")
    len(resp["Certificate"]["SubjectAlternativeNames"]).should.equal(3)

    # validation will be pending for 1 minute.
    with freeze_time("2012-01-01 12:00:00"):
        resp = client.describe_certificate(CertificateArn=arn)
    resp["Certificate"]["CertificateArn"].should.equal(arn)
    resp["Certificate"]["Status"].should.equal("PENDING_VALIDATION")

    if not settings.TEST_SERVER_MODE:
        # Move time to get it issued.
        with freeze_time("2012-01-01 12:02:00"):
            resp = client.describe_certificate(CertificateArn=arn)
        resp["Certificate"]["CertificateArn"].should.equal(arn)
        resp["Certificate"]["Status"].should.equal("ISSUED")


@mock.patch("moto.settings.ACM_VALIDATION_WAIT", 3)
@mock_acm
def test_request_certificate_issued_status_with_wait_in_envvar():
    # After requesting a certificate, it should then auto-validate after 3 seconds
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant manipulate time in server mode")

    client = boto3.client("acm", region_name="eu-central-1")

    with freeze_time("2012-01-01 12:00:00"):
        resp = client.request_certificate(DomainName="google.com")
    arn = resp["CertificateArn"]

    with freeze_time("2012-01-01 12:00:00"):
        resp = client.describe_certificate(CertificateArn=arn)
    resp["Certificate"]["CertificateArn"].should.equal(arn)
    resp["Certificate"]["Status"].should.equal("PENDING_VALIDATION")

    # validation will be pending for 3 seconds.
    with freeze_time("2012-01-01 12:00:02"):
        resp = client.describe_certificate(CertificateArn=arn)
    resp["Certificate"]["CertificateArn"].should.equal(arn)
    resp["Certificate"]["Status"].should.equal("PENDING_VALIDATION")

    with freeze_time("2012-01-01 12:00:04"):
        resp = client.describe_certificate(CertificateArn=arn)
    resp["Certificate"]["CertificateArn"].should.equal(arn)
    resp["Certificate"]["Status"].should.equal("ISSUED")


@mock_acm
def test_request_certificate_with_mutiple_times():
    if settings.TEST_SERVER_MODE:
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
        arn.should.equal(original_arn)

    # Move time
    with freeze_time("2012-01-01 13:01:00"):
        resp = client.request_certificate(
            IdempotencyToken="test_token",
            DomainName="google.com",
            SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
        )
    arn = resp["CertificateArn"]
    arn.should_not.equal(original_arn)


@mock_acm
@mock_elb
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
        LoadBalancerName="test",
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

    response["Certificate"]["InUseBy"].should.equal(
        [create_load_balancer_request["DNSName"]]
    )
