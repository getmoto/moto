import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


# RegisterWorkflowType endpoint
@mock_aws
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
    assert actype["workflowType"]["name"] == "test-workflow"
    assert actype["workflowType"]["version"] == "v1.0"


@mock_aws
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
    assert ex.value.response["Error"]["Code"] == "TypeAlreadyExistsFault"
    assert ex.value.response["Error"]["Message"] == (
        "WorkflowType=[name=test-workflow, version=v1.0]"
    )


# ListWorkflowTypes endpoint
@mock_aws
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
    assert names == ["a-test-workflow", "b-test-workflow", "c-test-workflow"]


# ListWorkflowTypes endpoint
@mock_aws
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
    assert names == ["c-test-workflow", "b-test-workflow", "a-test-workflow"]


# DeprecateWorkflowType endpoint
@mock_aws
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
    assert actype["workflowType"]["name"] == "test-workflow"
    assert actype["workflowType"]["version"] == "v1.0"


@mock_aws
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
    assert ex.value.response["Error"]["Code"] == "TypeDeprecatedFault"
    assert ex.value.response["Error"]["Message"] == (
        "WorkflowType=[name=test-workflow, version=v1.0]"
    )


@mock_aws
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
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        "Unknown type: WorkflowType=[name=test-workflow, version=v1.0]"
    )


# UndeprecateWorkflowType endpoint
@mock_aws
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
    assert resp["typeInfo"]["status"] == "REGISTERED"


@mock_aws
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

    with pytest.raises(ClientError):
        client.undeprecate_workflow_type(
            domain="test-domain",
            workflowType={"name": "test-workflow", "version": "v1.0"},
        )


@mock_aws
def test_undeprecate_never_deprecated_workflow_type():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_workflow_type(
        domain="test-domain", name="test-workflow", version="v1.0"
    )

    with pytest.raises(ClientError):
        client.undeprecate_workflow_type(
            domain="test-domain",
            workflowType={"name": "test-workflow", "version": "v1.0"},
        )


@mock_aws
def test_undeprecate_non_existent_workflow_type():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )

    with pytest.raises(ClientError):
        client.undeprecate_workflow_type(
            domain="test-domain",
            workflowType={"name": "test-workflow", "version": "v1.0"},
        )


# DescribeWorkflowType endpoint
@mock_aws
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
    assert resp["typeInfo"]["workflowType"]["name"] == "test-workflow"
    assert resp["typeInfo"]["workflowType"]["version"] == "v1.0"
    assert resp["typeInfo"]["status"] == "REGISTERED"
    assert resp["typeInfo"]["description"] == "Test workflow."
    assert resp["configuration"]["defaultTaskStartToCloseTimeout"] == "20"
    assert resp["configuration"]["defaultExecutionStartToCloseTimeout"] == "60"
    assert resp["configuration"]["defaultTaskList"]["name"] == "foo"
    assert resp["configuration"]["defaultTaskPriority"] == "-2"
    assert resp["configuration"]["defaultChildPolicy"] == "ABANDON"
    assert resp["configuration"]["defaultLambdaRole"] == "arn:bar"


@mock_aws
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
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        "Unknown type: WorkflowType=[name=non-existent, version=v1.0]"
    )
