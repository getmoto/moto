import datetime
import re

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

FAKE_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole"
TEST_REGION_NAME = "us-east-1"


class MyTransformJobModel:
    def __init__(
        self,
        transform_job_name,
        model_name,
        max_concurrent_transforms=None,
        model_client_config=None,
        max_payload_in_mb=None,
        batch_strategy=None,
        environment=None,
        transform_input=None,
        transform_output=None,
        data_capture_config=None,
        transform_resources=None,
        data_processing=None,
        tags=None,
        experiment_config=None,
    ):
        self.transform_job_name = transform_job_name
        self.model_name = model_name
        self.max_concurrent_transforms = max_concurrent_transforms or 1
        self.model_client_config = model_client_config or {}
        self.max_payload_in_mb = max_payload_in_mb or 1
        self.batch_strategy = batch_strategy or "SingleRecord"
        self.environment = environment or {}
        self.transform_input = transform_input or {
            "DataSource": {
                "S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": "input"}
            },
            "ContentType": "application/json",
            "CompressionType": "None",
            "SplitType": "None",
        }
        self.transform_output = transform_output or {
            "S3OutputPath": "some-bucket",
            "Accept": "application/json",
            "AssembleWith": "None",
            "KmsKeyId": "None",
        }
        self.data_capture_config = data_capture_config or {
            "DestinationS3Uri": "data_capture",
            "KmsKeyId": "None",
            "GenerateInferenceId": False,
        }
        self.transform_resources = transform_resources or {
            "InstanceType": "ml.m5.2xlarge",
            "InstanceCount": 1,
        }
        self.data_processing = data_processing or {}
        self.tags = tags or []
        self.experiment_config = experiment_config or {}

    def save(self):
        sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

        params = {
            "TransformJobName": self.transform_job_name,
            "ModelName": self.model_name,
            "MaxConcurrentTransforms": self.max_concurrent_transforms,
            "ModelClientConfig": self.model_client_config,
            "MaxPayloadInMB": self.max_payload_in_mb,
            "BatchStrategy": self.batch_strategy,
            "Environment": self.environment,
            "TransformInput": self.transform_input,
            "TransformOutput": self.transform_output,
            "DataCaptureConfig": self.data_capture_config,
            "TransformResources": self.transform_resources,
            "DataProcessing": self.data_processing,
            "Tags": self.tags,
            "ExperimentConfig": self.experiment_config,
        }
        return sagemaker.create_transform_job(**params)


@mock_aws
def test_create_transform_job():
    sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)
    transform_job_name = "MyTransformJob"
    model_name = "MyModelName"
    bucket = "my-bucket"
    transform_input = {
        "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": "input"}},
        "ContentType": "application/json",
        "CompressionType": "None",
        "SplitType": "None",
    }
    transform_output = {
        "S3OutputPath": bucket,
        "Accept": "application/json",
        "AssembleWith": "None",
        "KmsKeyId": "None",
    }

    model_client_config = {
        "InvocationsTimeoutInSeconds": 60,
        "InvocationsMaxRetries": 1,
    }

    max_payload_in_mb = 1

    data_capture_config = {
        "DestinationS3Uri": "data_capture",
        "KmsKeyId": "None",
        "GenerateInferenceId": False,
    }

    transform_resources = {
        "InstanceType": "ml.m5.2xlarge",
        "InstanceCount": 1,
    }

    data_processing = {
        "InputFilter": "$.features",
        "OutputFilter": "$['id','SageMakerOutput']",
        "JoinSource": "None",
    }

    experiment_config = {
        "ExperimentName": "MyExperiment",
        "TrialName": "MyTrial",
        "TrialComponentDisplayName": "MyTrialDisplay",
        "RunName": "MyRun",
    }

    job = MyTransformJobModel(
        transform_job_name=transform_job_name,
        model_name=model_name,
        transform_output=transform_output,
        model_client_config=model_client_config,
        max_payload_in_mb=max_payload_in_mb,
        data_capture_config=data_capture_config,
        transform_resources=transform_resources,
        data_processing=data_processing,
        experiment_config=experiment_config,
    )
    resp = job.save()
    assert re.match(
        rf"^arn:aws:sagemaker:.*:.*:transform-job/{transform_job_name}$",
        resp["TransformJobArn"],
    )
    resp = sagemaker.describe_transform_job(TransformJobName=transform_job_name)
    assert resp["TransformJobName"] == transform_job_name
    assert resp["TransformJobStatus"] == "Completed"
    assert resp["ModelName"] == model_name
    assert resp["MaxConcurrentTransforms"] == 1
    assert resp["ModelClientConfig"] == model_client_config
    assert resp["MaxPayloadInMB"] == max_payload_in_mb
    assert resp["BatchStrategy"] == "SingleRecord"
    assert resp["TransformInput"] == transform_input
    assert resp["TransformOutput"] == transform_output
    assert resp["DataCaptureConfig"] == data_capture_config
    assert resp["TransformResources"] == transform_resources
    assert resp["DataProcessing"] == data_processing
    assert resp["ExperimentConfig"] == experiment_config
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert isinstance(resp["TransformStartTime"], datetime.datetime)
    assert isinstance(resp["TransformEndTime"], datetime.datetime)


@mock_aws
def test_list_transform_jobs():
    client = boto3.client("sagemaker", region_name="us-east-1")
    name = "blah"
    model_name = "blah_model"
    test_transform_job = MyTransformJobModel(
        transform_job_name=name, model_name=model_name
    )
    test_transform_job.save()
    transform_jobs = client.list_transform_jobs()
    assert len(transform_jobs["TransformJobSummaries"]) == 1
    assert transform_jobs["TransformJobSummaries"][0]["TransformJobName"] == name

    assert re.match(
        rf"^arn:aws:sagemaker:.*:.*:transform-job/{name}$",
        transform_jobs["TransformJobSummaries"][0]["TransformJobArn"],
    )
    assert transform_jobs.get("NextToken") is None


@mock_aws
def test_list_transform_jobs_multiple():
    client = boto3.client("sagemaker", region_name="us-east-1")
    name_job_1 = "blah"
    model_name1 = "blah_model"
    test_transform_job_1 = MyTransformJobModel(
        transform_job_name=name_job_1, model_name=model_name1
    )
    test_transform_job_1.save()

    name_job_2 = "blah2"
    model_name2 = "blah_model2"
    test_transform_job_2 = MyTransformJobModel(
        transform_job_name=name_job_2, model_name=model_name2
    )
    test_transform_job_2.save()
    transform_jobs_limit = client.list_transform_jobs(MaxResults=1)
    assert len(transform_jobs_limit["TransformJobSummaries"]) == 1

    transform_jobs = client.list_transform_jobs()
    assert len(transform_jobs["TransformJobSummaries"]) == 2
    assert transform_jobs.get("NextToken") is None


@mock_aws
def test_list_transform_jobs_none():
    client = boto3.client("sagemaker", region_name="us-east-1")
    transform_jobs = client.list_transform_jobs()
    assert len(transform_jobs["TransformJobSummaries"]) == 0


@mock_aws
def test_list_transform_jobs_should_validate_input():
    client = boto3.client("sagemaker", region_name="us-east-1")
    junk_status_equals = "blah"
    with pytest.raises(ClientError) as ex:
        client.list_transform_jobs(StatusEquals=junk_status_equals)
    expected_error = (
        f"1 validation errors detected: Value '{junk_status_equals}' at "
        "'statusEquals' failed to satisfy constraint: Member must satisfy "
        "enum value set: ['Completed', 'Stopped', 'InProgress', 'Stopping', "
        "'Failed']"
    )
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["Error"]["Message"] == expected_error

    junk_next_token = "asdf"
    with pytest.raises(ClientError) as ex:
        client.list_transform_jobs(NextToken=junk_next_token)
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert (
        ex.value.response["Error"]["Message"]
        == 'Invalid pagination token because "{0}".'
    )


@mock_aws
def test_list_transform_jobs_with_name_filters():
    client = boto3.client("sagemaker", region_name="us-east-1")
    for i in range(5):
        name = f"xgboost-{i}"
        model_name = f"blah_model-{i}"
        MyTransformJobModel(transform_job_name=name, model_name=model_name).save()
    for i in range(5):
        name = f"vgg-{i}"
        model_name = f"blah_model-{i}"
        MyTransformJobModel(transform_job_name=name, model_name=model_name).save()
    xgboost_transform_jobs = client.list_transform_jobs(NameContains="xgboost")
    assert len(xgboost_transform_jobs["TransformJobSummaries"]) == 5

    transform_jobs_with_2 = client.list_transform_jobs(NameContains="2")
    assert len(transform_jobs_with_2["TransformJobSummaries"]) == 2


@mock_aws
def test_list_transform_jobs_paginated():
    client = boto3.client("sagemaker", region_name="us-east-1")
    for i in range(5):
        name = f"xgboost-{i}"
        model_name = f"my-model-{i}"
        MyTransformJobModel(transform_job_name=name, model_name=model_name).save()
    xgboost_transform_job_1 = client.list_transform_jobs(
        NameContains="xgboost", MaxResults=1
    )
    assert len(xgboost_transform_job_1["TransformJobSummaries"]) == 1
    assert (
        xgboost_transform_job_1["TransformJobSummaries"][0]["TransformJobName"]
        == "xgboost-0"
    )
    assert xgboost_transform_job_1.get("NextToken") is not None

    xgboost_transform_job_next = client.list_transform_jobs(
        NameContains="xgboost",
        MaxResults=1,
        NextToken=xgboost_transform_job_1.get("NextToken"),
    )
    assert len(xgboost_transform_job_next["TransformJobSummaries"]) == 1
    assert (
        xgboost_transform_job_next["TransformJobSummaries"][0]["TransformJobName"]
        == "xgboost-1"
    )
    assert xgboost_transform_job_next.get("NextToken") is not None


@mock_aws
def test_list_transform_jobs_paginated_with_target_in_middle():
    client = boto3.client("sagemaker", region_name="us-east-1")
    for i in range(5):
        name = f"xgboost-{i}"
        model_name = f"my-model-{i}"
        MyTransformJobModel(transform_job_name=name, model_name=model_name).save()
    for i in range(5):
        name = f"vgg-{i}"
        MyTransformJobModel(transform_job_name=name, model_name=model_name).save()

    vgg_transform_job_1 = client.list_transform_jobs(NameContains="vgg", MaxResults=1)
    assert len(vgg_transform_job_1["TransformJobSummaries"]) == 0
    assert vgg_transform_job_1.get("NextToken") is not None

    vgg_transform_job_6 = client.list_transform_jobs(NameContains="vgg", MaxResults=6)

    assert len(vgg_transform_job_6["TransformJobSummaries"]) == 1
    assert (
        vgg_transform_job_6["TransformJobSummaries"][0]["TransformJobName"] == "vgg-0"
    )
    assert vgg_transform_job_6.get("NextToken") is not None

    vgg_transform_job_10 = client.list_transform_jobs(NameContains="vgg", MaxResults=10)

    assert len(vgg_transform_job_10["TransformJobSummaries"]) == 5
    assert (
        vgg_transform_job_10["TransformJobSummaries"][-1]["TransformJobName"] == "vgg-4"
    )
    assert vgg_transform_job_10.get("NextToken") is None


@mock_aws
def test_list_transform_jobs_paginated_with_fragmented_targets():
    client = boto3.client("sagemaker", region_name="us-east-1")
    for i in range(5):
        name = f"xgboost-{i}"
        model_name = f"my-model-{i}"
        MyTransformJobModel(transform_job_name=name, model_name=model_name).save()
    for i in range(5):
        name = f"vgg-{i}"
        MyTransformJobModel(transform_job_name=name, model_name=model_name).save()

    transform_jobs_with_2 = client.list_transform_jobs(NameContains="2", MaxResults=8)
    assert len(transform_jobs_with_2["TransformJobSummaries"]) == 2
    assert transform_jobs_with_2.get("NextToken") is not None

    transform_jobs_with_2_next = client.list_transform_jobs(
        NameContains="2", MaxResults=1, NextToken=transform_jobs_with_2.get("NextToken")
    )
    assert len(transform_jobs_with_2_next["TransformJobSummaries"]) == 0
    assert transform_jobs_with_2_next.get("NextToken") is not None

    transform_jobs_with_2_next_next = client.list_transform_jobs(
        NameContains="2",
        MaxResults=1,
        NextToken=transform_jobs_with_2_next.get("NextToken"),
    )
    assert len(transform_jobs_with_2_next_next["TransformJobSummaries"]) == 0
    assert transform_jobs_with_2_next_next.get("NextToken") is None


@mock_aws
def test_add_tags_to_transform_job():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)
    name = "blah"
    model_name = "my-model"
    resource_arn = "arn:aws:sagemaker:us-east-1:123456789012:transform-job/blah"

    test_transform_job = MyTransformJobModel(
        transform_job_name=name, model_name=model_name
    )
    test_transform_job.save()
    tags = [
        {"Key": "myKey", "Value": "myValue"},
    ]
    response = client.add_tags(ResourceArn=resource_arn, Tags=tags)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = client.list_tags(ResourceArn=resource_arn)
    assert response["Tags"] == tags


@mock_aws
def test_delete_tags_from_transform_job():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)
    name = "blah"
    model_name = "my-model"
    resource_arn = "arn:aws:sagemaker:us-east-1:123456789012:transform-job/blah"
    test_transform_job = MyTransformJobModel(
        transform_job_name=name, model_name=model_name
    )
    test_transform_job.save()

    tags = [
        {"Key": "myKey", "Value": "myValue"},
    ]
    response = client.add_tags(ResourceArn=resource_arn, Tags=tags)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    tag_keys = [tag["Key"] for tag in tags]
    response = client.delete_tags(ResourceArn=resource_arn, TagKeys=tag_keys)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = client.list_tags(ResourceArn=resource_arn)
    assert response["Tags"] == []


@mock_aws
def test_describe_unknown_transform_job():
    client = boto3.client("sagemaker", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.describe_transform_job(TransformJobName="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == (
        "Could not find transform job 'arn:aws:sagemaker:us-east-1:"
        f"{ACCOUNT_ID}:transform-job/unknown'."
    )
