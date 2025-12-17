from datetime import datetime

import boto3
import pytest
from botocore.client import ClientError

from moto import mock_aws


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


@mock_aws
def test_start_and_get_workflow_run():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    run_id = client.start_workflow_run(Name=workflow_name)["RunId"]

    workflow_run_response = client.get_workflow_run(Name=workflow_name, RunId=run_id)

    assert workflow_run_response.get("Run")


@mock_aws
def test_get_workflow_run_with_nonexistent_workflow():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    run_id = client.start_workflow_run(Name=workflow_name)["RunId"]

    with pytest.raises(ClientError) as exc:
        client.get_workflow_run(Name="some_other_workflow", RunId=run_id)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Entity not found"


@mock_aws
def test_get_nonexistent_workflow_run():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    with pytest.raises(ClientError) as exc:
        client.get_workflow_run(Name=workflow_name, RunId="run_id")

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Entity not found"


@mock_aws
def test_get_workflow_runs():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    client.start_workflow_run(Name=workflow_name)

    workflow_run_response = client.get_workflow_runs(Name=workflow_name)

    assert len(workflow_run_response["Runs"])
    assert workflow_run_response["Runs"][0]["WorkflowRunId"]


@mock_aws
def test_get_workflow_runs_with_nonexistent_workflow():
    client = boto3.client("glue", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_workflow_runs(Name="some_other_workflow")

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Entity not found"


@mock_aws
def test_stop_workflow_run():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    run_id = client.start_workflow_run(Name=workflow_name)["RunId"]

    client.stop_workflow_run(Name=workflow_name, RunId=run_id)


@mock_aws
def test_stop_workflow_run_with_nonexistent_workflow():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    run_id = client.start_workflow_run(Name=workflow_name)["RunId"]

    with pytest.raises(ClientError) as exc:
        client.stop_workflow_run(Name="some_other_workflow", RunId=run_id)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Entity not found"


@mock_aws
def test_stop_workflow_nonexistent_run():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    client.start_workflow_run(Name=workflow_name)

    with pytest.raises(ClientError) as exc:
        client.stop_workflow_run(Name=workflow_name, RunId="run_id")

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Entity not found"


@mock_aws
def test_default_properties_in_workflow_run():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    default_properties = {"test": "test"}
    client.create_workflow(Name=workflow_name, DefaultRunProperties=default_properties)

    run_id = client.start_workflow_run(Name=workflow_name)["RunId"]

    properties = client.get_workflow_run_properties(Name=workflow_name, RunId=run_id)[
        "RunProperties"
    ]

    assert properties == default_properties


@mock_aws
def test_default_properties_overridden_by_run_properties():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    default_properties = {"test": "test"}
    client.create_workflow(Name=workflow_name, DefaultRunProperties=default_properties)

    run_properties = {"test": "run_test"}

    run_id = client.start_workflow_run(
        Name=workflow_name, RunProperties=run_properties
    )["RunId"]

    properties = client.get_workflow_run_properties(Name=workflow_name, RunId=run_id)[
        "RunProperties"
    ]

    assert properties == run_properties


@mock_aws
def test_get_run_properties_from_nonexistent_workflow():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    run_id = client.start_workflow_run(Name=workflow_name)["RunId"]

    with pytest.raises(ClientError) as exc:
        client.get_workflow_run_properties(Name="nonexistent_workflow", RunId=run_id)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Entity not found"


@mock_aws
def test_get_run_properties_from_nonexistent_run():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    with pytest.raises(ClientError) as exc:
        client.get_workflow_run_properties(Name=workflow_name, RunId="run_id")

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Entity not found"


@mock_aws
def test_put_run_properties():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    run_properties = {"test": "run_test"}

    run_id = client.start_workflow_run(
        Name=workflow_name, RunProperties=run_properties
    )["RunId"]

    new_properties = {"test": "new_test"}
    client.put_workflow_run_properties(
        Name=workflow_name, RunId=run_id, RunProperties=new_properties
    )

    properties = client.get_workflow_run_properties(Name=workflow_name, RunId=run_id)[
        "RunProperties"
    ]

    assert properties == new_properties


@mock_aws
def test_put_run_properties_nonexistent_workflow():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    run_id = client.start_workflow_run(Name=workflow_name)["RunId"]

    new_properties = {"test": "new_test"}

    with pytest.raises(ClientError) as exc:
        client.put_workflow_run_properties(
            Name="nonexistent_workflow", RunId=run_id, RunProperties=new_properties
        )

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Entity not found"


@mock_aws
def test_put_run_properties_nonexistent_run_id():
    client = boto3.client("glue", region_name="us-east-1")
    workflow_name = "test"
    client.create_workflow(Name=workflow_name)

    client.start_workflow_run(Name=workflow_name)

    new_properties = {"test": "new_test"}

    with pytest.raises(ClientError) as exc:
        client.put_workflow_run_properties(
            Name=workflow_name, RunId="run_id", RunProperties=new_properties
        )

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Entity not found"
