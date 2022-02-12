import boto3
from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import
import pytest

from moto import mock_swf
from moto.core import ACCOUNT_ID


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
    all_domains.should.have.key("domainInfos").being.length_of(1)
    domain = all_domains["domainInfos"][0]

    domain["name"].should.equal("test-domain")
    domain["status"].should.equal("REGISTERED")
    domain["description"].should.equal("A test domain")
    domain["arn"].should.equal(
        "arn:aws:swf:us-west-1:{0}:/domain/test-domain".format(ACCOUNT_ID)
    )


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
    ex.value.response["Error"]["Code"].should.equal("DomainAlreadyExistsFault")
    ex.value.response["Error"]["Message"].should.equal("test-domain")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


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
    all_domains.should.have.key("domainInfos").being.length_of(3)

    names = [domain["name"] for domain in all_domains["domainInfos"]]
    names.should.equal(["a-test-domain", "b-test-domain", "c-test-domain"])


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
    all_domains.should.have.key("domainInfos").being.length_of(3)

    names = [domain["name"] for domain in all_domains["domainInfos"]]
    names.should.equal(["c-test-domain", "b-test-domain", "a-test-domain"])


# DeprecateDomain endpoint
@mock_swf
def test_deprecate_domain_boto3():
    client = boto3.client("swf", region_name="us-west-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.deprecate_domain(name="test-domain")

    all_domains = client.list_domains(registrationStatus="REGISTERED")
    all_domains.should.have.key("domainInfos").being.length_of(0)

    all_domains = client.list_domains(registrationStatus="DEPRECATED")
    all_domains.should.have.key("domainInfos").being.length_of(1)

    domain = all_domains["domainInfos"][0]
    domain["name"].should.equal("test-domain")


@mock_swf
def test_deprecate_already_deprecated_domain_boto3():
    client = boto3.client("swf", region_name="us-west-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.deprecate_domain(name="test-domain")

    with pytest.raises(ClientError) as ex:
        client.deprecate_domain(name="test-domain")
    ex.value.response["Error"]["Code"].should.equal("DomainDeprecatedFault")
    ex.value.response["Error"]["Message"].should.equal("test-domain")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_swf
def test_deprecate_non_existent_domain_boto3():
    client = boto3.client("swf", region_name="us-west-1")

    with pytest.raises(ClientError) as ex:
        client.deprecate_domain(name="non-existent")
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal("Unknown domain: non-existent")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


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

    resp["domainInfo"]["status"].should.equal("REGISTERED")


@mock_swf
def test_undeprecate_already_undeprecated_domain():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.deprecate_domain(name="test-domain")
    client.undeprecate_domain(name="test-domain")

    client.undeprecate_domain.when.called_with(name="test-domain").should.throw(
        ClientError
    )


@mock_swf
def test_undeprecate_never_deprecated_domain():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )

    client.undeprecate_domain.when.called_with(name="test-domain").should.throw(
        ClientError
    )


@mock_swf
def test_undeprecate_non_existent_domain():
    client = boto3.client("swf", region_name="us-east-1")

    client.undeprecate_domain.when.called_with(name="non-existent").should.throw(
        ClientError
    )


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
    domain["configuration"]["workflowExecutionRetentionPeriodInDays"].should.equal("60")
    domain["domainInfo"]["description"].should.equal("A test domain")
    domain["domainInfo"]["name"].should.equal("test-domain")
    domain["domainInfo"]["status"].should.equal("REGISTERED")


@mock_swf
def test_describe_non_existent_domain_boto3():
    client = boto3.client("swf", region_name="us-west-1")

    with pytest.raises(ClientError) as ex:
        client.describe_domain(name="non-existent")
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal("Unknown domain: non-existent")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
