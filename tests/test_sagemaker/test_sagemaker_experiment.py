import boto3
import pytest

from moto import mock_sagemaker
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

TEST_REGION_NAME = "us-east-1"
TEST_EXPERIMENT_NAME = "MyExperimentName"


@pytest.fixture
def sagemaker_client():
    return boto3.client("sagemaker", region_name=TEST_REGION_NAME)


@mock_sagemaker
def test_create_experiment(sagemaker_client):
    resp = sagemaker_client.create_experiment(ExperimentName=TEST_EXPERIMENT_NAME)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = sagemaker_client.list_experiments()

    assert len(resp["ExperimentSummaries"]) == 1
    assert resp["ExperimentSummaries"][0]["ExperimentName"] == TEST_EXPERIMENT_NAME
    assert (
        resp["ExperimentSummaries"][0]["ExperimentArn"]
        == f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:experiment/{TEST_EXPERIMENT_NAME}"
    )


@mock_sagemaker
def test_list_experiments(sagemaker_client):

    experiment_names = [f"some-experiment-name-{i}" for i in range(10)]

    for experiment_name in experiment_names:
        resp = sagemaker_client.create_experiment(ExperimentName=experiment_name)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = sagemaker_client.list_experiments(MaxResults=1)

    assert len(resp["ExperimentSummaries"]) == 1

    next_token = resp["NextToken"]

    resp = sagemaker_client.list_experiments(MaxResults=2, NextToken=next_token)

    assert len(resp["ExperimentSummaries"]) == 2

    next_token = resp["NextToken"]

    resp = sagemaker_client.list_experiments(NextToken=next_token)

    assert len(resp["ExperimentSummaries"]) == 7

    assert resp.get("NextToken") is None


@mock_sagemaker
def test_delete_experiment(sagemaker_client):
    sagemaker_client.create_experiment(ExperimentName=TEST_EXPERIMENT_NAME)

    resp = sagemaker_client.delete_experiment(ExperimentName=TEST_EXPERIMENT_NAME)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = sagemaker_client.list_experiments()

    assert len(resp["ExperimentSummaries"]) == 0


@mock_sagemaker
def test_add_tags_to_experiment(sagemaker_client):
    sagemaker_client.create_experiment(ExperimentName=TEST_EXPERIMENT_NAME)

    resp = sagemaker_client.describe_experiment(ExperimentName=TEST_EXPERIMENT_NAME)

    arn = resp["ExperimentArn"]

    tags = [{"Key": "name", "Value": "value"}]

    sagemaker_client.add_tags(ResourceArn=arn, Tags=tags)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = sagemaker_client.list_tags(ResourceArn=arn)

    assert resp["Tags"] == tags


@mock_sagemaker
def test_delete_tags_to_experiment(sagemaker_client):
    sagemaker_client.create_experiment(ExperimentName=TEST_EXPERIMENT_NAME)

    resp = sagemaker_client.describe_experiment(ExperimentName=TEST_EXPERIMENT_NAME)

    arn = resp["ExperimentArn"]

    tags = [{"Key": "name", "Value": "value"}]

    sagemaker_client.add_tags(ResourceArn=arn, Tags=tags)

    sagemaker_client.delete_tags(ResourceArn=arn, TagKeys=[i["Key"] for i in tags])

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = sagemaker_client.list_tags(ResourceArn=arn)

    assert resp["Tags"] == []
