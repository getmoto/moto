import boto
from nose.tools import assert_raises
from sure import expect

from moto import mock_swf
from moto.swf.exceptions import (
    SWFUnknownResourceFault,
    SWFDomainAlreadyExistsFault,
    SWFDomainDeprecatedFault,
    SWFSerializationException,
)


# RegisterDomain endpoint
# ListDomain endpoint
@mock_swf
def test_register_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")

    all_domains = conn.list_domains("REGISTERED")
    domain = all_domains["domainInfos"][0]

    domain["name"].should.equal("test-domain")
    domain["status"].should.equal("REGISTERED")
    domain["description"].should.equal("A test domain")

@mock_swf
def test_register_already_existing_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")

    with assert_raises(SWFDomainAlreadyExistsFault) as err:
        conn.register_domain("test-domain", "60", description="A test domain")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("DomainAlreadyExistsFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#DomainAlreadyExistsFault",
        "message": "test-domain"
    })

@mock_swf
def test_register_with_wrong_parameter_type():
    conn = boto.connect_swf("the_key", "the_secret")

    with assert_raises(SWFSerializationException) as err:
        conn.register_domain("test-domain", 60, description="A test domain")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("SerializationException")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#SerializationException",
        "Message": "class java.lang.Foo can not be converted to an String (not a real SWF exception)"
    })


# DeprecateDomain endpoint
@mock_swf
def test_deprecate_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")
    conn.deprecate_domain("test-domain")

    all_domains = conn.list_domains("DEPRECATED")
    domain = all_domains["domainInfos"][0]

    domain["name"].should.equal("test-domain")

@mock_swf
def test_deprecate_already_deprecated_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")
    conn.deprecate_domain("test-domain")

    with assert_raises(SWFDomainDeprecatedFault) as err:
        conn.deprecate_domain("test-domain")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("DomainDeprecatedFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#DomainDeprecatedFault",
        "message": "test-domain"
    })

@mock_swf
def test_deprecate_non_existent_domain():
    conn = boto.connect_swf("the_key", "the_secret")

    with assert_raises(SWFUnknownResourceFault) as err:
        conn.deprecate_domain("non-existent")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("UnknownResourceFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#UnknownResourceFault",
        "message": "Unknown domain: non-existent"
    })

# DescribeDomain endpoint
@mock_swf
def test_describe_domain():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")

    domain = conn.describe_domain("test-domain")
    domain["configuration"]["workflowExecutionRetentionPeriodInDays"].should.equal("60")
    domain["domainInfo"]["description"].should.equal("A test domain")
    domain["domainInfo"]["name"].should.equal("test-domain")
    domain["domainInfo"]["status"].should.equal("REGISTERED")

@mock_swf
def test_describe_non_existent_domain():
    conn = boto.connect_swf("the_key", "the_secret")

    with assert_raises(SWFUnknownResourceFault) as err:
        conn.describe_domain("non-existent")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("UnknownResourceFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#UnknownResourceFault",
        "message": "Unknown domain: non-existent"
    })
