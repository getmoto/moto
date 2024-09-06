import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

TEST_REGION_NAME = "us-east-1"


@pytest.fixture(name="sagemaker_client")
def fixture_sagemaker_client():
    with mock_aws():
        yield boto3.client("sagemaker", region_name=TEST_REGION_NAME)


def test_search(sagemaker_client):
    experiment_name = "experiment_name"
    trial_component_name = "trial_component_name"
    trial_name = "trial_name"
    _set_up_trial_component(
        sagemaker_client,
        experiment_name=experiment_name,
        trial_component_name=trial_component_name,
        trial_name=trial_name,
    )

    resp = sagemaker_client.search(Resource="ExperimentTrialComponent")
    assert len(resp["Results"]) == 2

    resp = sagemaker_client.describe_trial_component(
        TrialComponentName=trial_component_name
    )
    trial_component_arn = resp["TrialComponentArn"]

    tags = [{"Key": "key-name", "Value": "some-value"}]
    sagemaker_client.add_tags(ResourceArn=trial_component_arn, Tags=tags)

    resp = sagemaker_client.search(
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

    resp = sagemaker_client.search(Resource="Experiment")
    assert len(resp["Results"]) == 1
    assert resp["Results"][0]["Experiment"]["ExperimentName"] == experiment_name

    resp = sagemaker_client.search(Resource="ExperimentTrial")
    assert len(resp["Results"]) == 1
    assert resp["Results"][0]["Trial"]["TrialName"] == trial_name


def test_search_trial_component_with_experiment_name(sagemaker_client):
    experiment_name = "experiment_name"
    trial_component_name = "trial_component_name"
    _set_up_trial_component(
        sagemaker_client,
        experiment_name=experiment_name,
        trial_component_name=trial_component_name,
    )

    resp = sagemaker_client.search(Resource="ExperimentTrialComponent")
    assert len(resp["Results"]) == 2

    resp = sagemaker_client.describe_trial_component(
        TrialComponentName=trial_component_name
    )
    trial_component_arn = resp["TrialComponentArn"]

    tags = [{"Key": "key-name", "Value": "some-value"}]
    sagemaker_client.add_tags(ResourceArn=trial_component_arn, Tags=tags)

    with pytest.raises(ClientError) as ex:
        sagemaker_client.search(
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

    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert (
        ex.value.response["Error"]["Message"] == "Unknown property name: ExperimentName"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


def test_search_experiments_with_filter(sagemaker_client):
    experiment_name = "experiment_name"
    trial_component_name = "trial_component_name"
    _set_up_trial_component(
        sagemaker_client,
        experiment_name=experiment_name,
        trial_component_name=trial_component_name,
    )

    _verify_search_results(
        {"Name": "ExperimentName", "Operator": "Contains", "Value": "_DEV"}, 0
    )
    _verify_search_results(
        {"Name": "ExperimentName", "Operator": "Contains", "Value": "_name"}, 1
    )
    _verify_search_results(
        {"Name": "ExperimentName", "Operator": "Equals", "Value": "_name"}, 0
    )
    _verify_search_results(
        {"Name": "ExperimentName", "Operator": "Equals", "Value": experiment_name}, 1
    )
    _verify_search_results(
        {"Name": "ExperimentName", "Operator": "NotEquals", "Value": experiment_name}, 0
    )
    _verify_search_results(
        {"Name": "ExperimentName", "Operator": "NotEquals", "Value": "else"}, 1
    )


def test_search_model_package_groups_with_filter(sagemaker_client):
    sagemaker_client.create_model_package_group(
        ModelPackageGroupName="mpg_DEV",
        ModelPackageGroupDescription="test-model-package-group-description",
    )

    _verify_search_results(
        {"Name": "ModelPackageGroupName", "Operator": "Contains", "Value": "_DEV"},
        1,
        resource="ModelPackageGroup",
    )
    _verify_search_results(
        {"Name": "ModelPackageGroupName", "Operator": "Contains", "Value": "_PROD"},
        0,
        resource="ModelPackageGroup",
    )


def _verify_search_results(_filter, nr_of_results, resource="Experiment"):
    sagemaker_client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)
    results = sagemaker_client.search(
        Resource=resource, SearchExpression={"Filters": [_filter]}
    )["Results"]
    assert len(results) == nr_of_results


def _set_up_trial_component(
    sagemaker_client,
    experiment_name="some-experiment-name",
    trial_component_name="some-trial-component-name",
    trial_name="some-trial-name",
    another_trial_component_name="another-trial-component-name",
):
    sagemaker_client.create_experiment(ExperimentName=experiment_name)
    sagemaker_client.create_trial(ExperimentName=experiment_name, TrialName=trial_name)
    sagemaker_client.create_trial_component(TrialComponentName=trial_component_name)
    sagemaker_client.create_trial_component(
        TrialComponentName=another_trial_component_name
    )
