import boto
from nose.tools import assert_raises
from sure import expect

from moto import mock_swf
from moto.swf.models import ActivityType
from moto.swf.exceptions import (
    SWFUnknownResourceFault,
    SWFTypeAlreadyExistsFault,
    SWFTypeDeprecatedFault,
    SWFSerializationException,
)


# RegisterActivityType endpoint
@mock_swf
def test_register_activity_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_activity_type("test-domain", "test-activity", "v1.0")

    types = conn.list_activity_types("test-domain", "REGISTERED")
    actype = types["typeInfos"][0]
    actype["activityType"]["name"].should.equal("test-activity")
    actype["activityType"]["version"].should.equal("v1.0")

@mock_swf
def test_register_already_existing_activity_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_activity_type("test-domain", "test-activity", "v1.0")

    with assert_raises(SWFTypeAlreadyExistsFault) as err:
        conn.register_activity_type("test-domain", "test-activity", "v1.0")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("TypeAlreadyExistsFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#TypeAlreadyExistsFault",
        "message": "ActivityType=[name=test-activity, version=v1.0]"
    })

@mock_swf
def test_register_with_wrong_parameter_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")

    with assert_raises(SWFSerializationException) as err:
        conn.register_activity_type("test-domain", "test-activity", 12)

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("SerializationException")
    ex.body["__type"].should.equal("com.amazonaws.swf.base.model#SerializationException")


# ListActivityTypes endpoint
@mock_swf
def test_list_activity_types():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_activity_type("test-domain", "b-test-activity", "v1.0")
    conn.register_activity_type("test-domain", "a-test-activity", "v1.0")
    conn.register_activity_type("test-domain", "c-test-activity", "v1.0")

    all_activity_types = conn.list_activity_types("test-domain", "REGISTERED")
    names = [activity_type["activityType"]["name"] for activity_type in all_activity_types["typeInfos"]]
    names.should.equal(["a-test-activity", "b-test-activity", "c-test-activity"])

@mock_swf
def test_list_activity_types_reverse_order():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_activity_type("test-domain", "b-test-activity", "v1.0")
    conn.register_activity_type("test-domain", "a-test-activity", "v1.0")
    conn.register_activity_type("test-domain", "c-test-activity", "v1.0")

    all_activity_types = conn.list_activity_types("test-domain", "REGISTERED",
                                                  reverse_order=True)
    names = [activity_type["activityType"]["name"] for activity_type in all_activity_types["typeInfos"]]
    names.should.equal(["c-test-activity", "b-test-activity", "a-test-activity"])


# DeprecateActivityType endpoint
@mock_swf
def test_deprecate_activity_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_activity_type("test-domain", "test-activity", "v1.0")
    conn.deprecate_activity_type("test-domain", "test-activity", "v1.0")

    actypes = conn.list_activity_types("test-domain", "DEPRECATED")
    actype = actypes["typeInfos"][0]
    actype["activityType"]["name"].should.equal("test-activity")
    actype["activityType"]["version"].should.equal("v1.0")

@mock_swf
def test_deprecate_already_deprecated_activity_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_activity_type("test-domain", "test-activity", "v1.0")
    conn.deprecate_activity_type("test-domain", "test-activity", "v1.0")

    with assert_raises(SWFTypeDeprecatedFault) as err:
        conn.deprecate_activity_type("test-domain", "test-activity", "v1.0")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("TypeDeprecatedFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#TypeDeprecatedFault",
        "message": "ActivityType=[name=test-activity, version=v1.0]"
    })

@mock_swf
def test_deprecate_non_existent_activity_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")

    with assert_raises(SWFUnknownResourceFault) as err:
        conn.deprecate_activity_type("test-domain", "non-existent", "v1.0")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("UnknownResourceFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#UnknownResourceFault",
        "message": "Unknown type: ActivityType=[name=non-existent, version=v1.0]"
    })

# DescribeActivityType endpoint
@mock_swf
def test_describe_activity_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_activity_type("test-domain", "test-activity", "v1.0",
                                task_list="foo", default_task_heartbeat_timeout="32")

    actype = conn.describe_activity_type("test-domain", "test-activity", "v1.0")
    actype["configuration"]["defaultTaskList"]["name"].should.equal("foo")
    infos = actype["typeInfo"]
    infos["activityType"]["name"].should.equal("test-activity")
    infos["activityType"]["version"].should.equal("v1.0")
    infos["status"].should.equal("REGISTERED")

@mock_swf
def test_describe_non_existent_activity_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")

    with assert_raises(SWFUnknownResourceFault) as err:
        conn.describe_activity_type("test-domain", "non-existent", "v1.0")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("UnknownResourceFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#UnknownResourceFault",
        "message": "Unknown type: ActivityType=[name=non-existent, version=v1.0]"
    })
