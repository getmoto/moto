import datetime
import uuid

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

TEST_REGION_NAME = "us-east-1"


@mock_aws
def test_create_trial_component():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    trial_component_name = "some-trial-component-name"

    resp = client.create_trial_component(TrialComponentName=trial_component_name)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = client.describe_trial_component(TrialComponentName=trial_component_name)

    assert resp["TrialComponentName"] == trial_component_name
    assert resp["TrialComponentArn"] == (
        f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}"
        f":experiment-trial-component/{trial_component_name}"
    )
    assert resp["DisplayName"] == trial_component_name
    assert resp.get("Status") is None
    assert resp.get("StartTime") is None
    assert resp.get("EndTime") is None
    assert resp.get("LastModifiedBy") == {}
    assert resp.get("CreatedBy") == {}
    assert resp.get("Parameters") == {}
    assert resp.get("InputArtifacts") == {}
    assert resp.get("OutputArtifacts") == {}
    assert resp.get("Metrics") == []
    assert resp.get("Sources") == []


@mock_aws
def test_list_trial_components():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    trial_component_names = [f"some-trial-component-name-{i}" for i in range(10)]

    for trial_component_name in trial_component_names:
        resp = client.create_trial_component(TrialComponentName=trial_component_name)

    resp = client.list_trial_components(MaxResults=1)

    assert len(resp["TrialComponentSummaries"]) == 1

    next_token = resp["NextToken"]

    resp = client.list_trial_components(MaxResults=2, NextToken=next_token)

    assert len(resp["TrialComponentSummaries"]) == 2

    next_token = resp["NextToken"]

    resp = client.list_trial_components(NextToken=next_token)

    assert len(resp["TrialComponentSummaries"]) == 7

    assert resp.get("NextToken") is None


@mock_aws
def test_delete__trial_component():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    trial_component_name = "some-trial-component-name"

    resp = client.create_trial_component(TrialComponentName=trial_component_name)
    resp = client.delete_trial_component(TrialComponentName=trial_component_name)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = client.list_trial_components()

    assert len(resp["TrialComponentSummaries"]) == 0


@mock_aws
def test_add_tags_to_trial_component():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    trial_component_name = "some-trial-component-name"

    resp = client.create_trial_component(TrialComponentName=trial_component_name)

    resp = client.describe_trial_component(TrialComponentName=trial_component_name)

    arn = resp["TrialComponentArn"]

    tags = [{"Key": "name", "Value": "value"}]

    client.add_tags(ResourceArn=arn, Tags=tags)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = client.list_tags(ResourceArn=arn)

    assert resp["Tags"] == tags


@mock_aws
def test_delete_tags_to_trial_component():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    trial_component_name = "some-trial-component-name"

    resp = client.create_trial_component(TrialComponentName=trial_component_name)

    resp = client.describe_trial_component(TrialComponentName=trial_component_name)

    arn = resp["TrialComponentArn"]

    tags = [{"Key": "name", "Value": "value"}]

    client.add_tags(ResourceArn=arn, Tags=tags)

    client.delete_tags(ResourceArn=arn, TagKeys=[i["Key"] for i in tags])

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = client.list_tags(ResourceArn=arn)

    assert resp["Tags"] == []


@mock_aws
def test_list_trial_component_tags():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    trial_component_name = "some-trial-component-name"
    client.create_trial_component(TrialComponentName=trial_component_name)
    resp = client.describe_trial_component(TrialComponentName=trial_component_name)
    resource_arn = resp["TrialComponentArn"]

    tags = []
    for _ in range(80):
        tags.append({"Key": str(uuid.uuid4()), "Value": "myValue"})

    response = client.add_tags(ResourceArn=resource_arn, Tags=tags)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = client.list_tags(ResourceArn=resource_arn)
    assert len(response["Tags"]) == 50
    assert response["Tags"] == tags[:50]

    response = client.list_tags(
        ResourceArn=resource_arn, NextToken=response["NextToken"]
    )
    assert len(response["Tags"]) == 30
    assert response["Tags"] == tags[50:]


@mock_aws
def test_associate_trial_component():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    experiment_name = "some-experiment-name"

    resp = client.create_experiment(ExperimentName=experiment_name)

    trial_name = "some-trial-name"

    resp = client.create_trial(ExperimentName=experiment_name, TrialName=trial_name)

    trial_component_name = "some-trial-component-name"

    resp = client.create_trial_component(TrialComponentName=trial_component_name)

    resp = client.associate_trial_component(
        TrialComponentName=trial_component_name, TrialName=trial_name
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["TrialComponentArn"] == (
        f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}"
        f":experiment-trial-component/{trial_component_name}"
    )
    assert (
        resp["TrialArn"]
        == f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:experiment-trial/{trial_name}"
    )

    resp = client.list_trial_components(TrialName=trial_name)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert (
        resp["TrialComponentSummaries"][0]["TrialComponentName"] == trial_component_name
    )

    resp = client.list_trials(TrialComponentName=trial_component_name)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["TrialSummaries"][0]["TrialName"] == trial_name

    with pytest.raises(ClientError) as ex:
        resp = client.associate_trial_component(
            TrialComponentName="does-not-exist", TrialName="does-not-exist"
        )

    assert ex.value.response["Error"]["Code"] == "ResourceNotFound"
    assert ex.value.response["Error"]["Message"] == (
        f"Trial 'arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}"
        ":experiment-trial/does-not-exist' does not exist."
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_disassociate_trial_component():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    experiment_name = "some-experiment-name"

    resp = client.create_experiment(ExperimentName=experiment_name)

    trial_name = "some-trial-name"

    resp = client.create_trial(ExperimentName=experiment_name, TrialName=trial_name)

    trial_component_name = "some-trial-component-name"

    resp = client.create_trial_component(TrialComponentName=trial_component_name)

    client.associate_trial_component(
        TrialComponentName=trial_component_name, TrialName=trial_name
    )

    resp = client.disassociate_trial_component(
        TrialComponentName=trial_component_name, TrialName=trial_name
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["TrialComponentArn"] == (
        f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}"
        f":experiment-trial-component/{trial_component_name}"
    )
    assert (
        resp["TrialArn"]
        == f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:experiment-trial/{trial_name}"
    )

    resp = client.list_trial_components(TrialName=trial_name)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp["TrialComponentSummaries"]) == 0

    resp = client.list_trials(TrialComponentName=trial_component_name)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp["TrialSummaries"]) == 0

    resp = client.disassociate_trial_component(
        TrialComponentName="does-not-exist", TrialName="does-not-exist"
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["TrialComponentArn"] == (
        f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:"
        "experiment-trial-component/does-not-exist"
    )
    assert (
        resp["TrialArn"]
        == f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:experiment-trial/does-not-exist"
    )


@mock_aws
def test_update_trial_component() -> None:
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    trial_component_name = "some-trial-component-name"
    client.create_trial_component(
        TrialComponentName=trial_component_name,
    )
    given_status = {"PrimaryStatus": "InProgress", "Message": "a-message"}
    given_display_name = "new-display-name"
    given_parameters = {
        "param1": {"StringValue": "param1-value", "NumberValue": 123.0},
        "param2": {"StringValue": "param2-value", "NumberValue": 456.0},
    }
    given_input_artifacts = {
        "artifact1": {"MediaType": "text/plain", "Value": "artifact1-value"}
    }
    given_output_artifacts = {
        "artifact2": {"MediaType": "text/plain", "Value": "artifact2-value"}
    }
    given_start_date = datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc)
    given_end_date = datetime.datetime(2021, 1, 2, tzinfo=datetime.timezone.utc)
    resp_created = client.describe_trial_component(
        TrialComponentName=trial_component_name
    )

    resp_update = client.update_trial_component(
        TrialComponentName=trial_component_name,
        DisplayName=given_display_name,
        Status=given_status,
        StartTime=given_start_date,
        EndTime=given_end_date,
        Parameters=given_parameters,
        InputArtifacts=given_input_artifacts,
        OutputArtifacts=given_output_artifacts,
    )
    resp_updated = client.describe_trial_component(
        TrialComponentName=trial_component_name
    )

    assert (
        resp_update["TrialComponentArn"]
        == f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:experiment-trial-component/some-trial-component-name"
    )
    assert resp_updated["DisplayName"] == given_display_name
    assert resp_updated["Status"] == given_status
    assert resp_updated["StartTime"] == given_start_date
    assert resp_updated["EndTime"] == given_end_date
    assert resp_updated["Parameters"] == given_parameters
    assert resp_updated["InputArtifacts"] == given_input_artifacts
    assert resp_updated["OutputArtifacts"] == given_output_artifacts
    assert resp_updated["LastModifiedTime"] >= resp_created["LastModifiedTime"]


@mock_aws
def test_update_trial_component_with_to_remove_options() -> None:
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    trial_component_name = "some-trial-component-name"
    client.create_trial_component(
        TrialComponentName=trial_component_name,
        Parameters={
            "param1": {"StringValue": "param1-value", "NumberValue": 123.0},
            "param2": {"StringValue": "param2-value", "NumberValue": 456.0},
        },
        InputArtifacts={
            "artifact1": {"MediaType": "text/plain", "Value": "artifact1-value"}
        },
        OutputArtifacts={
            "artifact2": {"MediaType": "text/plain", "Value": "artifact2-value"}
        },
    )

    client.update_trial_component(
        TrialComponentName=trial_component_name,
        ParametersToRemove=["param1"],
        InputArtifactsToRemove=["artifact1"],
        OutputArtifactsToRemove=["artifact2"],
    )
    resp_updated = client.describe_trial_component(
        TrialComponentName=trial_component_name
    )

    assert resp_updated["Parameters"].keys() == {"param2"}
    assert resp_updated["InputArtifacts"] == {}
    assert resp_updated["OutputArtifacts"] == {}


@mock_aws
def test_update_trial_component_should_return_an_error_if_trial_component_not_found() -> (
    None
):
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    with pytest.raises(ClientError) as ex:
        client.update_trial_component(
            TrialComponentName="not-found",
            DisplayName="new-display-name",
        )

    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["Error"]["Message"] == (
        "Could not find trial component 'arn:aws:sagemaker:us-east-1:123456789012:experiment-trial-component/not-found'"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
