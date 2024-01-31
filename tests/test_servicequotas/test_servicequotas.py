import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_list_aws_default_service_quotas():
    client = boto3.client("service-quotas", region_name="eu-west-1")
    resp = client.list_aws_default_service_quotas(ServiceCode="vpc")

    assert len(resp["Quotas"]) == 25

    assert {
        "Adjustable": True,
        "GlobalQuota": False,
        "QuotaArn": "arn:aws:servicequotas:eu-west-1::vpc/L-2AFB9258",
        "QuotaCode": "L-2AFB9258",
        "QuotaName": "Security groups per network interface",
        "ServiceCode": "vpc",
        "ServiceName": "Amazon Virtual Private Cloud (Amazon VPC)",
        "Unit": "None",
        "Value": 5.0,
    } in resp["Quotas"]
    assert {
        "Adjustable": True,
        "GlobalQuota": False,
        "QuotaArn": "arn:aws:servicequotas:eu-west-1::vpc/L-F678F1CE",
        "QuotaCode": "L-F678F1CE",
        "QuotaName": "VPCs per Region",
        "ServiceCode": "vpc",
        "ServiceName": "Amazon Virtual Private Cloud (Amazon VPC)",
        "Unit": "None",
        "Value": 5.0,
    } in resp["Quotas"]


@mock_aws
def test_list_defaults_for_unknown_service():
    client = boto3.client("service-quotas", "us-east-1")

    with pytest.raises(ClientError) as exc:
        client.list_aws_default_service_quotas(ServiceCode="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchResourceException"
    assert err["Message"] == (
        "This service is not available in the current Region. Choose a "
        "different Region or a different service."
    )


@mock_aws
def test_get_service_quota():
    client = boto3.client("service-quotas", region_name="us-east-2")
    quotas = client.list_aws_default_service_quotas(ServiceCode="vpc")["Quotas"]

    for quota in quotas:
        resp = client.get_service_quota(ServiceCode="vpc", QuotaCode=quota["QuotaCode"])
        assert quota == resp["Quota"]


@mock_aws
def test_get_unknown_service_quota():
    client = boto3.client("service-quotas", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.get_service_quota(ServiceCode="vpc", QuotaCode="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchResourceException"
