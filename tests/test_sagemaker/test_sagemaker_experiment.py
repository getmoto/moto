import boto3

from moto import mock_sagemaker
from moto.sts.models import ACCOUNT_ID

TEST_REGION_NAME = "us-east-1"


@mock_sagemaker
def test_create_experiment():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    experiment_name = "some-experiment-name"

    resp = client.create_experiment(ExperimentName=experiment_name)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = client.list_experiments()

    assert len(resp["ExperimentSummaries"]) == 1
    assert resp["ExperimentSummaries"][0]["ExperimentName"] == experiment_name
    assert (
        resp["ExperimentSummaries"][0]["ExperimentArn"]
        == f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:experiment/{experiment_name}"
    )


@mock_sagemaker
def test_list_experiments():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    experiment_names = [f"some-experiment-name-{i}" for i in range(10)]

    for experiment_name in experiment_names:
        resp = client.create_experiment(ExperimentName=experiment_name)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = client.list_experiments(MaxResults=1)

    assert len(resp["ExperimentSummaries"]) == 1

    next_token = resp["NextToken"]

    resp = client.list_experiments(MaxResults=2, NextToken=next_token)

    assert len(resp["ExperimentSummaries"]) == 2

    next_token = resp["NextToken"]

    resp = client.list_experiments(NextToken=next_token)

    assert len(resp["ExperimentSummaries"]) == 7

    assert resp.get("NextToken") is None


@mock_sagemaker
def test_delete_experiment():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    experiment_name = "some-experiment-name"

    resp = client.create_experiment(ExperimentName=experiment_name)

    resp = client.delete_experiment(ExperimentName=experiment_name)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = client.list_experiments()

    assert len(resp["ExperimentSummaries"]) == 0


@mock_sagemaker
def test_add_tags_to_experiment():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    experiment_name = "some-experiment-name"

    resp = client.create_experiment(ExperimentName=experiment_name)

    resp = client.describe_experiment(ExperimentName=experiment_name)

    arn = resp["ExperimentArn"]

    tags = [{"Key": "name", "Value": "value"}]

    client.add_tags(ResourceArn=arn, Tags=tags)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = client.list_tags(ResourceArn=arn)

    assert resp["Tags"] == tags


@mock_sagemaker
def test_delete_tags_to_experiment():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    experiment_name = "some-experiment-name"

    resp = client.create_experiment(ExperimentName=experiment_name)

    resp = client.describe_experiment(ExperimentName=experiment_name)

    arn = resp["ExperimentArn"]

    tags = [{"Key": "name", "Value": "value"}]

    client.add_tags(ResourceArn=arn, Tags=tags)

    client.delete_tags(ResourceArn=arn, TagKeys=[i["Key"] for i in tags])

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = client.list_tags(ResourceArn=arn)

    assert resp["Tags"] == []
