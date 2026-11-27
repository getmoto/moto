"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_acm import ACMClient, ACMConfig
    from aws_sdk_acm.models import ResourceNotFoundException
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-acm is not installed", allow_module_level=True)


@mock_aws
def test_website_certificate():
    """Request a certificate for a website, and find the DNS records needed to validate it."""
    config = ACMConfig.resolve(region="us-east-1")
    domain = f"{uuid4().hex}.example.com"

    with ACMClient(config=config) as client:
        certificate_arn = client.request_certificate(
            domain_name=domain,
            subject_alternative_names=[domain, f"www.{domain}"],
            validation_method="DNS",
            idempotency_token=uuid4().hex[:32],
            tags=[{"key": "website", "value": domain}],
        ).certificate_arn
        assert certificate_arn.startswith("arn:aws:acm:us-east-1:")

        certificate = client.describe_certificate(
            certificate_arn=certificate_arn
        ).certificate
        assert certificate.domain_name == domain
        assert sorted(certificate.subject_alternative_names) == [
            domain,
            f"www.{domain}",
        ]
        assert certificate.status == "PENDING_VALIDATION"
        assert certificate.type == "AMAZON_ISSUED"

        # These are the DNS records that need to be created to validate the certificate
        validations = {
            option.domain_name: option
            for option in certificate.domain_validation_options or []
        }
        assert set(validations) == {domain, f"www.{domain}"}
        assert validations[domain].validation_method == "DNS"
        assert validations[domain].resource_record.type == "CNAME"
        assert validations[domain].resource_record.name.endswith(f".{domain}.")

        pending = client.list_certificates(
            certificate_statuses=["PENDING_VALIDATION"]
        ).certificate_summary_list
        assert certificate_arn in [cert.certificate_arn for cert in pending]

        client.add_tags_to_certificate(
            certificate_arn=certificate_arn,
            tags=[{"key": "team", "value": "web"}],
        )
        tags = client.list_tags_for_certificate(certificate_arn=certificate_arn).tags
        assert {tag.key: tag.value for tag in tags} == {
            "website": domain,
            "team": "web",
        }

        client.delete_certificate(certificate_arn=certificate_arn)
        with pytest.raises(ResourceNotFoundException):
            client.describe_certificate(certificate_arn=certificate_arn)
