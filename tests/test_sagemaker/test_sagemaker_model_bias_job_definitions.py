"""Unit tests for sagemaker-supported APIs."""

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_create_model_bias_job():
    client = boto3.client("sagemaker", region_name="us-west-2")

    response = client.create_model_bias_job_definition(
        JobDefinitionName="test-bias-job",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/SageMakerRole",
        ModelBiasAppSpecification={
            "ImageUri": f"{ACCOUNT_ID}.dkr.ecr.us-west-2.amazonaws.com/my-image:latest",
            "ConfigUri": "s3://my-bucket/bias-config.json",
        },
        ModelBiasJobInput={
            "EndpointInput": {
                "EndpointName": "test-endpoint",
                "LocalPath": "/opt/ml/processing/input/endpoint",
                "S3InputMode": "File",
                "S3DataDistributionType": "FullyReplicated",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://my-bucket/ground-truth-data",
            },
        },
        ModelBiasJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://my-bucket/bias-output",
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                },
            ],
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m5.xlarge",
                "VolumeSizeInGB": 10,
            },
        },
        NetworkConfig={
            "EnableInterContainerTrafficEncryption": False,
            "EnableNetworkIsolation": False,
        },
    )

    expected_job_definition_arn = f"arn:aws:sagemaker:us-west-2:{ACCOUNT_ID}:model-bias-job-definition/test-bias-job"
    assert response["JobDefinitionArn"] == expected_job_definition_arn


@mock_aws
def test_describe_model_bias_job():
    client = boto3.client("sagemaker", region_name="us-east-1")

    job_name = "test-model-bias-job"
    client.create_model_bias_job_definition(
        JobDefinitionName=job_name,
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/SageMakerRole",
        ModelBiasAppSpecification={
            "ImageUri": f"{ACCOUNT_ID}.dkr.ecr.us-west-2.amazonaws.com/my-image:latest",
            "ConfigUri": "s3://my-bucket/bias-config.json",
        },
        ModelBiasJobInput={
            "EndpointInput": {
                "EndpointName": "test-endpoint",
                "LocalPath": "/opt/ml/processing/input/endpoint",
                "S3InputMode": "File",
                "S3DataDistributionType": "FullyReplicated",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://my-bucket/ground-truth-data",
            },
        },
        ModelBiasJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://my-bucket/bias-output",
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                },
            ],
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m5.xlarge",
                "VolumeSizeInGB": 10,
            },
        },
        NetworkConfig={
            "EnableInterContainerTrafficEncryption": False,
            "EnableNetworkIsolation": False,
        },
    )
    response = client.describe_model_bias_job_definition(JobDefinitionName=job_name)
    assert response["JobDefinitionName"] == job_name
    assert (
        response["JobDefinitionArn"]
        == f"arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:model-bias-job-definition/{job_name}"
    )


@mock_aws
def test_list_model_bias_jobs():
    client = boto3.client("sagemaker", region_name="us-east-1")
    client.create_model_bias_job_definition(
        JobDefinitionName="test-bias-job-1",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/SageMakerRole",
        ModelBiasAppSpecification={
            "ImageUri": f"{ACCOUNT_ID}.dkr.ecr.us-west-2.amazonaws.com/my-image:latest",
            "ConfigUri": "s3://my-bucket/bias-config.json",
        },
        ModelBiasJobInput={
            "EndpointInput": {
                "EndpointName": "test-endpoint",
                "LocalPath": "/opt/ml/processing/input/endpoint",
                "S3InputMode": "File",
                "S3DataDistributionType": "FullyReplicated",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://my-bucket/ground-truth-data",
            },
        },
        ModelBiasJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://my-bucket/bias-output",
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                },
            ],
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m5.xlarge",
                "VolumeSizeInGB": 10,
            },
        },
        NetworkConfig={
            "EnableInterContainerTrafficEncryption": False,
            "EnableNetworkIsolation": False,
        },
    )
    client.create_model_bias_job_definition(
        JobDefinitionName="test-bias-job-2",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/SageMakerRole",
        ModelBiasAppSpecification={
            "ImageUri": f"{ACCOUNT_ID}.dkr.ecr.us-west-2.amazonaws.com/my-image:latest",
            "ConfigUri": "s3://my-bucket/bias-config.json",
        },
        ModelBiasJobInput={
            "EndpointInput": {
                "EndpointName": "test-endpoint",
                "LocalPath": "/opt/ml/processing/input/endpoint",
                "S3InputMode": "File",
                "S3DataDistributionType": "FullyReplicated",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://my-bucket/ground-truth-data",
            },
        },
        ModelBiasJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://my-bucket/bias-output",
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                },
            ],
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m5.xlarge",
                "VolumeSizeInGB": 10,
            },
        },
        NetworkConfig={
            "EnableInterContainerTrafficEncryption": False,
            "EnableNetworkIsolation": False,
        },
    )
    response = client.list_model_bias_job_definitions()

    job_names = [
        job["MonitoringJobDefinitionName"] for job in response["JobDefinitionSummaries"]
    ]
    assert "test-bias-job-1" in job_names
    assert "test-bias-job-2" in job_names


@mock_aws
def test_delete_model_bias_job():
    client = boto3.client("sagemaker", region_name="us-east-1")

    client.create_model_bias_job_definition(
        JobDefinitionName="test-bias-job",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/SageMakerRole",
        ModelBiasAppSpecification={
            "ImageUri": f"{ACCOUNT_ID}.dkr.ecr.us-west-2.amazonaws.com/my-image:latest",
            "ConfigUri": "s3://my-bucket/bias-config.json",
        },
        ModelBiasJobInput={
            "EndpointInput": {
                "EndpointName": "test-endpoint",
                "LocalPath": "/opt/ml/processing/input/endpoint",
                "S3InputMode": "File",
                "S3DataDistributionType": "FullyReplicated",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://my-bucket/ground-truth-data",
            },
        },
        ModelBiasJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://my-bucket/bias-output",
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                },
            ],
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m5.xlarge",
                "VolumeSizeInGB": 10,
            },
        },
        NetworkConfig={
            "EnableInterContainerTrafficEncryption": False,
            "EnableNetworkIsolation": False,
        },
    )
    client.delete_model_bias_job_definition(JobDefinitionName="test-bias-job")
    response = client.list_model_bias_job_definitions()
    job_names = [job["JobDefinitionName"] for job in response["JobDefinitionSummaries"]]
    assert "test-bias-job" not in job_names
