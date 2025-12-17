"""Unit tests for sagemaker-supported APIs."""

import datetime

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_compilation_job():
    client = boto3.client("sagemaker", region_name="ap-southeast-1")
    resp = client.create_compilation_job(
        CompilationJobName="testcompilationjob",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        InputConfig={
            "S3Uri": "s3://MyBucket/model.tar.gz",
            "DataInputConfig": "{'input0':[1,3,224,224]}",
            "Framework": "PYTORCH",
            "FrameworkVersion": "2.0",
        },
        OutputConfig={
            "S3OutputLocation": "s3://MyBucket/output",
            "TargetDevice": "lambda",
            "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        },
        VpcConfig={
            "SecurityGroupIds": [
                "sg-12345678901234567",
            ],
            "Subnets": [
                "subnet-12345678901234567",
            ],
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
        Tags=[
            {"Key": "testkey", "Value": "testvalue"},
        ],
    )
    assert (
        resp["CompilationJobArn"]
        == "arn:aws:sagemaker:ap-southeast-1:123456789012:compilation-job/testcompilationjob"
    )


@mock_aws
def test_create_compilation_job_defaults():
    client = boto3.client("sagemaker", region_name="ap-southeast-1")
    resp = client.create_compilation_job(
        CompilationJobName="testcompilationjob",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        ModelPackageVersionArn=f"arn:aws:sagemaker:ap-southeast-1:{ACCOUNT_ID}:model-package/FakeModelPackage",
        OutputConfig={
            "S3OutputLocation": "s3://MyBucket/output",
            "TargetDevice": "lambda",
            "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
    )
    assert (
        resp["CompilationJobArn"]
        == "arn:aws:sagemaker:ap-southeast-1:123456789012:compilation-job/testcompilationjob"
    )


@mock_aws
def test_describe_compilation_job():
    client = boto3.client("sagemaker", region_name="ap-southeast-1")
    resp = client.create_compilation_job(
        CompilationJobName="testcompilationjob",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        InputConfig={
            "S3Uri": "s3://MyBucket/model.tar.gz",
            "DataInputConfig": "{'input0':[1,3,224,224]}",
            "Framework": "PYTORCH",
            "FrameworkVersion": "2.0",
        },
        OutputConfig={
            "S3OutputLocation": "s3://MyBucket/output",
            "TargetPlatform": {
                "Os": "LINUX",
                "Arch": "X86_64",
                "Accelerator": "NVIDIA",
            },
            "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        },
        VpcConfig={
            "SecurityGroupIds": [
                "sg-12345678901234567",
            ],
            "Subnets": [
                "subnet-12345678901234567",
            ],
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
        Tags=[
            {"Key": "testkey", "Value": "testvalue"},
        ],
    )
    resp = client.describe_compilation_job(CompilationJobName="testcompilationjob")
    assert resp["CompilationJobName"] == "testcompilationjob"
    assert (
        resp["CompilationJobArn"]
        == "arn:aws:sagemaker:ap-southeast-1:123456789012:compilation-job/testcompilationjob"
    )
    assert resp["CompilationJobStatus"] == "COMPLETED"
    assert isinstance(resp["CompilationStartTime"], datetime.datetime)
    assert isinstance(resp["CompilationEndTime"], datetime.datetime)
    assert resp["StoppingCondition"] == {
        "MaxRuntimeInSeconds": 123,
        "MaxWaitTimeInSeconds": 123,
        "MaxPendingTimeInSeconds": 7200,
    }
    assert resp["InferenceImage"] == "InferenceImage"
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)
    assert resp["FailureReason"] == ""
    assert resp["ModelArtifacts"] == {"S3ModelArtifacts": "s3://MyBucket/output"}
    assert resp["ModelDigests"] == {
        "ArtifactDigest": "786a02f742015903c6c6fd852552d272912f4740e15847618a86e217f71f5419d25e1031afee585313896444934eb04b903a685b1448b755d56f701afe9be2ce"
    }
    assert resp["RoleArn"] == f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole"
    assert resp["InputConfig"] == {
        "S3Uri": "s3://MyBucket/model.tar.gz",
        "DataInputConfig": "{'input0':[1,3,224,224]}",
        "Framework": "PYTORCH",
        "FrameworkVersion": "2.0",
    }
    assert resp["OutputConfig"] == {
        "S3OutputLocation": "s3://MyBucket/output",
        "TargetPlatform": {"Os": "LINUX", "Arch": "X86_64", "Accelerator": "NVIDIA"},
        "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
    }
    assert resp["VpcConfig"] == {
        "SecurityGroupIds": [
            "sg-12345678901234567",
        ],
        "Subnets": [
            "subnet-12345678901234567",
        ],
    }
    assert resp["DerivedInformation"] == {
        "DerivedDataInputConfig": "DerivedDataInputConfig"
    }


@mock_aws
def test_describe_compilation_job_defaults():
    client = boto3.client("sagemaker", region_name="ap-southeast-1")
    resp = client.create_compilation_job(
        CompilationJobName="testcompilationjob",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        ModelPackageVersionArn=f"arn:aws:sagemaker:ap-southeast-1:{ACCOUNT_ID}:model-package/FakeModelPackage",
        OutputConfig={
            "S3OutputLocation": "s3://MyBucket/output",
            "TargetDevice": "lambda",
            "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
    )
    assert (
        resp["CompilationJobArn"]
        == "arn:aws:sagemaker:ap-southeast-1:123456789012:compilation-job/testcompilationjob"
    )

    resp = client.describe_compilation_job(CompilationJobName="testcompilationjob")
    assert resp["CompilationJobName"] == "testcompilationjob"
    assert (
        resp["CompilationJobArn"]
        == "arn:aws:sagemaker:ap-southeast-1:123456789012:compilation-job/testcompilationjob"
    )
    assert resp["CompilationJobStatus"] == "COMPLETED"
    assert isinstance(resp["CompilationStartTime"], datetime.datetime)
    assert isinstance(resp["CompilationEndTime"], datetime.datetime)
    assert resp["StoppingCondition"] == {
        "MaxRuntimeInSeconds": 123,
        "MaxWaitTimeInSeconds": 123,
        "MaxPendingTimeInSeconds": 7200,
    }
    assert resp["InferenceImage"] == "InferenceImage"
    assert (
        resp["ModelPackageVersionArn"]
        == f"arn:aws:sagemaker:ap-southeast-1:{ACCOUNT_ID}:model-package/FakeModelPackage"
    )
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)
    assert resp["FailureReason"] == ""
    assert resp["ModelArtifacts"] == {"S3ModelArtifacts": "s3://MyBucket/output"}
    assert resp["ModelDigests"] == {
        "ArtifactDigest": "786a02f742015903c6c6fd852552d272912f4740e15847618a86e217f71f5419d25e1031afee585313896444934eb04b903a685b1448b755d56f701afe9be2ce"
    }
    assert resp["RoleArn"] == f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole"
    assert resp["OutputConfig"] == {
        "S3OutputLocation": "s3://MyBucket/output",
        "TargetDevice": "lambda",
        "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
    }
    assert resp["DerivedInformation"] == {
        "DerivedDataInputConfig": "DerivedDataInputConfig"
    }


@mock_aws
def test_list_compilation_jobs():
    client = boto3.client("sagemaker", region_name="us-east-2")
    client.create_compilation_job(
        CompilationJobName="testcompilationjob",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        ModelPackageVersionArn=f"arn:aws:sagemaker:ap-southeast-1:{ACCOUNT_ID}:model-package/FakeModelPackage",
        OutputConfig={
            "S3OutputLocation": "s3://MyBucket/output",
            "TargetDevice": "lambda",
            "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
    )
    client.create_compilation_job(
        CompilationJobName="testcompilationjob2",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        InputConfig={
            "S3Uri": "s3://MyBucket/model.tar.gz",
            "DataInputConfig": "{'input0':[1,3,224,224]}",
            "Framework": "PYTORCH",
            "FrameworkVersion": "2.0",
        },
        OutputConfig={
            "S3OutputLocation": "s3://MyBucket/output",
            "TargetPlatform": {
                "Os": "LINUX",
                "Arch": "X86_64",
                "Accelerator": "NVIDIA",
            },
            "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
    )
    resp = client.list_compilation_jobs()
    assert len(resp["CompilationJobSummaries"]) == 2
    assert (
        resp["CompilationJobSummaries"][0]["CompilationJobName"] == "testcompilationjob"
    )
    assert (
        resp["CompilationJobSummaries"][0]["CompilationJobArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:compilation-job/testcompilationjob"
    )
    assert isinstance(
        resp["CompilationJobSummaries"][0]["CreationTime"], datetime.datetime
    )
    assert isinstance(
        resp["CompilationJobSummaries"][0]["CompilationStartTime"], datetime.datetime
    )
    assert isinstance(
        resp["CompilationJobSummaries"][0]["CompilationEndTime"], datetime.datetime
    )
    assert resp["CompilationJobSummaries"][0]["CompilationTargetDevice"] == "lambda"
    assert isinstance(
        resp["CompilationJobSummaries"][0]["LastModifiedTime"], datetime.datetime
    )
    assert resp["CompilationJobSummaries"][0]["CompilationJobStatus"] == "COMPLETED"
    assert (
        resp["CompilationJobSummaries"][1]["CompilationJobName"]
        == "testcompilationjob2"
    )
    assert (
        resp["CompilationJobSummaries"][1]["CompilationJobArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:compilation-job/testcompilationjob2"
    )
    assert isinstance(
        resp["CompilationJobSummaries"][1]["CreationTime"], datetime.datetime
    )
    assert isinstance(
        resp["CompilationJobSummaries"][1]["CompilationStartTime"], datetime.datetime
    )
    assert isinstance(
        resp["CompilationJobSummaries"][1]["CompilationEndTime"], datetime.datetime
    )
    assert resp["CompilationJobSummaries"][1]["CompilationTargetPlatformOs"] == "LINUX"
    assert (
        resp["CompilationJobSummaries"][1]["CompilationTargetPlatformArch"] == "X86_64"
    )
    assert (
        resp["CompilationJobSummaries"][1]["CompilationTargetPlatformAccelerator"]
        == "NVIDIA"
    )
    assert isinstance(
        resp["CompilationJobSummaries"][1]["LastModifiedTime"], datetime.datetime
    )
    assert resp["CompilationJobSummaries"][1]["CompilationJobStatus"] == "COMPLETED"


@mock_aws
def test_list_compilation_jobs_filters():
    client = boto3.client("sagemaker", region_name="us-east-2")
    client.create_compilation_job(
        CompilationJobName="testcompilationjob",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        ModelPackageVersionArn=f"arn:aws:sagemaker:ap-southeast-1:{ACCOUNT_ID}:model-package/FakeModelPackage",
        OutputConfig={
            "S3OutputLocation": "s3://MyBucket/output",
            "TargetDevice": "lambda",
            "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
    )
    client.create_compilation_job(
        CompilationJobName="testmycompilationjob",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        ModelPackageVersionArn=f"arn:aws:sagemaker:ap-southeast-1:{ACCOUNT_ID}:model-package/FakeModelPackage",
        OutputConfig={
            "S3OutputLocation": "s3://MyBucket/output",
            "TargetDevice": "lambda",
            "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
    )
    client.create_compilation_job(
        CompilationJobName="testcompilationjob2",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        InputConfig={
            "S3Uri": "s3://MyBucket/model.tar.gz",
            "DataInputConfig": "{'input0':[1,3,224,224]}",
            "Framework": "PYTORCH",
            "FrameworkVersion": "2.0",
        },
        OutputConfig={
            "S3OutputLocation": "s3://MyBucket/output",
            "TargetPlatform": {
                "Os": "LINUX",
                "Arch": "X86_64",
                "Accelerator": "NVIDIA",
            },
            "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
    )
    resp = client.list_compilation_jobs(
        CreationTimeAfter=datetime.datetime(2015, 1, 1),
        CreationTimeBefore=datetime.datetime(2099, 1, 1),
        LastModifiedTimeAfter=datetime.datetime(2015, 1, 1),
        LastModifiedTimeBefore=datetime.datetime(2099, 1, 1),
        NameContains="testcompilationjob",
        StatusEquals="COMPLETED",
        SortBy="Name",
        SortOrder="Ascending",
    )
    assert len(resp["CompilationJobSummaries"]) == 2
    assert (
        resp["CompilationJobSummaries"][0]["CompilationJobName"] == "testcompilationjob"
    )
    assert (
        resp["CompilationJobSummaries"][0]["CompilationJobArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:compilation-job/testcompilationjob"
    )
    assert isinstance(
        resp["CompilationJobSummaries"][0]["CreationTime"], datetime.datetime
    )
    assert isinstance(
        resp["CompilationJobSummaries"][0]["CompilationStartTime"], datetime.datetime
    )
    assert isinstance(
        resp["CompilationJobSummaries"][0]["CompilationEndTime"], datetime.datetime
    )
    assert resp["CompilationJobSummaries"][0]["CompilationTargetDevice"] == "lambda"
    assert isinstance(
        resp["CompilationJobSummaries"][0]["LastModifiedTime"], datetime.datetime
    )
    assert resp["CompilationJobSummaries"][0]["CompilationJobStatus"] == "COMPLETED"
    assert (
        resp["CompilationJobSummaries"][1]["CompilationJobName"]
        == "testcompilationjob2"
    )
    assert (
        resp["CompilationJobSummaries"][1]["CompilationJobArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:compilation-job/testcompilationjob2"
    )
    assert isinstance(
        resp["CompilationJobSummaries"][1]["CreationTime"], datetime.datetime
    )
    assert isinstance(
        resp["CompilationJobSummaries"][1]["CompilationStartTime"], datetime.datetime
    )
    assert isinstance(
        resp["CompilationJobSummaries"][1]["CompilationEndTime"], datetime.datetime
    )
    assert resp["CompilationJobSummaries"][1]["CompilationTargetPlatformOs"] == "LINUX"
    assert (
        resp["CompilationJobSummaries"][1]["CompilationTargetPlatformArch"] == "X86_64"
    )
    assert (
        resp["CompilationJobSummaries"][1]["CompilationTargetPlatformAccelerator"]
        == "NVIDIA"
    )
    assert isinstance(
        resp["CompilationJobSummaries"][1]["LastModifiedTime"], datetime.datetime
    )
    assert resp["CompilationJobSummaries"][1]["CompilationJobStatus"] == "COMPLETED"


@mock_aws
def test_delete_compilation_job():
    client = boto3.client("sagemaker", region_name="ap-southeast-1")
    client.create_compilation_job(
        CompilationJobName="testcompilationjob",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        ModelPackageVersionArn=f"arn:aws:sagemaker:ap-southeast-1:{ACCOUNT_ID}:model-package/FakeModelPackage",
        OutputConfig={
            "S3OutputLocation": "s3://MyBucket/output",
            "TargetDevice": "lambda",
            "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
    )
    client.create_compilation_job(
        CompilationJobName="testcompilationjob2",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        ModelPackageVersionArn=f"arn:aws:sagemaker:ap-southeast-1:{ACCOUNT_ID}:model-package/FakeModelPackage",
        OutputConfig={
            "S3OutputLocation": "s3://MyBucket/output",
            "TargetDevice": "lambda",
            "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
    )
    client.delete_compilation_job(CompilationJobName="testcompilationjob")
    resp = client.list_compilation_jobs()
    assert len(resp["CompilationJobSummaries"]) == 1
    assert (
        resp["CompilationJobSummaries"][0]["CompilationJobName"]
        == "testcompilationjob2"
    )


@mock_aws
def test_tag_compilation_job():
    client = boto3.client("sagemaker", region_name="us-east-1")
    client.create_compilation_job(
        CompilationJobName="testcompilationjob",
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        ModelPackageVersionArn=f"arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:model-package/FakeModelPackage",
        OutputConfig={
            "S3OutputLocation": "s3://MyBucket/output",
            "TargetDevice": "lambda",
            "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
        Tags=[
            {"Key": "testkey", "Value": "testvalue"},
        ],
    )
    client.add_tags(
        ResourceArn="arn:aws:sagemaker:us-east-1:123456789012:compilation-job/testcompilationjob",
        Tags=[{"Key": "testkey2", "Value": "testvalue2"}],
    )
    resp = client.list_tags(
        ResourceArn="arn:aws:sagemaker:us-east-1:123456789012:compilation-job/testcompilationjob"
    )
    assert resp["Tags"] == [
        {"Key": "testkey", "Value": "testvalue"},
        {"Key": "testkey2", "Value": "testvalue2"},
    ]
