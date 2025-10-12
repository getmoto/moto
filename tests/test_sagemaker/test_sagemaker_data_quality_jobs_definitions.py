"""Unit tests for sagemaker-supported APIs."""

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_create_data_quality_job():
    client = boto3.client("sagemaker", region_name="us-east-1")

    job_name = "test-data-quality-job"
    response = client.create_data_quality_job_definition(
        JobDefinitionName=job_name,
        DataQualityAppSpecification={
            "ImageUri": "{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/my-image:latest",
            "ContainerEntrypoint": ["python", "script.py"],
            "ContainerArguments": ["--arg1", "value1"],
        },
        DataQualityBaselineConfig={
            "ConstraintsResource": {"S3Uri": "s3://my-bucket/constraints.json"},
            "StatisticsResource": {"S3Uri": "s3://my-bucket/statistics.json"},
        },
        DataQualityJobInput={
            "EndpointInput": {
                "EndpointName": "my-endpoint",
                "LocalPath": "/opt/ml/processing/input",
                "S3InputMode": "File",
                "S3DataDistributionType": "FullyReplicated",
                "FeaturesAttribute": "my-features",
                "InferenceAttribute": "my-inference",
                "ProbabilityAttribute": "my-probability",
            }
        },
        DataQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://my-bucket/output",
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    }
                }
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m5.xlarge",
                "VolumeSizeInGB": 20,
            }
        },
        NetworkConfig={
            "EnableInterContainerTrafficEncryption": False,
            "EnableNetworkIsolation": False,
            "VpcConfig": {
                "SecurityGroupIds": ["sg-12345678"],
                "Subnets": ["subnet-12345678"],
            },
        },
        RoleArn="arn:aws:iam::{ACCOUNT_ID}:role/SageMakerRole",
        StoppingCondition={"MaxRuntimeInSeconds": 3600},
    )

    assert (
        response["JobDefinitionArn"]
        == f"arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:data-quality-job-definition/{job_name}"
    )


@mock_aws
def test_describe_data_quality_job_definition():
    client = boto3.client("sagemaker", region_name="us-east-1")

    # Create a data quality job definition first
    job_name = "test-data-quality-job"
    client.create_data_quality_job_definition(
        JobDefinitionName=job_name,
        DataQualityAppSpecification={
            "ImageUri": f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/my-image:latest",
            "ContainerEntrypoint": ["python", "script.py"],
            "ContainerArguments": ["--arg1", "value1"],
        },
        DataQualityBaselineConfig={
            "ConstraintsResource": {"S3Uri": "s3://my-bucket/constraints.json"},
            "StatisticsResource": {"S3Uri": "s3://my-bucket/statistics.json"},
        },
        DataQualityJobInput={
            "EndpointInput": {
                "EndpointName": "my-endpoint",
                "LocalPath": "/opt/ml/processing/input",
                "S3InputMode": "File",
                "S3DataDistributionType": "FullyReplicated",
                "FeaturesAttribute": "my-features",
                "InferenceAttribute": "my-inference",
                "ProbabilityAttribute": "my-probability",
            }
        },
        DataQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://my-bucket/output",
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    }
                }
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m5.xlarge",
                "VolumeSizeInGB": 20,
            }
        },
        NetworkConfig={
            "EnableInterContainerTrafficEncryption": False,
            "EnableNetworkIsolation": False,
            "VpcConfig": {
                "SecurityGroupIds": ["sg-12345678"],
                "Subnets": ["subnet-12345678"],
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/SageMakerRole",
        StoppingCondition={"MaxRuntimeInSeconds": 3600},
    )

    # Now describe the created data quality job definition
    response = client.describe_data_quality_job_definition(JobDefinitionName=job_name)

    assert (
        response["JobDefinitionArn"]
        == f"arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:data-quality-job-definition/{job_name}"
    )
    assert response["JobDefinitionName"] == job_name
    assert "DataQualityAppSpecification" in response
    assert "DataQualityBaselineConfig" in response
    assert "DataQualityJobInput" in response
    assert "DataQualityJobOutputConfig" in response
    assert "JobResources" in response
    assert "NetworkConfig" in response
    assert "RoleArn" in response
    assert "StoppingCondition" in response


@mock_aws
def test_list_data_quality_job_definitions():
    client = boto3.client("sagemaker", region_name="us-east-1")

    job_name_1 = "test-data-quality-job-1"
    job_name_2 = "test-data-quality-job-2"

    client.create_data_quality_job_definition(
        JobDefinitionName=job_name_1,
        DataQualityAppSpecification={
            "ImageUri": f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/my-image:latest",
            "ContainerEntrypoint": ["python", "script.py"],
            "ContainerArguments": ["--arg1", "value1"],
        },
        DataQualityBaselineConfig={
            "ConstraintsResource": {"S3Uri": "s3://my-bucket/constraints.json"},
            "StatisticsResource": {"S3Uri": "s3://my-bucket/statistics.json"},
        },
        DataQualityJobInput={
            "EndpointInput": {
                "EndpointName": "my-endpoint",
                "LocalPath": "/opt/ml/processing/input",
                "S3InputMode": "File",
                "S3DataDistributionType": "FullyReplicated",
                "FeaturesAttribute": "my-features",
                "InferenceAttribute": "my-inference",
                "ProbabilityAttribute": "my-probability",
            }
        },
        DataQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://my-bucket/output",
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    }
                }
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m5.xlarge",
                "VolumeSizeInGB": 20,
            }
        },
        NetworkConfig={
            "EnableInterContainerTrafficEncryption": False,
            "EnableNetworkIsolation": False,
            "VpcConfig": {
                "SecurityGroupIds": ["sg-12345678"],
                "Subnets": ["subnet-12345678"],
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/SageMakerRole",
        StoppingCondition={"MaxRuntimeInSeconds": 3600},
    )

    client.create_data_quality_job_definition(
        JobDefinitionName=job_name_2,
        DataQualityAppSpecification={
            "ImageUri": f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/my-image:latest",
            "ContainerEntrypoint": ["python", "script.py"],
            "ContainerArguments": ["--arg1", "value1"],
        },
        DataQualityBaselineConfig={
            "ConstraintsResource": {"S3Uri": "s3://my-bucket/constraints.json"},
            "StatisticsResource": {"S3Uri": "s3://my-bucket/statistics.json"},
        },
        DataQualityJobInput={
            "EndpointInput": {
                "EndpointName": "my-endpoint",
                "LocalPath": "/opt/ml/processing/input",
                "S3InputMode": "File",
                "S3DataDistributionType": "FullyReplicated",
                "FeaturesAttribute": "my-features",
                "InferenceAttribute": "my-inference",
                "ProbabilityAttribute": "my-probability",
            }
        },
        DataQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://my-bucket/output",
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    }
                }
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m5.xlarge",
                "VolumeSizeInGB": 20,
            }
        },
        NetworkConfig={
            "EnableInterContainerTrafficEncryption": False,
            "EnableNetworkIsolation": False,
            "VpcConfig": {
                "SecurityGroupIds": ["sg-12345678"],
                "Subnets": ["subnet-12345678"],
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/SageMakerRole",
        StoppingCondition={"MaxRuntimeInSeconds": 3600},
    )

    response = client.list_data_quality_job_definitions()

    job_names = [
        job["MonitoringJobDefinitionName"] for job in response["JobDefinitionSummaries"]
    ]
    assert job_name_1 in job_names
    assert job_name_2 in job_names
    assert len(job_names) == 2


@mock_aws
def test_delete_data_quality_job_definition():
    client = boto3.client("sagemaker", region_name="us-east-1")

    job_name = "test-data-quality-job"
    client.create_data_quality_job_definition(
        JobDefinitionName=job_name,
        DataQualityAppSpecification={
            "ImageUri": f"{ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/my-image:latest",
            "ContainerEntrypoint": ["python", "script.py"],
            "ContainerArguments": ["--arg1", "value1"],
        },
        DataQualityBaselineConfig={
            "ConstraintsResource": {"S3Uri": "s3://my-bucket/constraints.json"},
            "StatisticsResource": {"S3Uri": "s3://my-bucket/statistics.json"},
        },
        DataQualityJobInput={
            "EndpointInput": {
                "EndpointName": "my-endpoint",
                "LocalPath": "/opt/ml/processing/input",
                "S3InputMode": "File",
                "S3DataDistributionType": "FullyReplicated",
                "FeaturesAttribute": "my-features",
                "InferenceAttribute": "my-inference",
                "ProbabilityAttribute": "my-probability",
            }
        },
        DataQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://my-bucket/output",
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    }
                }
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m5.xlarge",
                "VolumeSizeInGB": 20,
            }
        },
        NetworkConfig={
            "EnableInterContainerTrafficEncryption": False,
            "EnableNetworkIsolation": False,
            "VpcConfig": {
                "SecurityGroupIds": ["sg-12345678"],
                "Subnets": ["subnet-12345678"],
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/SageMakerRole",
        StoppingCondition={"MaxRuntimeInSeconds": 3600},
    )

    client.delete_data_quality_job_definition(JobDefinitionName=job_name)

    response = client.list_data_quality_job_definitions()
    job_names = [job["JobDefinitionName"] for job in response["JobDefinitionSummaries"]]
    assert job_name not in job_names
