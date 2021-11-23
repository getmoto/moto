import boto3
import pytest

from botocore.exceptions import ClientError

from moto import mock_sagemaker

TEST_REGION_NAME = "us-east-1"


@mock_sagemaker
def test_search():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    experiment_name = "some-experiment-name"

    resp = client.create_experiment(ExperimentName=experiment_name)

    trial_name = "some-trial-name"

    resp = client.create_trial(ExperimentName=experiment_name, TrialName=trial_name)

    trial_component_name = "some-trial-component-name"
    another_trial_component_name = "another-trial-component-name"

    resp = client.create_trial_component(TrialComponentName=trial_component_name)
    resp = client.create_trial_component(
        TrialComponentName=another_trial_component_name
    )

    resp = client.search(Resource="ExperimentTrialComponent")

    assert len(resp["Results"]) == 2

    resp = client.describe_trial_component(TrialComponentName=trial_component_name)

    trial_component_arn = resp["TrialComponentArn"]

    tags = [{"Key": "key-name", "Value": "some-value"}]

    client.add_tags(ResourceArn=trial_component_arn, Tags=tags)

    resp = client.search(
        Resource="ExperimentTrialComponent",
        SearchExpression={
            "Filters": [
                {"Name": "Tags.key-name", "Operator": "Equals", "Value": "some-value"}
            ]
        },
    )

    assert len(resp["Results"]) == 1
    assert (
        resp["Results"][0]["TrialComponent"]["TrialComponentName"]
        == trial_component_name
    )

    resp = client.search(Resource="Experiment")
    assert len(resp["Results"]) == 1
    assert resp["Results"][0]["Experiment"]["ExperimentName"] == experiment_name

    resp = client.search(Resource="ExperimentTrial")
    assert len(resp["Results"]) == 1
    assert resp["Results"][0]["Trial"]["TrialName"] == trial_name


@mock_sagemaker
def test_search_trial_component_with_experiment_name():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    experiment_name = "some-experiment-name"

    resp = client.create_experiment(ExperimentName=experiment_name)

    trial_name = "some-trial-name"

    resp = client.create_trial(ExperimentName=experiment_name, TrialName=trial_name)

    trial_component_name = "some-trial-component-name"
    another_trial_component_name = "another-trial-component-name"

    resp = client.create_trial_component(TrialComponentName=trial_component_name)
    resp = client.create_trial_component(
        TrialComponentName=another_trial_component_name
    )

    resp = client.search(Resource="ExperimentTrialComponent")

    assert len(resp["Results"]) == 2

    resp = client.describe_trial_component(TrialComponentName=trial_component_name)

    trial_component_arn = resp["TrialComponentArn"]

    tags = [{"Key": "key-name", "Value": "some-value"}]

    client.add_tags(ResourceArn=trial_component_arn, Tags=tags)

    with pytest.raises(ClientError) as ex:
        client.search(
            Resource="ExperimentTrialComponent",
            SearchExpression={
                "Filters": [
                    {
                        "Name": "ExperimentName",
                        "Operator": "Equals",
                        "Value": experiment_name,
                    }
                ]
            },
        )

    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.equal(
        "Unknown property name: ExperimentName"
    )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
