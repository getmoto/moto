"""Unit tests for sagemakermetrics-supported APIs."""

import datetime

import boto3

from moto import mock_aws


@mock_aws
def test_batch_put_metrics():
    trial_component_name = "some-trial-component-name"
    client_sagemaker = boto3.client("sagemaker", region_name="eu-west-1")
    client_sagemaker.create_trial_component(TrialComponentName=trial_component_name)
    describe_before_metrics = client_sagemaker.describe_trial_component(
        TrialComponentName=trial_component_name
    )

    client = boto3.client("sagemaker-metrics", region_name="eu-west-1")
    given_datetime = datetime.datetime(2024, 4, 21, 0, 0, 0)
    resp = client.batch_put_metrics(
        TrialComponentName=trial_component_name,
        MetricData=[
            {
                "MetricName": "some-metric-name",
                "Timestamp": given_datetime,
                "Step": 0,
                "Value": 123.0,
            },
        ],
    )
    describe_after_metrics = client_sagemaker.describe_trial_component(
        TrialComponentName=trial_component_name
    )

    assert describe_before_metrics["Metrics"] == []
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["Errors"] == []
    assert describe_after_metrics["Metrics"][0]["MetricName"] == "some-metric-name"
    assert (
        describe_after_metrics["Metrics"][0]["SourceArn"]
        == "arn:aws:sagemaker:eu-west-1:123456789012:experiment-trial-component/some-trial-component-name"
    )
    assert describe_after_metrics["Metrics"][0]["TimeStamp"] == given_datetime
    assert describe_after_metrics["Metrics"][0]["Max"] == 123.0
    assert describe_after_metrics["Metrics"][0]["Min"] == 123.0
    assert describe_after_metrics["Metrics"][0]["Last"] == 123.0
    assert describe_after_metrics["Metrics"][0]["Count"] == 1
    assert describe_after_metrics["Metrics"][0]["Avg"] == 123.0
    assert describe_after_metrics["Metrics"][0]["StdDev"] == 0.0


@mock_aws
def test_batch_put_metrics_should_return_validation_error_if_trial_component_not_found():
    trial_component_name = "some-trial-component-name-not-existing"
    client = boto3.client("sagemaker-metrics", region_name="eu-west-1")
    resp = client.batch_put_metrics(
        TrialComponentName=trial_component_name,
        MetricData=[
            {
                "MetricName": "some-metric-name",
                "Timestamp": datetime.datetime(2015, 1, 1),
                "Step": 0,
                "Value": 123.0,
            }
        ],
    )

    assert resp.get("Errors") is not None
    assert resp["Errors"][0]["Code"] == "VALIDATION_ERROR"
