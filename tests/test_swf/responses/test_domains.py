import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_swf
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


# RegisterDomain endpoint
@mock_swf
def test_register_domain_boto3():
    client = boto3.client("swf", region_name="us-west-1")
    client.register_domain(
        name="test-domain",
        workflowExecutionRetentionPeriodInDays="60",
        description="A test domain",
    )

    all_domains = client.list_domains(registrationStatus="REGISTERED")
    assert len(all_domains["domainInfos"]) == 1
    domain = all_domains["domainInfos"][0]

    assert domain["name"] == "test-domain"
    assert domain["status"] == "REGISTERED"
    assert domain["description"] == "A test domain"
    assert domain["arn"] == f"arn:aws:swf:us-west-1:{ACCOUNT_ID}:/domain/test-domain"


@mock_swf
def test_register_already_existing_domain_boto3():
    client = boto3.client("swf", region_name="us-west-1")
    client.register_domain(
        name="test-domain",
        workflowExecutionRetentionPeriodInDays="60",
        description="A test domain",
    )

    with pytest.raises(ClientError) as ex:
        client.register_domain(
            name="test-domain",
            workflowExecutionRetentionPeriodInDays="60",
            description="A test domain",
        )
    assert ex.value.response["Error"]["Code"] == "DomainAlreadyExistsFault"
    assert ex.value.response["Error"]["Message"] == "test-domain"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


# ListDomains endpoint
@mock_swf
def test_list_domains_order_boto3():
    client = boto3.client("swf", region_name="us-west-1")
    client.register_domain(
        name="b-test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_domain(
        name="a-test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_domain(
        name="c-test-domain", workflowExecutionRetentionPeriodInDays="60"
    )

    all_domains = client.list_domains(registrationStatus="REGISTERED")
    assert len(all_domains["domainInfos"]) == 3

    names = [domain["name"] for domain in all_domains["domainInfos"]]
    assert names == ["a-test-domain", "b-test-domain", "c-test-domain"]


@mock_swf
def test_list_domains_reverse_order_boto3():
    client = boto3.client("swf", region_name="us-west-1")
    client.register_domain(
        name="b-test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_domain(
        name="a-test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_domain(
        name="c-test-domain", workflowExecutionRetentionPeriodInDays="60"
    )

    all_domains = client.list_domains(
        registrationStatus="REGISTERED", reverseOrder=True
    )
    assert len(all_domains["domainInfos"]) == 3

    names = [domain["name"] for domain in all_domains["domainInfos"]]
    assert names == ["c-test-domain", "b-test-domain", "a-test-domain"]


# DeprecateDomain endpoint
@mock_swf
def test_deprecate_domain_boto3():
    client = boto3.client("swf", region_name="us-west-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.deprecate_domain(name="test-domain")

    all_domains = client.list_domains(registrationStatus="REGISTERED")
    assert len(all_domains["domainInfos"]) == 0

    all_domains = client.list_domains(registrationStatus="DEPRECATED")
    assert len(all_domains["domainInfos"]) == 1

    domain = all_domains["domainInfos"][0]
    assert domain["name"] == "test-domain"


@mock_swf
def test_deprecate_already_deprecated_domain_boto3():
    client = boto3.client("swf", region_name="us-west-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.deprecate_domain(name="test-domain")

    with pytest.raises(ClientError) as ex:
        client.deprecate_domain(name="test-domain")
    assert ex.value.response["Error"]["Code"] == "DomainDeprecatedFault"
    assert ex.value.response["Error"]["Message"] == "test-domain"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_swf
def test_deprecate_non_existent_domain_boto3():
    client = boto3.client("swf", region_name="us-west-1")

    with pytest.raises(ClientError) as ex:
        client.deprecate_domain(name="non-existent")
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == "Unknown domain: non-existent"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


# UndeprecateDomain endpoint
@mock_swf
def test_undeprecate_domain():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.deprecate_domain(name="test-domain")
    client.undeprecate_domain(name="test-domain")

    resp = client.describe_domain(name="test-domain")

    assert resp["domainInfo"]["status"] == "REGISTERED"


@mock_swf
def test_undeprecate_already_undeprecated_domain():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.deprecate_domain(name="test-domain")
    client.undeprecate_domain(name="test-domain")

    with pytest.raises(ClientError):
        client.undeprecate_domain(name="test-domain")


@mock_swf
def test_undeprecate_never_deprecated_domain():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )

    with pytest.raises(ClientError):
        client.undeprecate_domain(name="test-domain")


@mock_swf
def test_undeprecate_non_existent_domain():
    client = boto3.client("swf", region_name="us-east-1")

    with pytest.raises(ClientError):
        client.undeprecate_domain(name="non-existent")


# DescribeDomain endpoint
@mock_swf
def test_describe_domain_boto3():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain",
        workflowExecutionRetentionPeriodInDays="60",
        description="A test domain",
    )

    domain = client.describe_domain(name="test-domain")
    assert domain["configuration"]["workflowExecutionRetentionPeriodInDays"] == "60"
    assert domain["domainInfo"]["description"] == "A test domain"
    assert domain["domainInfo"]["name"] == "test-domain"
    assert domain["domainInfo"]["status"] == "REGISTERED"


@mock_swf
def test_describe_non_existent_domain_boto3():
    client = boto3.client("swf", region_name="us-west-1")

    with pytest.raises(ClientError) as ex:
        client.describe_domain(name="non-existent")
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == "Unknown domain: non-existent"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
