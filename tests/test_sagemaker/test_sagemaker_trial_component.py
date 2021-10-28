import boto3

from moto import mock_sagemaker
from moto.sts.models import ACCOUNT_ID

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
def test_associate_trial_component():
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

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = client.list_trial_components(TrialName=trial_name)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert (
        resp["TrialComponentSummaries"][0]["TrialComponentName"] == trial_component_name
    )
