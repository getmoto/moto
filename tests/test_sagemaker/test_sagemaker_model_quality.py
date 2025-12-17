"""Unit tests for sagemaker-supported APIs."""

import datetime

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_model_quality_job_definition():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    arn = client.create_model_quality_job_definition(
        JobDefinitionName="testmodelqualityjobdefinition",
        ModelQualityBaselineConfig={
            "BaseliningJobName": "testbaseliningjobname",
            "ConstraintsResource": {"S3Uri": "s3://constrain/resource"},
        },
        ModelQualityAppSpecification={
            "ImageUri": "testimageuri",
            "Environment": {"test": "test"},
        },
        ModelQualityJobInput={
            "EndpointInput": {
                "EndpointName": "testendpointname",
                "LocalPath": "testlocalpath",
                "S3DataDistributionType": "FullyReplicated",
                "S3InputMode": "File",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://groundtruth/test",
            },
        },
        ModelQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://output/uri",
                        "LocalPath": "testlocalpath",
                        "S3UploadMode": "Continuous",
                    }
                },
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m4.xlarge",
                "VolumeSizeInGB": 4,
            },
        },
        NetworkConfig={"EnableInterContainerTrafficEncryption": True},
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        StoppingCondition={"MaxRuntimeInSeconds": 123},
        Tags=[{"Key": "testkey", "Value": "testvalue"}],
    )
    assert (
        arn["JobDefinitionArn"]
        == f"arn:aws:sagemaker:eu-west-1:{ACCOUNT_ID}:model-quality-job-definition/testmodelqualityjobdefinition"
    )


@mock_aws
def test_describe_model_quality_job_definition():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_quality_job_definition(
        JobDefinitionName="testmodelqualityjobdefinition",
        ModelQualityBaselineConfig={
            "BaseliningJobName": "testbaseliningjobname",
            "ConstraintsResource": {"S3Uri": "s3://constrain/resource"},
        },
        ModelQualityAppSpecification={
            "ImageUri": "testimageuri",
            "Environment": {"test": "test"},
        },
        ModelQualityJobInput={
            "EndpointInput": {
                "EndpointName": "testendpointname",
                "LocalPath": "testlocalpath",
                "S3DataDistributionType": "FullyReplicated",
                "S3InputMode": "File",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://groundtruth/test",
            },
        },
        ModelQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://output/uri",
                        "LocalPath": "testlocalpath",
                        "S3UploadMode": "Continuous",
                    }
                },
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m4.xlarge",
                "VolumeSizeInGB": 4,
            },
        },
        NetworkConfig={"EnableInterContainerTrafficEncryption": True},
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        StoppingCondition={"MaxRuntimeInSeconds": 123},
        Tags=[{"Key": "testkey", "Value": "testvalue"}],
    )
    resp = client.describe_model_quality_job_definition(
        JobDefinitionName="testmodelqualityjobdefinition"
    )
    assert (
        resp["JobDefinitionArn"]
        == f"arn:aws:sagemaker:eu-west-1:{ACCOUNT_ID}:model-quality-job-definition/testmodelqualityjobdefinition"
    )
    assert resp["JobDefinitionName"] == "testmodelqualityjobdefinition"
    assert resp["ModelQualityBaselineConfig"] == {
        "BaseliningJobName": "testbaseliningjobname",
        "ConstraintsResource": {"S3Uri": "s3://constrain/resource"},
    }
    assert resp["ModelQualityAppSpecification"] == {
        "ImageUri": "testimageuri",
        "Environment": {"test": "test"},
    }
    assert resp["ModelQualityJobInput"] == {
        "EndpointInput": {
            "EndpointName": "testendpointname",
            "LocalPath": "testlocalpath",
            "S3DataDistributionType": "FullyReplicated",
            "S3InputMode": "File",
        },
        "GroundTruthS3Input": {
            "S3Uri": "s3://groundtruth/test",
        },
    }
    assert resp["ModelQualityJobOutputConfig"] == {
        "MonitoringOutputs": [
            {
                "S3Output": {
                    "S3Uri": "s3://output/uri",
                    "LocalPath": "testlocalpath",
                    "S3UploadMode": "Continuous",
                }
            },
        ]
    }
    assert resp["JobResources"] == {
        "ClusterConfig": {
            "InstanceCount": 1,
            "InstanceType": "ml.m4.xlarge",
            "VolumeSizeInGB": 4,
        },
    }
    assert resp["NetworkConfig"] == {"EnableInterContainerTrafficEncryption": True}
    assert resp["RoleArn"] == f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole"


@mock_aws
def test_describe_model_quality_job_definition_defaults():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_quality_job_definition(
        JobDefinitionName="testmodelqualityjobdefinition",
        ModelQualityAppSpecification={
            "ImageUri": "testimageuri",
        },
        ModelQualityJobInput={
            "EndpointInput": {
                "EndpointName": "testendpointname",
                "LocalPath": "testlocalpath",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://groundtruth/test",
            },
        },
        ModelQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://output/uri",
                        "LocalPath": "testlocalpath",
                    }
                },
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m4.xlarge",
                "VolumeSizeInGB": 4,
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
    )
    resp = client.describe_model_quality_job_definition(
        JobDefinitionName="testmodelqualityjobdefinition"
    )
    assert (
        resp["JobDefinitionArn"]
        == f"arn:aws:sagemaker:eu-west-1:{ACCOUNT_ID}:model-quality-job-definition/testmodelqualityjobdefinition"
    )
    assert resp["JobDefinitionName"] == "testmodelqualityjobdefinition"
    assert resp["ModelQualityAppSpecification"] == {
        "ImageUri": "testimageuri",
    }
    assert resp["ModelQualityJobInput"] == {
        "EndpointInput": {
            "EndpointName": "testendpointname",
            "LocalPath": "testlocalpath",
        },
        "GroundTruthS3Input": {
            "S3Uri": "s3://groundtruth/test",
        },
    }
    assert resp["ModelQualityJobOutputConfig"] == {
        "MonitoringOutputs": [
            {
                "S3Output": {
                    "S3Uri": "s3://output/uri",
                    "LocalPath": "testlocalpath",
                }
            },
        ]
    }
    assert resp["JobResources"] == {
        "ClusterConfig": {
            "InstanceCount": 1,
            "InstanceType": "ml.m4.xlarge",
            "VolumeSizeInGB": 4,
        },
    }
    assert resp["RoleArn"] == f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole"


@mock_aws
def test_list_model_quality_job_definitions():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_quality_job_definition(
        JobDefinitionName="testmodelqualityjobdefinition",
        ModelQualityAppSpecification={
            "ImageUri": "testimageuri",
        },
        ModelQualityJobInput={
            "EndpointInput": {
                "EndpointName": "testendpointname",
                "LocalPath": "testlocalpath",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://groundtruth/test",
            },
        },
        ModelQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://output/uri",
                        "LocalPath": "testlocalpath",
                    }
                },
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m4.xlarge",
                "VolumeSizeInGB": 4,
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
    )
    client.create_model_quality_job_definition(
        JobDefinitionName="testmodelqualityjobdefinition2",
        ModelQualityAppSpecification={
            "ImageUri": "testimageuri",
        },
        ModelQualityJobInput={
            "EndpointInput": {
                "EndpointName": "testendpointname2",
                "LocalPath": "testlocalpath",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://groundtruth/test",
            },
        },
        ModelQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://output/uri",
                        "LocalPath": "testlocalpath",
                    }
                },
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m4.xlarge",
                "VolumeSizeInGB": 4,
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
    )
    resp = client.list_model_quality_job_definitions()["JobDefinitionSummaries"]
    assert resp[0]["MonitoringJobDefinitionName"] == "testmodelqualityjobdefinition"
    assert (
        resp[0]["MonitoringJobDefinitionArn"]
        == f"arn:aws:sagemaker:eu-west-1:{ACCOUNT_ID}:model-quality-job-definition/testmodelqualityjobdefinition"
    )
    assert isinstance(resp[0]["CreationTime"], datetime.datetime)
    assert resp[0]["EndpointName"] == "testendpointname"
    assert resp[1]["MonitoringJobDefinitionName"] == "testmodelqualityjobdefinition2"
    assert (
        resp[1]["MonitoringJobDefinitionArn"]
        == f"arn:aws:sagemaker:eu-west-1:{ACCOUNT_ID}:model-quality-job-definition/testmodelqualityjobdefinition2"
    )
    assert isinstance(resp[1]["CreationTime"], datetime.datetime)
    assert resp[1]["EndpointName"] == "testendpointname2"


@mock_aws
def test_list_model_quality_job_definitions_filters():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_quality_job_definition(
        JobDefinitionName="testmodelqualityjobdefinition",
        ModelQualityAppSpecification={
            "ImageUri": "testimageuri",
        },
        ModelQualityJobInput={
            "EndpointInput": {
                "EndpointName": "testendpointname",
                "LocalPath": "testlocalpath",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://groundtruth/test",
            },
        },
        ModelQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://output/uri",
                        "LocalPath": "testlocalpath",
                    }
                },
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m4.xlarge",
                "VolumeSizeInGB": 4,
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
    )
    client.create_model_quality_job_definition(
        JobDefinitionName="test2modelqualityjobdefinition2",
        ModelQualityAppSpecification={
            "ImageUri": "testimageuri",
        },
        ModelQualityJobInput={
            "EndpointInput": {
                "EndpointName": "testendpointname",
                "LocalPath": "testlocalpath",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://groundtruth/test",
            },
        },
        ModelQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://output/uri",
                        "LocalPath": "testlocalpath",
                    }
                },
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m4.xlarge",
                "VolumeSizeInGB": 4,
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
    )
    client.create_model_quality_job_definition(
        JobDefinitionName="testmodelqualityjobdefinition3",
        ModelQualityAppSpecification={
            "ImageUri": "testimageuri",
        },
        ModelQualityJobInput={
            "EndpointInput": {
                "EndpointName": "test3endpointname3",
                "LocalPath": "testlocalpath",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://groundtruth/test",
            },
        },
        ModelQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://output/uri",
                        "LocalPath": "testlocalpath",
                    }
                },
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m4.xlarge",
                "VolumeSizeInGB": 4,
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
    )
    resp = client.list_model_quality_job_definitions(
        EndpointName="testendpointname",
        SortBy="Name",
        SortOrder="Ascending",
        NameContains="testmodelqualityjobdefinition",
        CreationTimeBefore=str(datetime.datetime(2099, 1, 1)),
        CreationTimeAfter=str(datetime.datetime(2021, 1, 1)),
    )["JobDefinitionSummaries"]
    assert len(resp) == 1
    assert resp[0]["MonitoringJobDefinitionName"] == "testmodelqualityjobdefinition"
    assert (
        resp[0]["MonitoringJobDefinitionArn"]
        == f"arn:aws:sagemaker:eu-west-1:{ACCOUNT_ID}:model-quality-job-definition/testmodelqualityjobdefinition"
    )
    assert isinstance(resp[0]["CreationTime"], datetime.datetime)
    assert resp[0]["EndpointName"] == "testendpointname"


@mock_aws
def test_delete_model_quality_job_definition():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_quality_job_definition(
        JobDefinitionName="testmodelqualityjobdefinition",
        ModelQualityAppSpecification={
            "ImageUri": "testimageuri",
        },
        ModelQualityJobInput={
            "EndpointInput": {
                "EndpointName": "testendpointname",
                "LocalPath": "testlocalpath",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://groundtruth/test",
            },
        },
        ModelQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://output/uri",
                        "LocalPath": "testlocalpath",
                    }
                },
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m4.xlarge",
                "VolumeSizeInGB": 4,
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
    )
    client.create_model_quality_job_definition(
        JobDefinitionName="test2modelqualityjobdefinition2",
        ModelQualityAppSpecification={
            "ImageUri": "testimageuri",
        },
        ModelQualityJobInput={
            "EndpointInput": {
                "EndpointName": "testendpointname",
                "LocalPath": "testlocalpath",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://groundtruth/test",
            },
        },
        ModelQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://output/uri",
                        "LocalPath": "testlocalpath",
                    }
                },
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m4.xlarge",
                "VolumeSizeInGB": 4,
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
    )
    client.delete_model_quality_job_definition(
        JobDefinitionName="testmodelqualityjobdefinition"
    )
    resp = client.list_model_quality_job_definitions()
    assert len(resp["JobDefinitionSummaries"]) == 1
    assert (
        resp["JobDefinitionSummaries"][0]["MonitoringJobDefinitionName"]
        == "test2modelqualityjobdefinition2"
    )


@mock_aws
def test_tag_model_quality_job_definition():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_quality_job_definition(
        JobDefinitionName="testmodelqualityjobdefinition",
        ModelQualityAppSpecification={
            "ImageUri": "testimageuri",
        },
        ModelQualityJobInput={
            "EndpointInput": {
                "EndpointName": "testendpointname",
                "LocalPath": "testlocalpath",
            },
            "GroundTruthS3Input": {
                "S3Uri": "s3://groundtruth/test",
            },
        },
        ModelQualityJobOutputConfig={
            "MonitoringOutputs": [
                {
                    "S3Output": {
                        "S3Uri": "s3://output/uri",
                        "LocalPath": "testlocalpath",
                    }
                },
            ]
        },
        JobResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m4.xlarge",
                "VolumeSizeInGB": 4,
            },
        },
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        Tags=[{"Key": "testkey", "Value": "testvalue"}],
    )
    resp1 = client.list_tags(
        ResourceArn=f"arn:aws:sagemaker:eu-west-1:{ACCOUNT_ID}:model-quality-job-definition/testmodelqualityjobdefinition"
    )
    assert resp1["Tags"] == [{"Key": "testkey", "Value": "testvalue"}]
    client.add_tags(
        ResourceArn=f"arn:aws:sagemaker:eu-west-1:{ACCOUNT_ID}:model-quality-job-definition/testmodelqualityjobdefinition",
        Tags=[{"Key": "testkey2", "Value": "testvalue2"}],
    )
    resp2 = client.list_tags(
        ResourceArn=f"arn:aws:sagemaker:eu-west-1:{ACCOUNT_ID}:model-quality-job-definition/testmodelqualityjobdefinition"
    )
    assert resp2["Tags"] == [
        {"Key": "testkey", "Value": "testvalue"},
        {"Key": "testkey2", "Value": "testvalue2"},
    ]
    client.delete_tags(
        ResourceArn=f"arn:aws:sagemaker:eu-west-1:{ACCOUNT_ID}:model-quality-job-definition/testmodelqualityjobdefinition",
        TagKeys=["testkey"],
    )
    resp3 = client.list_tags(
        ResourceArn=f"arn:aws:sagemaker:eu-west-1:{ACCOUNT_ID}:model-quality-job-definition/testmodelqualityjobdefinition"
    )
    assert resp3["Tags"] == [{"Key": "testkey2", "Value": "testvalue2"}]
