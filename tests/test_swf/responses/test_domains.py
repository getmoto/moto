import boto
from boto.swf.exceptions import SWFResponseError
import sure  # noqa

from moto import mock_swf_deprecated


# RegisterDomain endpoint
@mock_swf_deprecated
def test_register_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")

    all_domains = conn.list_domains("REGISTERED")
    domain = all_domains["domainInfos"][0]

    domain["name"].should.equal("test-domain")
    domain["status"].should.equal("REGISTERED")
    domain["description"].should.equal("A test domain")


@mock_swf_deprecated
def test_register_already_existing_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")

    conn.register_domain.when.called_with(
        "test-domain", "60", description="A test domain"
    ).should.throw(SWFResponseError)


@mock_swf_deprecated
def test_register_with_wrong_parameter_type():
    conn = boto.connect_swf("the_key", "the_secret")

    conn.register_domain.when.called_with(
        "test-domain", 60, description="A test domain"
    ).should.throw(SWFResponseError)


# ListDomains endpoint
@mock_swf_deprecated
def test_list_domains_order():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("b-test-domain", "60")
    conn.register_domain("a-test-domain", "60")
    conn.register_domain("c-test-domain", "60")

    all_domains = conn.list_domains("REGISTERED")
    names = [domain["name"] for domain in all_domains["domainInfos"]]
    names.should.equal(["a-test-domain", "b-test-domain", "c-test-domain"])


@mock_swf_deprecated
def test_list_domains_reverse_order():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("b-test-domain", "60")
    conn.register_domain("a-test-domain", "60")
    conn.register_domain("c-test-domain", "60")

    all_domains = conn.list_domains("REGISTERED", reverse_order=True)
    names = [domain["name"] for domain in all_domains["domainInfos"]]
    names.should.equal(["c-test-domain", "b-test-domain", "a-test-domain"])


# DeprecateDomain endpoint
@mock_swf_deprecated
def test_deprecate_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")
    conn.deprecate_domain("test-domain")

    all_domains = conn.list_domains("DEPRECATED")
    domain = all_domains["domainInfos"][0]

    domain["name"].should.equal("test-domain")


@mock_swf_deprecated
def test_deprecate_already_deprecated_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")
    conn.deprecate_domain("test-domain")

    conn.deprecate_domain.when.called_with(
        "test-domain"
    ).should.throw(SWFResponseError)


@mock_swf_deprecated
def test_deprecate_non_existent_domain():
    conn = boto.connect_swf("the_key", "the_secret")

    conn.deprecate_domain.when.called_with(
        "non-existent"
    ).should.throw(SWFResponseError)


# DescribeDomain endpoint
@mock_swf_deprecated
def test_describe_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")

    domain = conn.describe_domain("test-domain")
    domain["configuration"][
        "workflowExecutionRetentionPeriodInDays"].should.equal("60")
    domain["domainInfo"]["description"].should.equal("A test domain")
    domain["domainInfo"]["name"].should.equal("test-domain")
    domain["domainInfo"]["status"].should.equal("REGISTERED")


@mock_swf_deprecated
def test_describe_non_existent_domain():
    conn = boto.connect_swf("the_key", "the_secret")

    conn.describe_domain.when.called_with(
        "non-existent"
    ).should.throw(SWFResponseError)
