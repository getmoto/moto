"""Unit tests for sagemakermetrics-supported APIs."""
from datetime import datetime

import boto3

from moto import mock_aws

# @mock_aws
def test_batch_put_metrics():
    trial_component_name = "some-trial-component-name"
    client_sagemaker = boto3.client(
        "sagemaker",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
        region_name="eu-west-1"
    )
    # client_sagemaker.create_trial_component(TrialComponentName=trial_component_name)

    client = boto3.client(
        "sagemaker-metrics",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
        region_name="eu-west-1"
    )
    resp = client.batch_put_metrics(
        TrialComponentName=trial_component_name,
        MetricData=[{
            'MetricName': 'some-metric-name',
            'Timestamp': datetime(2015, 1, 1),
            'Step': 123,
            'Value': 123.0
        },]
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

@mock_aws
def test_batch_put_metrics_should_return_validation_error_if_trial_component_not_found():
    trial_component_name = "some-trial-component-name-not-existing"
    client = boto3.client(
        "sagemaker-metrics",
        region_name="eu-west-1"
    )
    resp = client.batch_put_metrics(
        TrialComponentName=trial_component_name,
        MetricData=[{
            'MetricName': 'some-metric-name',
            'Timestamp': datetime(2015, 1, 1),
            'Step': 0,
            'Value': 123.0,
        }]
    )

    assert resp.get("Errors") is not None
    assert resp["Errors"][0]["Code"] == "VALIDATION_ERROR"

