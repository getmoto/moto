import sure
import boto
import boto3

from moto import mock_swf_deprecated
from moto import mock_swf
from boto.swf.exceptions import SWFResponseError
from botocore.exceptions import ClientError


# RegisterWorkflowType endpoint
@mock_swf_deprecated
def test_register_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "test-workflow", "v1.0")

    types = conn.list_workflow_types("test-domain", "REGISTERED")
    actype = types["typeInfos"][0]
    actype["workflowType"]["name"].should.equal("test-workflow")
    actype["workflowType"]["version"].should.equal("v1.0")


@mock_swf_deprecated
def test_register_already_existing_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "test-workflow", "v1.0")

    conn.register_workflow_type.when.called_with(
        "test-domain", "test-workflow", "v1.0"
    ).should.throw(SWFResponseError)


@mock_swf_deprecated
def test_register_with_wrong_parameter_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")

    conn.register_workflow_type.when.called_with(
        "test-domain", "test-workflow", 12
    ).should.throw(SWFResponseError)


# ListWorkflowTypes endpoint
@mock_swf_deprecated
def test_list_workflow_types():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "b-test-workflow", "v1.0")
    conn.register_workflow_type("test-domain", "a-test-workflow", "v1.0")
    conn.register_workflow_type("test-domain", "c-test-workflow", "v1.0")

    all_workflow_types = conn.list_workflow_types("test-domain", "REGISTERED")
    names = [
        activity_type["workflowType"]["name"]
        for activity_type in all_workflow_types["typeInfos"]
    ]
    names.should.equal(["a-test-workflow", "b-test-workflow", "c-test-workflow"])


@mock_swf_deprecated
def test_list_workflow_types_reverse_order():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "b-test-workflow", "v1.0")
    conn.register_workflow_type("test-domain", "a-test-workflow", "v1.0")
    conn.register_workflow_type("test-domain", "c-test-workflow", "v1.0")

    all_workflow_types = conn.list_workflow_types(
        "test-domain", "REGISTERED", reverse_order=True
    )
    names = [
        activity_type["workflowType"]["name"]
        for activity_type in all_workflow_types["typeInfos"]
    ]
    names.should.equal(["c-test-workflow", "b-test-workflow", "a-test-workflow"])


# DeprecateWorkflowType endpoint
@mock_swf_deprecated
def test_deprecate_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "test-workflow", "v1.0")
    conn.deprecate_workflow_type("test-domain", "test-workflow", "v1.0")

    actypes = conn.list_workflow_types("test-domain", "DEPRECATED")
    actype = actypes["typeInfos"][0]
    actype["workflowType"]["name"].should.equal("test-workflow")
    actype["workflowType"]["version"].should.equal("v1.0")


@mock_swf_deprecated
def test_deprecate_already_deprecated_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type("test-domain", "test-workflow", "v1.0")
    conn.deprecate_workflow_type("test-domain", "test-workflow", "v1.0")

    conn.deprecate_workflow_type.when.called_with(
        "test-domain", "test-workflow", "v1.0"
    ).should.throw(SWFResponseError)


@mock_swf_deprecated
def test_deprecate_non_existent_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")

    conn.deprecate_workflow_type.when.called_with(
        "test-domain", "non-existent", "v1.0"
    ).should.throw(SWFResponseError)


# UndeprecateWorkflowType endpoint
@mock_swf
def test_undeprecate_workflow_type():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_workflow_type(
        domain="test-domain", name="test-workflow", version="v1.0"
    )
    client.deprecate_workflow_type(
        domain="test-domain", workflowType={"name": "test-workflow", "version": "v1.0"}
    )
    client.undeprecate_workflow_type(
        domain="test-domain", workflowType={"name": "test-workflow", "version": "v1.0"}
    )

    resp = client.describe_workflow_type(
        domain="test-domain", workflowType={"name": "test-workflow", "version": "v1.0"}
    )
    resp["typeInfo"]["status"].should.equal("REGISTERED")


@mock_swf
def test_undeprecate_already_undeprecated_workflow_type():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_workflow_type(
        domain="test-domain", name="test-workflow", version="v1.0"
    )
    client.deprecate_workflow_type(
        domain="test-domain", workflowType={"name": "test-workflow", "version": "v1.0"}
    )
    client.undeprecate_workflow_type(
        domain="test-domain", workflowType={"name": "test-workflow", "version": "v1.0"}
    )

    client.undeprecate_workflow_type.when.called_with(
        domain="test-domain", workflowType={"name": "test-workflow", "version": "v1.0"}
    ).should.throw(ClientError)


@mock_swf
def test_undeprecate_never_deprecated_workflow_type():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_workflow_type(
        domain="test-domain", name="test-workflow", version="v1.0"
    )

    client.undeprecate_workflow_type.when.called_with(
        domain="test-domain", workflowType={"name": "test-workflow", "version": "v1.0"}
    ).should.throw(ClientError)


@mock_swf
def test_undeprecate_non_existent_workflow_type():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )

    client.undeprecate_workflow_type.when.called_with(
        domain="test-domain", workflowType={"name": "test-workflow", "version": "v1.0"}
    ).should.throw(ClientError)


# DescribeWorkflowType endpoint
@mock_swf_deprecated
def test_describe_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")
    conn.register_workflow_type(
        "test-domain",
        "test-workflow",
        "v1.0",
        task_list="foo",
        default_child_policy="TERMINATE",
    )

    actype = conn.describe_workflow_type("test-domain", "test-workflow", "v1.0")
    actype["configuration"]["defaultTaskList"]["name"].should.equal("foo")
    actype["configuration"]["defaultChildPolicy"].should.equal("TERMINATE")
    actype["configuration"].keys().should_not.contain("defaultTaskStartToCloseTimeout")
    infos = actype["typeInfo"]
    infos["workflowType"]["name"].should.equal("test-workflow")
    infos["workflowType"]["version"].should.equal("v1.0")
    infos["status"].should.equal("REGISTERED")


@mock_swf
def test_describe_workflow_type_full_boto3():
    # boto3 required as boto doesn't support all of the arguments
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="2"
    )
    client.register_workflow_type(
        domain="test-domain",
        name="test-workflow",
        version="v1.0",
        description="Test workflow.",
        defaultTaskStartToCloseTimeout="20",
        defaultExecutionStartToCloseTimeout="60",
        defaultTaskList={"name": "foo"},
        defaultTaskPriority="-2",
        defaultChildPolicy="ABANDON",
        defaultLambdaRole="arn:bar",
    )

    resp = client.describe_workflow_type(
        domain="test-domain", workflowType={"name": "test-workflow", "version": "v1.0"}
    )
    resp["typeInfo"]["workflowType"]["name"].should.equal("test-workflow")
    resp["typeInfo"]["workflowType"]["version"].should.equal("v1.0")
    resp["typeInfo"]["status"].should.equal("REGISTERED")
    resp["typeInfo"]["description"].should.equal("Test workflow.")
    resp["configuration"]["defaultTaskStartToCloseTimeout"].should.equal("20")
    resp["configuration"]["defaultExecutionStartToCloseTimeout"].should.equal("60")
    resp["configuration"]["defaultTaskList"]["name"].should.equal("foo")
    resp["configuration"]["defaultTaskPriority"].should.equal("-2")
    resp["configuration"]["defaultChildPolicy"].should.equal("ABANDON")
    resp["configuration"]["defaultLambdaRole"].should.equal("arn:bar")


@mock_swf_deprecated
def test_describe_non_existent_workflow_type():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60")

    conn.describe_workflow_type.when.called_with(
        "test-domain", "non-existent", "v1.0"
    ).should.throw(SWFResponseError)
