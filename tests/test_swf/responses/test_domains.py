import boto
from boto.swf.exceptions import SWFResponseError
import boto3
from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import
import pytest

from moto import mock_swf_deprecated
from moto import mock_swf
from moto.core import ACCOUNT_ID


# RegisterDomain endpoint
# Has boto3 equivalent
@mock_swf_deprecated
def test_register_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")

    all_domains = conn.list_domains("REGISTERED")
    domain = all_domains["domainInfos"][0]

    domain["name"].should.equal("test-domain")
    domain["status"].should.equal("REGISTERED")
    domain["description"].should.equal("A test domain")
    domain["arn"].should.equal(
        "arn:aws:swf:us-east-1:{0}:/domain/test-domain".format(ACCOUNT_ID)
    )


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


# Has boto3 equivalent
@mock_swf_deprecated
def test_register_already_existing_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")

    conn.register_domain.when.called_with(
        "test-domain", "60", description="A test domain"
    ).should.throw(SWFResponseError)


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


# Has boto3 equivalent
@mock_swf_deprecated
def test_register_with_wrong_parameter_type():
    conn = boto.connect_swf("the_key", "the_secret")

    conn.register_domain.when.called_with(
        "test-domain", 60, description="A test domain"
    ).should.throw(SWFResponseError)


# ListDomains endpoint
# Has boto3 equivalent
@mock_swf_deprecated
def test_list_domains_order():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("b-test-domain", "60")
    conn.register_domain("a-test-domain", "60")
    conn.register_domain("c-test-domain", "60")

    all_domains = conn.list_domains("REGISTERED")
    names = [domain["name"] for domain in all_domains["domainInfos"]]
    names.should.equal(["a-test-domain", "b-test-domain", "c-test-domain"])


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


# Has boto3 equivalent
@mock_swf_deprecated
def test_list_domains_reverse_order():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("b-test-domain", "60")
    conn.register_domain("a-test-domain", "60")
    conn.register_domain("c-test-domain", "60")

    all_domains = conn.list_domains("REGISTERED", reverse_order=True)
    names = [domain["name"] for domain in all_domains["domainInfos"]]
    names.should.equal(["c-test-domain", "b-test-domain", "a-test-domain"])


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
# Has boto3 equivalent
@mock_swf_deprecated
def test_deprecate_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")
    conn.deprecate_domain("test-domain")

    all_domains = conn.list_domains("DEPRECATED")
    domain = all_domains["domainInfos"][0]

    domain["name"].should.equal("test-domain")


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


# Has boto3 equivalent
@mock_swf_deprecated
def test_deprecate_already_deprecated_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")
    conn.deprecate_domain("test-domain")

    conn.deprecate_domain.when.called_with("test-domain").should.throw(SWFResponseError)


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


# Has boto3 equivalent
@mock_swf_deprecated
def test_deprecate_non_existent_domain():
    conn = boto.connect_swf("the_key", "the_secret")

    conn.deprecate_domain.when.called_with("non-existent").should.throw(
        SWFResponseError
    )


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
# Has boto3 equivalent
@mock_swf_deprecated
def test_describe_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")

    domain = conn.describe_domain("test-domain")
    domain["configuration"]["workflowExecutionRetentionPeriodInDays"].should.equal("60")
    domain["domainInfo"]["description"].should.equal("A test domain")
    domain["domainInfo"]["name"].should.equal("test-domain")
    domain["domainInfo"]["status"].should.equal("REGISTERED")


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


# Has boto3 equivalent
@mock_swf_deprecated
def test_describe_non_existent_domain():
    conn = boto.connect_swf("the_key", "the_secret")

    conn.describe_domain.when.called_with("non-existent").should.throw(SWFResponseError)


@mock_swf
def test_describe_non_existent_domain_boto3():
    client = boto3.client("swf", region_name="us-west-1")

    with pytest.raises(ClientError) as ex:
        client.describe_domain(name="non-existent")
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal("Unknown domain: non-existent")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
