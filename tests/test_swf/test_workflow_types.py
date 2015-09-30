import boto
from nose.tools import assert_raises
from sure import expect

from moto import mock_swf
from moto.swf.exceptions import (
    SWFUnknownResourceFault,
    SWFTypeAlreadyExistsFault,
    SWFTypeDeprecatedFault,
    SWFSerializationException,
)


# RegisterWorkflowType endpoint
@mock_swf
def test_register_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "test-workflow", "v1.0")

    types = conn.list_workflow_types("test-domain", "REGISTERED")
    actype = types["typeInfos"][0]
    actype["workflowType"]["name"].should.equal("test-workflow")
    actype["workflowType"]["version"].should.equal("v1.0")

@mock_swf
def test_register_already_existing_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "test-workflow", "v1.0")

    with assert_raises(SWFTypeAlreadyExistsFault) as err:
        conn.register_workflow_type("test-domain", "test-workflow", "v1.0")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("TypeAlreadyExistsFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#TypeAlreadyExistsFault",
        "message": "WorkflowType=[name=test-workflow, version=v1.0]"
    })

@mock_swf
def test_register_with_wrong_parameter_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")

    with assert_raises(SWFSerializationException) as err:
        conn.register_workflow_type("test-domain", "test-workflow", 12)

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("SerializationException")
    ex.body["__type"].should.equal("com.amazonaws.swf.base.model#SerializationException")


# ListWorkflowTypes endpoint
@mock_swf
def test_list_workflow_types():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "b-test-workflow", "v1.0")
    conn.register_workflow_type("test-domain", "a-test-workflow", "v1.0")
    conn.register_workflow_type("test-domain", "c-test-workflow", "v1.0")

    all_workflow_types = conn.list_workflow_types("test-domain", "REGISTERED")
    names = [activity_type["workflowType"]["name"] for activity_type in all_workflow_types["typeInfos"]]
    names.should.equal(["a-test-workflow", "b-test-workflow", "c-test-workflow"])

@mock_swf
def test_list_workflow_types_reverse_order():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "b-test-workflow", "v1.0")
    conn.register_workflow_type("test-domain", "a-test-workflow", "v1.0")
    conn.register_workflow_type("test-domain", "c-test-workflow", "v1.0")

    all_workflow_types = conn.list_workflow_types("test-domain", "REGISTERED",
                                                  reverse_order=True)
    names = [activity_type["workflowType"]["name"] for activity_type in all_workflow_types["typeInfos"]]
    names.should.equal(["c-test-workflow", "b-test-workflow", "a-test-workflow"])


# DeprecateWorkflowType endpoint
@mock_swf
def test_deprecate_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "test-workflow", "v1.0")
    conn.deprecate_workflow_type("test-domain", "test-workflow", "v1.0")

    actypes = conn.list_workflow_types("test-domain", "DEPRECATED")
    actype = actypes["typeInfos"][0]
    actype["workflowType"]["name"].should.equal("test-workflow")
    actype["workflowType"]["version"].should.equal("v1.0")

@mock_swf
def test_deprecate_already_deprecated_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "test-workflow", "v1.0")
    conn.deprecate_workflow_type("test-domain", "test-workflow", "v1.0")

    with assert_raises(SWFTypeDeprecatedFault) as err:
        conn.deprecate_workflow_type("test-domain", "test-workflow", "v1.0")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("TypeDeprecatedFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#TypeDeprecatedFault",
        "message": "WorkflowType=[name=test-workflow, version=v1.0]"
    })

@mock_swf
def test_deprecate_non_existent_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")

    with assert_raises(SWFUnknownResourceFault) as err:
        conn.deprecate_workflow_type("test-domain", "non-existent", "v1.0")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("UnknownResourceFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#UnknownResourceFault",
        "message": "Unknown type: WorkflowType=[name=non-existent, version=v1.0]"
    })

# DescribeWorkflowType endpoint
@mock_swf
def test_describe_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "test-workflow", "v1.0",
                                task_list="foo", default_child_policy="TERMINATE")

    actype = conn.describe_workflow_type("test-domain", "test-workflow", "v1.0")
    actype["configuration"]["defaultTaskList"]["name"].should.equal("foo")
    actype["configuration"]["defaultChildPolicy"].should.equal("TERMINATE")
    actype["configuration"].keys().should_not.contain("defaultTaskStartToCloseTimeout")
    infos = actype["typeInfo"]
    infos["workflowType"]["name"].should.equal("test-workflow")
    infos["workflowType"]["version"].should.equal("v1.0")
    infos["status"].should.equal("REGISTERED")

@mock_swf
def test_describe_non_existent_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")

    with assert_raises(SWFUnknownResourceFault) as err:
        conn.describe_workflow_type("test-domain", "non-existent", "v1.0")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("UnknownResourceFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#UnknownResourceFault",
        "message": "Unknown type: WorkflowType=[name=non-existent, version=v1.0]"
    })
