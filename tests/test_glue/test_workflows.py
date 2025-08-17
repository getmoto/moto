import boto3
import pytest
from botocore.client import ClientError
from moto import mock_aws
from datetime import datetime


@mock_aws
def test_create_workflow():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    workflow_names_response = client.list_workflows()

    assert workflow_names_response["Workflows"][0] == workflow_name


workflow_properties_and_values = [
    ("DefaultRunProperties", {"property": "value"}),
    ("Description", "Some description"),
    ("MaxConcurrentRuns", 10),
]


@mock_aws
@pytest.mark.parametrize("property,value", workflow_properties_and_values)
def test_create_workflow_properties(property, value):
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"

    create_kwargs = {property: value}
    client.create_workflow(Name=workflow_name, **create_kwargs)

    workflow_response = client.get_workflow(Name=workflow_name)
    assert workflow_response["Workflow"][property] == value


@mock_aws
def test_get_workflow():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    workflow_response = client.get_workflow(Name=workflow_name)

    assert workflow_response["Workflow"]["Name"] == workflow_name


@mock_aws
def test_get_workflow_missing_entity():
    client = boto3.client("glue", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.get_workflow(Name="test")

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Entity not found"


@mock_aws
def test_delete_workflow():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    client.delete_workflow(Name=workflow_name)

    assert len(client.list_workflows()["Workflows"]) == 0


@mock_aws
def test_delete_doesnt_error_on_nonexistent():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"

    client.delete_workflow(Name=workflow_name)


@mock_aws
def test_batch_get_workflows():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    workflow_response = client.batch_get_workflows(Names=[workflow_name])

    assert workflow_response["Workflows"][0]["Name"] == workflow_name


@mock_aws
def test_batch_get_nonexistent_workflow():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"

    workflow_response = client.batch_get_workflows(Names=[workflow_name])

    assert workflow_response["MissingWorkflows"][0] == workflow_name


@mock_aws
def test_update_workflow_updated_timestamp():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)
    before_update = datetime.now()

    client.update_workflow(Name=workflow_name)

    workflow_response = client.get_workflow(Name=workflow_name)
    assert workflow_response["Workflow"]["LastModifiedOn"] >= before_update


@mock_aws
@pytest.mark.parametrize("property,value", workflow_properties_and_values)
def test_update_workflow_properties(property, value):
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    update_kwargs = {property: value}
    client.update_workflow(Name=workflow_name, **update_kwargs)

    workflow_response = client.get_workflow(Name=workflow_name)
    assert workflow_response["Workflow"][property] == value


@mock_aws
def test_update_nonexistent_workflow():
    client = boto3.client("glue", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.update_workflow(Name="test")

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Entity not found"
