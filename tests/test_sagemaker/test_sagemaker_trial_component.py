import uuid

import boto3
import pytest

from botocore.exceptions import ClientError

from moto import mock_sagemaker
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

TEST_REGION_NAME = "us-east-1"


@mock_sagemaker
def test_create__trial_component():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    trial_component_name = "some-trial-component-name"

    resp = client.create_trial_component(TrialComponentName=trial_component_name)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = client.list_trial_components()

    assert len(resp["TrialComponentSummaries"]) == 1
    assert (
        resp["TrialComponentSummaries"][0]["TrialComponentName"] == trial_component_name
    )
    assert (
        resp["TrialComponentSummaries"][0]["TrialComponentArn"]
        == f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:experiment-trial-component/{trial_component_name}"
    )


@mock_sagemaker
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


@mock_sagemaker
def test_delete__trial_component():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    trial_component_name = "some-trial-component-name"

    resp = client.create_trial_component(TrialComponentName=trial_component_name)
    resp = client.delete_trial_component(TrialComponentName=trial_component_name)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = client.list_trial_components()

    assert len(resp["TrialComponentSummaries"]) == 0


@mock_sagemaker
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


@mock_sagemaker
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


@mock_sagemaker
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


@mock_sagemaker
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
    assert (
        resp["TrialComponentArn"]
        == f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:experiment-trial-component/{trial_component_name}"
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

    ex.value.response["Error"]["Code"].should.equal("ResourceNotFound")
    ex.value.response["Error"]["Message"].should.equal(
        f"Trial 'arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:experiment-trial/does-not-exist' does not exist."
    )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_sagemaker
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
    assert (
        resp["TrialComponentArn"]
        == f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:experiment-trial-component/{trial_component_name}"
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
    assert (
        resp["TrialComponentArn"]
        == f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:experiment-trial-component/does-not-exist"
    )
    assert (
        resp["TrialArn"]
        == f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:experiment-trial/does-not-exist"
    )
