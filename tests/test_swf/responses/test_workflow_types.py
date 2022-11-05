import sure  # noqa # pylint: disable=unused-import
import boto3
import pytest

from moto import mock_swf
from botocore.exceptions import ClientError


# RegisterWorkflowType endpoint
@mock_swf
def test_register_workflow_type_boto3():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_workflow_type(
        domain="test-domain", name="test-workflow", version="v1.0"
    )

    types = client.list_workflow_types(
        domain="test-domain", registrationStatus="REGISTERED"
    )
    actype = types["typeInfos"][0]
    actype["workflowType"]["name"].should.equal("test-workflow")
    actype["workflowType"]["version"].should.equal("v1.0")


@mock_swf
def test_register_already_existing_workflow_type_boto3():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_workflow_type(
        domain="test-domain", name="test-workflow", version="v1.0"
    )

    with pytest.raises(ClientError) as ex:
        client.register_workflow_type(
            domain="test-domain", name="test-workflow", version="v1.0"
        )
    ex.value.response["Error"]["Code"].should.equal("TypeAlreadyExistsFault")
    ex.value.response["Error"]["Message"].should.equal(
        "WorkflowType=[name=test-workflow, version=v1.0]"
    )


# ListWorkflowTypes endpoint
@mock_swf
def test_list_workflow_types_boto3():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_workflow_type(
        domain="test-domain", name="b-test-workflow", version="v1.0"
    )
    client.register_workflow_type(
        domain="test-domain", name="a-test-workflow", version="v1.0"
    )
    client.register_workflow_type(
        domain="test-domain", name="c-test-workflow", version="v1.0"
    )

    all_workflow_types = client.list_workflow_types(
        domain="test-domain", registrationStatus="REGISTERED"
    )
    names = [
        activity_type["workflowType"]["name"]
        for activity_type in all_workflow_types["typeInfos"]
    ]
    names.should.equal(["a-test-workflow", "b-test-workflow", "c-test-workflow"])


# ListWorkflowTypes endpoint
@mock_swf
def test_list_workflow_types_reverse_order_boto3():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_workflow_type(
        domain="test-domain", name="b-test-workflow", version="v1.0"
    )
    client.register_workflow_type(
        domain="test-domain", name="a-test-workflow", version="v1.0"
    )
    client.register_workflow_type(
        domain="test-domain", name="c-test-workflow", version="v1.0"
    )

    all_workflow_types = client.list_workflow_types(
        domain="test-domain", registrationStatus="REGISTERED", reverseOrder=True
    )
    names = [
        activity_type["workflowType"]["name"]
        for activity_type in all_workflow_types["typeInfos"]
    ]
    names.should.equal(["c-test-workflow", "b-test-workflow", "a-test-workflow"])


# DeprecateWorkflowType endpoint
@mock_swf
def test_deprecate_workflow_type_boto3():
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

    actypes = client.list_workflow_types(
        domain="test-domain", registrationStatus="DEPRECATED"
    )
    actype = actypes["typeInfos"][0]
    actype["workflowType"]["name"].should.equal("test-workflow")
    actype["workflowType"]["version"].should.equal("v1.0")


@mock_swf
def test_deprecate_already_deprecated_workflow_type_boto3():
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

    with pytest.raises(ClientError) as ex:
        client.deprecate_workflow_type(
            domain="test-domain",
            workflowType={"name": "test-workflow", "version": "v1.0"},
        )
    ex.value.response["Error"]["Code"].should.equal("TypeDeprecatedFault")
    ex.value.response["Error"]["Message"].should.equal(
        "WorkflowType=[name=test-workflow, version=v1.0]"
    )


@mock_swf
def test_deprecate_non_existent_workflow_type_boto3():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )

    with pytest.raises(ClientError) as ex:
        client.deprecate_workflow_type(
            domain="test-domain",
            workflowType={"name": "test-workflow", "version": "v1.0"},
        )
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Unknown type: WorkflowType=[name=test-workflow, version=v1.0]"
    )


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


@mock_swf
def test_describe_non_existent_workflow_type_boto3():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )

    with pytest.raises(ClientError) as ex:
        client.describe_workflow_type(
            domain="test-domain",
            workflowType={"name": "non-existent", "version": "v1.0"},
        )
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Unknown type: WorkflowType=[name=non-existent, version=v1.0]"
    )
