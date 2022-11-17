import boto3
from botocore.exceptions import ClientError
import datetime
import pytest

from moto import mock_sagemaker
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

FAKE_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole"
FAKE_PROCESSING_JOB_NAME = "MyProcessingJob"
FAKE_CONTAINER = "382416733822.dkr.ecr.us-east-1.amazonaws.com/linear-learner:1"
TEST_REGION_NAME = "us-east-1"


@pytest.fixture(name="sagemaker_client")
def fixture_sagemaker_client():
    with mock_sagemaker():
        yield boto3.client("sagemaker", region_name=TEST_REGION_NAME)


class MyProcessingJobModel(object):
    def __init__(
        self,
        processing_job_name,
        role_arn,
        container=None,
        bucket=None,
        prefix=None,
        app_specification=None,
        network_config=None,
        processing_inputs=None,
        processing_output_config=None,
        processing_resources=None,
        stopping_condition=None,
    ):
        self.processing_job_name = processing_job_name
        self.role_arn = role_arn
        self.container = (
            container
            or "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:0.23-1-cpu-py3"
        )
        self.bucket = bucket or "my-bucket"
        self.prefix = prefix or "sagemaker"
        self.app_specification = app_specification or {
            "ImageUri": self.container,
            "ContainerEntrypoint": ["python3"],
        }
        self.network_config = network_config or {
            "EnableInterContainerTrafficEncryption": False,
            "EnableNetworkIsolation": False,
        }
        self.processing_inputs = processing_inputs or [
            {
                "InputName": "input",
                "AppManaged": False,
                "S3Input": {
                    "S3Uri": f"s3://{self.bucket}/{self.prefix}/processing/",
                    "LocalPath": "/opt/ml/processing/input",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File",
                    "S3DataDistributionType": "FullyReplicated",
                    "S3CompressionType": "None",
                },
            }
        ]
        self.processing_output_config = processing_output_config or {
            "Outputs": [
                {
                    "OutputName": "output",
                    "S3Output": {
                        "S3Uri": f"s3://{self.bucket}/{self.prefix}/processing/",
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                    "AppManaged": False,
                }
            ]
        }
        self.processing_resources = processing_resources or {
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m5.large",
                "VolumeSizeInGB": 10,
            },
        }
        self.stopping_condition = stopping_condition or {
            "MaxRuntimeInSeconds": 3600,
        }

    def save(self, sagemaker_client):
        params = {
            "AppSpecification": self.app_specification,
            "NetworkConfig": self.network_config,
            "ProcessingInputs": self.processing_inputs,
            "ProcessingJobName": self.processing_job_name,
            "ProcessingOutputConfig": self.processing_output_config,
            "ProcessingResources": self.processing_resources,
            "RoleArn": self.role_arn,
            "StoppingCondition": self.stopping_condition,
        }

        return sagemaker_client.create_processing_job(**params)


def test_create_processing_job(sagemaker_client):
    bucket = "my-bucket"
    prefix = "my-prefix"
    app_specification = {
        "ImageUri": FAKE_CONTAINER,
        "ContainerEntrypoint": ["python3", "app.py"],
    }
    processing_resources = {
        "ClusterConfig": {
            "InstanceCount": 2,
            "InstanceType": "ml.m5.xlarge",
            "VolumeSizeInGB": 20,
        },
    }
    stopping_condition = {"MaxRuntimeInSeconds": 60 * 60}

    job = MyProcessingJobModel(
        processing_job_name=FAKE_PROCESSING_JOB_NAME,
        role_arn=FAKE_ROLE_ARN,
        container=FAKE_CONTAINER,
        bucket=bucket,
        prefix=prefix,
        app_specification=app_specification,
        processing_resources=processing_resources,
        stopping_condition=stopping_condition,
    )
    resp = job.save(sagemaker_client)
    resp["ProcessingJobArn"].should.match(
        rf"^arn:aws:sagemaker:.*:.*:processing-job/{FAKE_PROCESSING_JOB_NAME}$"
    )

    resp = sagemaker_client.describe_processing_job(
        ProcessingJobName=FAKE_PROCESSING_JOB_NAME
    )
    resp["ProcessingJobName"].should.equal(FAKE_PROCESSING_JOB_NAME)
    resp["ProcessingJobArn"].should.match(
        rf"^arn:aws:sagemaker:.*:.*:processing-job/{FAKE_PROCESSING_JOB_NAME}$"
    )
    assert "python3" in resp["AppSpecification"]["ContainerEntrypoint"]
    assert "app.py" in resp["AppSpecification"]["ContainerEntrypoint"]
    assert resp["RoleArn"] == FAKE_ROLE_ARN
    assert resp["ProcessingJobStatus"] == "Completed"
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)


def test_list_processing_jobs(sagemaker_client):
    test_processing_job = MyProcessingJobModel(
        processing_job_name=FAKE_PROCESSING_JOB_NAME, role_arn=FAKE_ROLE_ARN
    )
    test_processing_job.save(sagemaker_client)
    processing_jobs = sagemaker_client.list_processing_jobs()
    assert len(processing_jobs["ProcessingJobSummaries"]).should.equal(1)
    assert processing_jobs["ProcessingJobSummaries"][0][
        "ProcessingJobName"
    ].should.equal(FAKE_PROCESSING_JOB_NAME)

    assert processing_jobs["ProcessingJobSummaries"][0][
        "ProcessingJobArn"
    ].should.match(
        rf"^arn:aws:sagemaker:.*:.*:processing-job/{FAKE_PROCESSING_JOB_NAME}$"
    )
    assert processing_jobs.get("NextToken") is None


def test_list_processing_jobs_multiple(sagemaker_client):
    name_job_1 = "blah"
    arn_job_1 = "arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar"
    test_processing_job_1 = MyProcessingJobModel(
        processing_job_name=name_job_1, role_arn=arn_job_1
    )
    test_processing_job_1.save(sagemaker_client)

    name_job_2 = "blah2"
    arn_job_2 = "arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar2"
    test_processing_job_2 = MyProcessingJobModel(
        processing_job_name=name_job_2, role_arn=arn_job_2
    )
    test_processing_job_2.save(sagemaker_client)
    processing_jobs_limit = sagemaker_client.list_processing_jobs(MaxResults=1)
    assert len(processing_jobs_limit["ProcessingJobSummaries"]).should.equal(1)

    processing_jobs = sagemaker_client.list_processing_jobs()
    assert len(processing_jobs["ProcessingJobSummaries"]).should.equal(2)
    assert processing_jobs.get("NextToken").should.be.none


def test_list_processing_jobs_none(sagemaker_client):
    processing_jobs = sagemaker_client.list_processing_jobs()
    assert len(processing_jobs["ProcessingJobSummaries"]).should.equal(0)


def test_list_processing_jobs_should_validate_input(sagemaker_client):
    junk_status_equals = "blah"
    with pytest.raises(ClientError) as ex:
        sagemaker_client.list_processing_jobs(StatusEquals=junk_status_equals)
    expected_error = f"1 validation errors detected: Value '{junk_status_equals}' at 'statusEquals' failed to satisfy constraint: Member must satisfy enum value set: ['Completed', 'Stopped', 'InProgress', 'Stopping', 'Failed']"
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["Error"]["Message"] == expected_error

    junk_next_token = "asdf"
    with pytest.raises(ClientError) as ex:
        sagemaker_client.list_processing_jobs(NextToken=junk_next_token)
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert (
        ex.value.response["Error"]["Message"]
        == 'Invalid pagination token because "{0}".'
    )


def test_list_processing_jobs_with_name_filters(sagemaker_client):
    for i in range(5):
        name = f"xgboost-{i}"
        arn = f"arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar-{i}"
        MyProcessingJobModel(processing_job_name=name, role_arn=arn).save(
            sagemaker_client
        )

    for i in range(5):
        name = f"vgg-{i}"
        arn = f"arn:aws:sagemaker:us-east-1:000000000000:x-x/barfoo-{i}"
        MyProcessingJobModel(processing_job_name=name, role_arn=arn).save(
            sagemaker_client
        )

    xgboost_processing_jobs = sagemaker_client.list_processing_jobs(
        NameContains="xgboost"
    )
    assert len(xgboost_processing_jobs["ProcessingJobSummaries"]).should.equal(5)

    processing_jobs_with_2 = sagemaker_client.list_processing_jobs(NameContains="2")
    assert len(processing_jobs_with_2["ProcessingJobSummaries"]).should.equal(2)


def test_list_processing_jobs_paginated(sagemaker_client):
    for i in range(5):
        name = f"xgboost-{i}"
        arn = f"arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar-{i}"
        MyProcessingJobModel(processing_job_name=name, role_arn=arn).save(
            sagemaker_client
        )

    xgboost_processing_job_1 = sagemaker_client.list_processing_jobs(
        NameContains="xgboost", MaxResults=1
    )
    assert len(xgboost_processing_job_1["ProcessingJobSummaries"]).should.equal(1)
    assert xgboost_processing_job_1["ProcessingJobSummaries"][0][
        "ProcessingJobName"
    ].should.equal("xgboost-0")
    assert xgboost_processing_job_1.get("NextToken").should_not.be.none

    xgboost_processing_job_next = sagemaker_client.list_processing_jobs(
        NameContains="xgboost",
        MaxResults=1,
        NextToken=xgboost_processing_job_1.get("NextToken"),
    )
    assert len(xgboost_processing_job_next["ProcessingJobSummaries"]).should.equal(1)
    assert xgboost_processing_job_next["ProcessingJobSummaries"][0][
        "ProcessingJobName"
    ].should.equal("xgboost-1")
    assert xgboost_processing_job_next.get("NextToken").should_not.be.none


def test_list_processing_jobs_paginated_with_target_in_middle(sagemaker_client):
    for i in range(5):
        name = f"xgboost-{i}"
        arn = f"arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar-{i}"
        MyProcessingJobModel(processing_job_name=name, role_arn=arn).save(
            sagemaker_client
        )

    for i in range(5):
        name = f"vgg-{i}"
        arn = f"arn:aws:sagemaker:us-east-1:000000000000:x-x/barfoo-{i}"
        MyProcessingJobModel(processing_job_name=name, role_arn=arn).save(
            sagemaker_client
        )

    vgg_processing_job_1 = sagemaker_client.list_processing_jobs(
        NameContains="vgg", MaxResults=1
    )
    assert len(vgg_processing_job_1["ProcessingJobSummaries"]).should.equal(0)
    assert vgg_processing_job_1.get("NextToken").should_not.be.none

    vgg_processing_job_6 = sagemaker_client.list_processing_jobs(
        NameContains="vgg", MaxResults=6
    )

    assert len(vgg_processing_job_6["ProcessingJobSummaries"]).should.equal(1)
    assert vgg_processing_job_6["ProcessingJobSummaries"][0][
        "ProcessingJobName"
    ].should.equal("vgg-0")
    assert vgg_processing_job_6.get("NextToken").should_not.be.none

    vgg_processing_job_10 = sagemaker_client.list_processing_jobs(
        NameContains="vgg", MaxResults=10
    )

    assert len(vgg_processing_job_10["ProcessingJobSummaries"]).should.equal(5)
    assert vgg_processing_job_10["ProcessingJobSummaries"][-1][
        "ProcessingJobName"
    ].should.equal("vgg-4")
    assert vgg_processing_job_10.get("NextToken").should.be.none


def test_list_processing_jobs_paginated_with_fragmented_targets(sagemaker_client):
    for i in range(5):
        name = f"xgboost-{i}"
        arn = f"arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar-{i}"
        MyProcessingJobModel(processing_job_name=name, role_arn=arn).save(
            sagemaker_client
        )

    for i in range(5):
        name = f"vgg-{i}"
        arn = f"arn:aws:sagemaker:us-east-1:000000000000:x-x/barfoo-{i}"
        MyProcessingJobModel(processing_job_name=name, role_arn=arn).save(
            sagemaker_client
        )

    processing_jobs_with_2 = sagemaker_client.list_processing_jobs(
        NameContains="2", MaxResults=8
    )
    assert len(processing_jobs_with_2["ProcessingJobSummaries"]).should.equal(2)
    assert processing_jobs_with_2.get("NextToken").should_not.be.none

    processing_jobs_with_2_next = sagemaker_client.list_processing_jobs(
        NameContains="2",
        MaxResults=1,
        NextToken=processing_jobs_with_2.get("NextToken"),
    )
    assert len(processing_jobs_with_2_next["ProcessingJobSummaries"]).should.equal(0)
    assert processing_jobs_with_2_next.get("NextToken").should_not.be.none

    processing_jobs_with_2_next_next = sagemaker_client.list_processing_jobs(
        NameContains="2",
        MaxResults=1,
        NextToken=processing_jobs_with_2_next.get("NextToken"),
    )
    assert len(processing_jobs_with_2_next_next["ProcessingJobSummaries"]).should.equal(
        0
    )
    assert processing_jobs_with_2_next_next.get("NextToken").should.be.none


def test_add_and_delete_tags_in_training_job(sagemaker_client):
    processing_job_name = "MyProcessingJob"
    role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole"
    container = "382416733822.dkr.ecr.us-east-1.amazonaws.com/linear-learner:1"
    bucket = "my-bucket"
    prefix = "my-prefix"
    app_specification = {
        "ImageUri": container,
        "ContainerEntrypoint": ["python3", "app.py"],
    }
    processing_resources = {
        "ClusterConfig": {
            "InstanceCount": 2,
            "InstanceType": "ml.m5.xlarge",
            "VolumeSizeInGB": 20,
        },
    }
    stopping_condition = {"MaxRuntimeInSeconds": 60 * 60}

    job = MyProcessingJobModel(
        processing_job_name,
        role_arn,
        container=container,
        bucket=bucket,
        prefix=prefix,
        app_specification=app_specification,
        processing_resources=processing_resources,
        stopping_condition=stopping_condition,
    )
    resp = job.save(sagemaker_client)
    resource_arn = resp["ProcessingJobArn"]

    tags = [
        {"Key": "myKey", "Value": "myValue"},
    ]
    response = sagemaker_client.add_tags(ResourceArn=resource_arn, Tags=tags)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = sagemaker_client.list_tags(ResourceArn=resource_arn)
    assert response["Tags"] == tags

    tag_keys = [tag["Key"] for tag in tags]
    response = sagemaker_client.delete_tags(ResourceArn=resource_arn, TagKeys=tag_keys)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = sagemaker_client.list_tags(ResourceArn=resource_arn)
    assert response["Tags"] == []
