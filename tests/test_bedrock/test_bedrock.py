"""Unit tests for bedrock-supported APIs."""

from datetime import datetime
from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time

from moto import mock_aws, settings

DEFAULT_REGION = "us-east-1"

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_model_customization_job():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    # create a test s3 client and bucket
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")

    resp = client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    assert (
        resp["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob"
    )


@mock_aws
def test_get_model_customization_job():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    resp = client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.get_model_customization_job(jobIdentifier="testjob")

    assert (
        resp["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob"
    )
    assert resp["roleArn"] == "testrole"


@mock_aws
def test_get_model_invocation_logging_configuration():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    logging_config = {
        "cloudWatchConfig": {
            "logGroupName": "Test",
            "roleArn": "testrole",
            "largeDataDeliveryS3Config": {
                "bucketName": "testbucket",
            },
        },
        "s3Config": {
            "bucketName": "testconfigbucket",
        },
    }
    client.put_model_invocation_logging_configuration(loggingConfig=logging_config)
    response = client.get_model_invocation_logging_configuration()
    assert response["loggingConfig"]["cloudWatchConfig"]["logGroupName"] == "Test"
    assert response["loggingConfig"]["s3Config"]["bucketName"] == "testconfigbucket"


@mock_aws
def test_put_model_invocation_logging_configuration():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    logging_config = {
        "cloudWatchConfig": {
            "logGroupName": "Test",
            "roleArn": "testrole",
            "largeDataDeliveryS3Config": {
                "bucketName": "testbucket",
            },
        },
        "s3Config": {
            "bucketName": "testconfigbucket",
        },
    }
    client.put_model_invocation_logging_configuration(loggingConfig=logging_config)
    response = client.get_model_invocation_logging_configuration()
    assert response["loggingConfig"]["cloudWatchConfig"]["logGroupName"] == "Test"


@mock_aws
def test_tag_resource_model_customization_job():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    job_arn = client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.tag_resource(
        resourceARN=job_arn["jobArn"],
        tags=[
            {"key": "testkey", "value": "testvalue"},
            {"key": "testkey2", "value": "testvalue2"},
        ],
    )
    resp = client.list_tags_for_resource(resourceARN=job_arn["jobArn"])
    assert resp["tags"][0]["key"] == "testkey"
    assert resp["tags"][1]["value"] == "testvalue2"


@mock_aws
def test_untag_resource():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    job_arn = client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    client.tag_resource(
        resourceARN=job_arn["jobArn"],
        tags=[
            {"key": "testkey", "value": "testvalue"},
            {"key": "testkey2", "value": "testvalue2"},
        ],
    )
    client.untag_resource(resourceARN=job_arn["jobArn"], tagKeys=["testkey"])
    resp = client.list_tags_for_resource(resourceARN=job_arn["jobArn"])

    assert resp["tags"][0]["key"] == "testkey2"
    assert resp["tags"][0]["value"] == "testvalue2"


@mock_aws
def test_untag_resource_custom_model():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    job_arn = client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )

    client.tag_resource(
        resourceARN=job_arn["jobArn"],
        tags=[
            {"key": "testkey", "value": "testvalue"},
            {"key": "testkey2", "value": "testvalue2"},
        ],
    )
    resp = client.untag_resource(resourceARN=job_arn["jobArn"], tagKeys=["testkey"])
    resp = client.list_tags_for_resource(resourceARN=job_arn["jobArn"])

    assert resp["tags"][0]["key"] == "testkey2"
    assert resp["tags"][0]["value"] == "testvalue2"


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    job_arn = client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    client.tag_resource(
        resourceARN=job_arn["jobArn"],
        tags=[
            {"key": "testkey", "value": "testvalue"},
            {"key": "testkey2", "value": "testvalue2"},
        ],
    )
    resp = client.list_tags_for_resource(resourceARN=job_arn["jobArn"])

    assert resp["tags"][0]["key"] == "testkey"
    assert resp["tags"][1]["value"] == "testvalue2"


@mock_aws
def test_get_custom_model():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    job_arn = client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.get_custom_model(modelIdentifier="testmodel")
    assert (
        resp["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel"
    )
    assert resp["jobArn"] == job_arn["jobArn"]


@mock_aws
def test_get_custom_model_arn():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    job_arn = client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )

    resp = client.get_custom_model(modelIdentifier="testmodel")
    model = client.get_custom_model(modelIdentifier=resp["modelArn"])
    assert model["modelName"] == "testmodel"
    assert resp["jobArn"] == job_arn["jobArn"]


@mock_aws
def test_get_custom_model_arn_not_found():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )

    resp = client.get_custom_model(modelIdentifier="testmodel")
    with pytest.raises(ClientError) as ex:
        client.get_custom_model(modelIdentifier=(resp["modelArn"] + "no"))
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_custom_models():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel1",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    client.create_model_customization_job(
        jobName="testjob2",
        customModelName="testmodel2",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.list_custom_models()
    assert len(resp["modelSummaries"]) == 2
    assert (
        resp["modelSummaries"][0]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel1"
    )
    assert (
        resp["modelSummaries"][1]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel2"
    )


@mock_aws
def test_list_model_customization_jobs():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel1",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    client.create_model_customization_job(
        jobName="testjob2",
        customModelName="testmodel2",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.list_model_customization_jobs()
    assert len(resp["modelCustomizationJobSummaries"]) == 2
    assert (
        resp["modelCustomizationJobSummaries"][0]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob"
    )
    assert (
        resp["modelCustomizationJobSummaries"][1]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob2"
    )


@mock_aws
def test_delete_custom_model():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    client.delete_custom_model(modelIdentifier="testmodel")

    with pytest.raises(ClientError) as ex:
        client.get_custom_model(modelIdentifier="testmodel")
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_delete_custom_model_not_found():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )

    with pytest.raises(ClientError) as ex:
        client.delete_custom_model(modelIdentifier="testmodel1")
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_stop_model_customization_job():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.stop_model_customization_job(jobIdentifier="testjob")
    resp = client.get_model_customization_job(jobIdentifier="testjob")
    assert resp["status"] == "Stopped"


@mock_aws
def test_delete_model_invocation_logging_configuration():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    logging_config = {
        "cloudWatchConfig": {
            "logGroupName": "Test",
            "roleArn": "testrole",
            "largeDataDeliveryS3Config": {
                "bucketName": "testbucket",
            },
        },
        "s3Config": {
            "bucketName": "testconfigbucket",
        },
    }
    client.put_model_invocation_logging_configuration(loggingConfig=logging_config)
    client.delete_model_invocation_logging_configuration()
    assert client.get_model_invocation_logging_configuration()["loggingConfig"] == {}


@mock_aws
def test_create_model_customization_job_bad_training_data_config():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    # create a test s3 client and bucket
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    with pytest.raises(ClientError) as ex:
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "aws:s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_create_model_customization_job_bad_validation_data_config():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    # create a test s3 client and bucket
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    with pytest.raises(ClientError) as ex:
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            validationDataConfig={
                "validators": [{"s3Uri": "aws:s3://validation_bucket"}]
            },
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_create_model_customization_job_bad_output_data_config():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    # create a test s3 client and bucket
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    with pytest.raises(ClientError) as ex:
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            validationDataConfig={"validators": [{"s3Uri": "s3://validation_bucket"}]},
            outputDataConfig={"s3Uri": "aws:s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_create_model_customization_job_duplicate_job_name():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    # create a test s3 client and bucket
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        validationDataConfig={"validators": [{"s3Uri": "s3://validation_bucket"}]},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with pytest.raises(ClientError) as ex:
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel1",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            validationDataConfig={"validators": [{"s3Uri": "s3://validation_bucket"}]},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    assert ex.value.response["Error"]["Code"] == "ResourceInUseException"


@mock_aws
def test_create_model_customization_job_duplicate_model_name():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    # create a test s3 client and bucket
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    client.create_model_customization_job(
        jobName="testjob1",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        validationDataConfig={"validators": [{"s3Uri": "s3://validation_bucket"}]},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with pytest.raises(ClientError) as ex:
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            validationDataConfig={"validators": [{"s3Uri": "s3://validation_bucket"}]},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    assert ex.value.response["Error"]["Code"] == "ResourceInUseException"


@mock_aws
def test_create_model_customization_job_tags():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    # create a test s3 client and bucket
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    resp = client.create_model_customization_job(
        jobName="testjob1",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        validationDataConfig={"validators": [{"s3Uri": "s3://validation_bucket"}]},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
        jobTags=[{"key": "test", "value": "testvalue"}],
        customModelTags=[{"key": "modeltest", "value": "modeltestvalue"}],
    )
    job_tags = client.list_tags_for_resource(resourceARN=resp["jobArn"])
    model_arn = client.list_custom_models()["modelSummaries"][0]["modelArn"]
    model_tags = client.list_tags_for_resource(resourceARN=model_arn)
    assert job_tags["tags"] == [{"key": "test", "value": "testvalue"}]
    assert model_tags["tags"] == [{"key": "modeltest", "value": "modeltestvalue"}]


@mock_aws
def test_get_model_customization_job_not_found():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with pytest.raises(ClientError) as ex:
        client.get_model_customization_job(jobIdentifier="testjob1")
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_stop_model_customization_job_not_found():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with pytest.raises(ClientError) as ex:
        client.stop_model_customization_job(jobIdentifier="testjob1")
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_model_customization_jobs_max_results():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel1",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    client.create_model_customization_job(
        jobName="testjob2",
        customModelName="testmodel2",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.list_model_customization_jobs(maxResults=1)
    assert len(resp["modelCustomizationJobSummaries"]) == 1
    assert (
        resp["modelCustomizationJobSummaries"][0]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob"
    )


@mock_aws
def test_list_model_customization_jobs_name_contains():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel1",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    client.create_model_customization_job(
        jobName="testjob2",
        customModelName="testmodel2",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.list_model_customization_jobs(nameContains="testjob2")
    assert len(resp["modelCustomizationJobSummaries"]) == 1
    assert (
        resp["modelCustomizationJobSummaries"][0]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob2"
    )


@mock_aws
def test_list_model_customization_jobs_creation_time_before():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    with freeze_time("2022-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel1",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    client.create_model_customization_job(
        jobName="testjob2",
        customModelName="testmodel2",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.list_model_customization_jobs(
        creationTimeBefore=datetime(2022, 2, 1, 12, 0, 0)
    )
    assert len(resp["modelCustomizationJobSummaries"]) == 1
    assert (
        resp["modelCustomizationJobSummaries"][0]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob"
    )


@mock_aws
def test_list_model_customization_jobs_creation_time_after():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    with freeze_time("2022-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel1",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    client.create_model_customization_job(
        jobName="testjob2",
        customModelName="testmodel2",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.list_model_customization_jobs(
        creationTimeAfter=datetime(2022, 2, 1, 12, 0, 0)
    )
    assert len(resp["modelCustomizationJobSummaries"]) == 1
    assert (
        resp["modelCustomizationJobSummaries"][0]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob2"
    )


@mock_aws
def test_list_model_customization_jobs_status():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel1",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    client.create_model_customization_job(
        jobName="testjob2",
        customModelName="testmodel2",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.list_model_customization_jobs(statusEquals="InProgress")
    assert len(resp["modelCustomizationJobSummaries"]) == 2
    assert (
        resp["modelCustomizationJobSummaries"][0]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob"
    )
    assert (
        resp["modelCustomizationJobSummaries"][1]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob2"
    )


@mock_aws
def test_list_model_customization_jobs_ascending_sort():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    with freeze_time("2022-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel1",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    client.create_model_customization_job(
        jobName="testjob3",
        customModelName="testmodel3",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with freeze_time("2023-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob2",
            customModelName="testmodel2",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    resp = client.list_model_customization_jobs(
        sortBy="CreationTime", sortOrder="Ascending"
    )
    assert len(resp["modelCustomizationJobSummaries"]) == 3
    assert (
        resp["modelCustomizationJobSummaries"][0]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob"
    )
    assert (
        resp["modelCustomizationJobSummaries"][1]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob2"
    )
    assert (
        resp["modelCustomizationJobSummaries"][2]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob3"
    )


@mock_aws
def test_list_model_customization_jobs_descending_sort():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    with freeze_time("2022-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel1",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    client.create_model_customization_job(
        jobName="testjob3",
        customModelName="testmodel3",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with freeze_time("2023-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob2",
            customModelName="testmodel2",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    resp = client.list_model_customization_jobs(
        sortBy="CreationTime", sortOrder="Descending"
    )
    assert len(resp["modelCustomizationJobSummaries"]) == 3
    assert (
        resp["modelCustomizationJobSummaries"][0]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob3"
    )
    assert (
        resp["modelCustomizationJobSummaries"][1]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob2"
    )
    assert (
        resp["modelCustomizationJobSummaries"][2]["jobArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/testjob"
    )


@mock_aws
def test_list_model_customization_jobs_bad_sort_order():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as ex:
        client.list_model_customization_jobs(
            sortBy="CreationTime", sortOrder="decending"
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_list_model_customization_jobs_bad_sort_by():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    with freeze_time("2022-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel1",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    client.create_model_customization_job(
        jobName="testjob3",
        customModelName="testmodel3",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with freeze_time("2023-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob2",
            customModelName="testmodel2",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    with pytest.raises(ClientError) as ex:
        client.list_model_customization_jobs(
            sortBy="Creationime", sortOrder="Descending"
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_get_model_invocation_logging_configuration_empty():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    response = client.get_model_invocation_logging_configuration()
    assert response["loggingConfig"] == {}


@mock_aws
def test_list_custom_models_max_results():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    client.create_model_customization_job(
        jobName="testjob2",
        customModelName="testmodel2",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.list_custom_models(maxResults=1)
    assert len(resp["modelSummaries"]) == 1
    assert (
        resp["modelSummaries"][0]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel"
    )


@mock_aws
def test_list_custom_models_name_contains():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel1",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    client.create_model_customization_job(
        jobName="testjob2",
        customModelName="testmodel2",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.list_custom_models(nameContains="testjob2")
    assert len(resp["modelSummaries"]) == 1
    assert (
        resp["modelSummaries"][0]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel2"
    )


@mock_aws
def test_list_custom_models_creation_time_before():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    with freeze_time("2022-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    client.create_model_customization_job(
        jobName="testjob2",
        customModelName="testmodel2",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.list_custom_models(creationTimeBefore=datetime(2022, 2, 1, 12, 0, 0))
    assert len(resp["modelSummaries"]) == 1
    assert (
        resp["modelSummaries"][0]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel"
    )


@mock_aws
def test_list_custom_models_creation_time_after():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    with freeze_time("2022-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel1",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    client.create_model_customization_job(
        jobName="testjob2",
        customModelName="testmodel2",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.list_custom_models(creationTimeAfter=datetime(2022, 2, 1, 12, 0, 0))
    assert len(resp["modelSummaries"]) == 1
    assert (
        resp["modelSummaries"][0]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel2"
    )


@mock_aws
def test_list_custom_models_ascending_sort():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    with freeze_time("2022-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    client.create_model_customization_job(
        jobName="testjob3",
        customModelName="testmodel3",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with freeze_time("2023-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob2",
            customModelName="testmodel2",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    resp = client.list_custom_models(sortBy="CreationTime", sortOrder="Ascending")
    assert len(resp["modelSummaries"]) == 3
    assert (
        resp["modelSummaries"][0]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel"
    )
    assert (
        resp["modelSummaries"][1]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel2"
    )
    assert (
        resp["modelSummaries"][2]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel3"
    )


@mock_aws
def test_list_custom_models_descending_sort():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    with freeze_time("2022-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    client.create_model_customization_job(
        jobName="testjob3",
        customModelName="testmodel3",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with freeze_time("2023-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob2",
            customModelName="testmodel2",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    resp = client.list_custom_models(sortBy="CreationTime", sortOrder="Descending")
    assert len(resp["modelSummaries"]) == 3
    assert (
        resp["modelSummaries"][0]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel3"
    )
    assert (
        resp["modelSummaries"][1]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel2"
    )
    assert (
        resp["modelSummaries"][2]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel"
    )


@mock_aws
def test_list_custom_models_bad_sort_order():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    with freeze_time("2022-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel1",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    client.create_model_customization_job(
        jobName="testjob3",
        customModelName="testmodel3",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with freeze_time("2023-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob2",
            customModelName="testmodel2",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    with pytest.raises(ClientError) as ex:
        client.list_custom_models(sortBy="CreationTime", sortOrder="decending")
    assert ex.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_list_custom_models_bad_sort_by():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    with freeze_time("2022-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob",
            customModelName="testmodel1",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    client.create_model_customization_job(
        jobName="testjob3",
        customModelName="testmodel3",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with freeze_time("2023-01-01 12:00:00"):
        client.create_model_customization_job(
            jobName="testjob2",
            customModelName="testmodel2",
            roleArn="testrole",
            baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
            trainingDataConfig={"s3Uri": "s3://training_bucket"},
            outputDataConfig={"s3Uri": "s3://output_bucket"},
            hyperParameters={"learning_rate": "0.01"},
        )
    with pytest.raises(ClientError) as ex:
        client.list_custom_models(sortBy="Creationime", sortOrder="Descending")
    assert ex.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_list_custom_models_base_model_arn_equals():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    client.create_model_customization_job(
        jobName="testjob2",
        customModelName="testmodel2",
        roleArn="testrole",
        baseModelIdentifier="amazon.titan-text-lite-v1",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    resp = client.list_custom_models(
        baseModelArnEquals="arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
    )
    assert len(resp["modelSummaries"]) == 1
    assert (
        resp["modelSummaries"][0]["modelArn"]
        == "arn:aws:bedrock:us-east-1:123456789012:custom-model/testmodel"
    )


@mock_aws
def test_tag_resource_not_found():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    job_arn = client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with pytest.raises(ClientError) as ex:
        client.tag_resource(
            resourceARN=job_arn["jobArn"] + "no",
            tags=[
                {"key": "testkey", "value": "testvalue"},
                {"key": "testkey2", "value": "testvalue2"},
            ],
        )
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_tag_resource_too_many():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    job_arn = client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    with pytest.raises(ClientError) as ex:
        client.tag_resource(
            resourceARN=job_arn["jobArn"],
            tags=[{"key": f"testkey{i}", "value": f"testvalue{i}"} for i in range(51)],
        )
    assert ex.value.response["Error"]["Code"] == "TooManyTagsException"


@mock_aws
def test_untag_resource_not_found():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    job_arn = client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )

    client.tag_resource(
        resourceARN=job_arn["jobArn"],
        tags=[
            {"key": "testkey", "value": "testvalue"},
            {"key": "testkey2", "value": "testvalue2"},
        ],
    )
    with pytest.raises(ClientError) as ex:
        client.untag_resource(resourceARN=job_arn["jobArn"] + "no", tagKeys=["testkey"])
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_tags_for_resource_not_found():
    client = boto3.client("bedrock", region_name=DEFAULT_REGION)
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION)
    s3_client.create_bucket(Bucket="training_bucket")
    s3_client.create_bucket(Bucket="output_bucket")
    job_arn = client.create_model_customization_job(
        jobName="testjob",
        customModelName="testmodel",
        roleArn="testrole",
        baseModelIdentifier="anthropic.claude-3-sonnet-20240229-v1:0",
        trainingDataConfig={"s3Uri": "s3://training_bucket"},
        outputDataConfig={"s3Uri": "s3://output_bucket"},
        hyperParameters={"learning_rate": "0.01"},
    )
    client.tag_resource(
        resourceARN=job_arn["jobArn"],
        tags=[
            {"key": "testkey", "value": "testvalue"},
            {"key": "testkey2", "value": "testvalue2"},
        ],
    )
    with pytest.raises(ClientError) as ex:
        client.list_tags_for_resource(resourceARN=job_arn["jobArn"] + "no")
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"
