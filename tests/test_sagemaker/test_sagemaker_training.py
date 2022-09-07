import boto3
from botocore.exceptions import ClientError
import datetime
import sure  # noqa # pylint: disable=unused-import
import pytest

from moto import mock_sagemaker
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

FAKE_ROLE_ARN = "arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID)
TEST_REGION_NAME = "us-east-1"


class MyTrainingJobModel(object):
    def __init__(
        self,
        training_job_name,
        role_arn,
        container=None,
        bucket=None,
        prefix=None,
        algorithm_specification=None,
        resource_config=None,
        input_data_config=None,
        output_data_config=None,
        hyper_parameters=None,
        stopping_condition=None,
    ):
        self.training_job_name = training_job_name
        self.role_arn = role_arn
        self.container = (
            container or "382416733822.dkr.ecr.us-east-1.amazonaws.com/linear-learner:1"
        )
        self.bucket = bucket or "my-bucket"
        self.prefix = prefix or "sagemaker/DEMO-breast-cancer-prediction/"
        self.algorithm_specification = algorithm_specification or {
            "TrainingImage": self.container,
            "TrainingInputMode": "File",
        }
        self.resource_config = resource_config or {
            "InstanceCount": 1,
            "InstanceType": "ml.c4.2xlarge",
            "VolumeSizeInGB": 10,
        }
        self.input_data_config = input_data_config or [
            {
                "ChannelName": "train",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": "s3://{}/{}/train/".format(self.bucket, self.prefix),
                        "S3DataDistributionType": "ShardedByS3Key",
                    }
                },
                "CompressionType": "None",
                "RecordWrapperType": "None",
            },
            {
                "ChannelName": "validation",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": "s3://{}/{}/validation/".format(
                            self.bucket, self.prefix
                        ),
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "CompressionType": "None",
                "RecordWrapperType": "None",
            },
        ]
        self.output_data_config = output_data_config or {
            "S3OutputPath": "s3://{}/{}/".format(self.bucket, self.prefix)
        }
        self.hyper_parameters = hyper_parameters or {
            "feature_dim": "30",
            "mini_batch_size": "100",
            "predictor_type": "regressor",
            "epochs": "10",
            "num_models": "32",
            "loss": "absolute_loss",
        }

        self.stopping_condition = stopping_condition or {"MaxRuntimeInSeconds": 60 * 60}

    def save(self):
        sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

        params = {
            "RoleArn": self.role_arn,
            "TrainingJobName": self.training_job_name,
            "AlgorithmSpecification": self.algorithm_specification,
            "ResourceConfig": self.resource_config,
            "InputDataConfig": self.input_data_config,
            "OutputDataConfig": self.output_data_config,
            "HyperParameters": self.hyper_parameters,
            "StoppingCondition": self.stopping_condition,
        }
        return sagemaker.create_training_job(**params)


@mock_sagemaker
def test_create_training_job():
    sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    training_job_name = "MyTrainingJob"
    role_arn = "arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID)
    container = "382416733822.dkr.ecr.us-east-1.amazonaws.com/linear-learner:1"
    bucket = "my-bucket"
    prefix = "sagemaker/DEMO-breast-cancer-prediction/"
    algorithm_specification = {
        "TrainingImage": container,
        "TrainingInputMode": "File",
    }
    resource_config = {
        "InstanceCount": 1,
        "InstanceType": "ml.c4.2xlarge",
        "VolumeSizeInGB": 10,
    }
    input_data_config = [
        {
            "ChannelName": "train",
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": "s3://{}/{}/train/".format(bucket, prefix),
                    "S3DataDistributionType": "ShardedByS3Key",
                }
            },
            "CompressionType": "None",
            "RecordWrapperType": "None",
        },
        {
            "ChannelName": "validation",
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": "s3://{}/{}/validation/".format(bucket, prefix),
                    "S3DataDistributionType": "FullyReplicated",
                }
            },
            "CompressionType": "None",
            "RecordWrapperType": "None",
        },
    ]
    output_data_config = {"S3OutputPath": "s3://{}/{}/".format(bucket, prefix)}
    hyper_parameters = {
        "feature_dim": "30",
        "mini_batch_size": "100",
        "predictor_type": "regressor",
        "epochs": "10",
        "num_models": "32",
        "loss": "absolute_loss",
    }
    stopping_condition = {"MaxRuntimeInSeconds": 60 * 60}

    job = MyTrainingJobModel(
        training_job_name,
        role_arn,
        container=container,
        bucket=bucket,
        prefix=prefix,
        algorithm_specification=algorithm_specification,
        resource_config=resource_config,
        input_data_config=input_data_config,
        output_data_config=output_data_config,
        hyper_parameters=hyper_parameters,
        stopping_condition=stopping_condition,
    )
    resp = job.save()
    resp["TrainingJobArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:training-job/{}$".format(training_job_name)
    )

    resp = sagemaker.describe_training_job(TrainingJobName=training_job_name)
    resp["TrainingJobName"].should.equal(training_job_name)
    resp["TrainingJobArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:training-job/{}$".format(training_job_name)
    )
    assert resp["ModelArtifacts"]["S3ModelArtifacts"].startswith(
        output_data_config["S3OutputPath"]
    )
    assert training_job_name in (resp["ModelArtifacts"]["S3ModelArtifacts"])
    assert resp["ModelArtifacts"]["S3ModelArtifacts"].endswith("output/model.tar.gz")
    assert resp["TrainingJobStatus"] == "Completed"
    assert resp["SecondaryStatus"] == "Completed"
    assert resp["HyperParameters"] == hyper_parameters
    assert (
        resp["AlgorithmSpecification"]["TrainingImage"]
        == algorithm_specification["TrainingImage"]
    )
    assert (
        resp["AlgorithmSpecification"]["TrainingInputMode"]
        == algorithm_specification["TrainingInputMode"]
    )
    assert "MetricDefinitions" in resp["AlgorithmSpecification"]
    assert "Name" in resp["AlgorithmSpecification"]["MetricDefinitions"][0]
    assert "Regex" in resp["AlgorithmSpecification"]["MetricDefinitions"][0]
    assert resp["RoleArn"] == role_arn
    assert resp["InputDataConfig"] == input_data_config
    assert resp["OutputDataConfig"] == output_data_config
    assert resp["ResourceConfig"] == resource_config
    assert resp["StoppingCondition"] == stopping_condition
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert isinstance(resp["TrainingStartTime"], datetime.datetime)
    assert isinstance(resp["TrainingEndTime"], datetime.datetime)
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)
    assert "SecondaryStatusTransitions" in resp
    assert "Status" in resp["SecondaryStatusTransitions"][0]
    assert "StartTime" in resp["SecondaryStatusTransitions"][0]
    assert "EndTime" in resp["SecondaryStatusTransitions"][0]
    assert "StatusMessage" in resp["SecondaryStatusTransitions"][0]
    assert "FinalMetricDataList" in resp
    assert "MetricName" in resp["FinalMetricDataList"][0]
    assert "Value" in resp["FinalMetricDataList"][0]
    assert "Timestamp" in resp["FinalMetricDataList"][0]

    pass


@mock_sagemaker
def test_list_training_jobs():
    client = boto3.client("sagemaker", region_name="us-east-1")
    name = "blah"
    arn = "arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar"
    test_training_job = MyTrainingJobModel(training_job_name=name, role_arn=arn)
    test_training_job.save()
    training_jobs = client.list_training_jobs()
    assert len(training_jobs["TrainingJobSummaries"]).should.equal(1)
    assert training_jobs["TrainingJobSummaries"][0]["TrainingJobName"].should.equal(
        name
    )

    assert training_jobs["TrainingJobSummaries"][0]["TrainingJobArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:training-job/{}$".format(name)
    )
    assert training_jobs.get("NextToken") is None


@mock_sagemaker
def test_list_training_jobs_multiple():
    client = boto3.client("sagemaker", region_name="us-east-1")
    name_job_1 = "blah"
    arn_job_1 = "arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar"
    test_training_job_1 = MyTrainingJobModel(
        training_job_name=name_job_1, role_arn=arn_job_1
    )
    test_training_job_1.save()

    name_job_2 = "blah2"
    arn_job_2 = "arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar2"
    test_training_job_2 = MyTrainingJobModel(
        training_job_name=name_job_2, role_arn=arn_job_2
    )
    test_training_job_2.save()
    training_jobs_limit = client.list_training_jobs(MaxResults=1)
    assert len(training_jobs_limit["TrainingJobSummaries"]).should.equal(1)

    training_jobs = client.list_training_jobs()
    assert len(training_jobs["TrainingJobSummaries"]).should.equal(2)
    assert training_jobs.get("NextToken").should.be.none


@mock_sagemaker
def test_list_training_jobs_none():
    client = boto3.client("sagemaker", region_name="us-east-1")
    training_jobs = client.list_training_jobs()
    assert len(training_jobs["TrainingJobSummaries"]).should.equal(0)


@mock_sagemaker
def test_list_training_jobs_should_validate_input():
    client = boto3.client("sagemaker", region_name="us-east-1")
    junk_status_equals = "blah"
    with pytest.raises(ClientError) as ex:
        client.list_training_jobs(StatusEquals=junk_status_equals)
    expected_error = f"1 validation errors detected: Value '{junk_status_equals}' at 'statusEquals' failed to satisfy constraint: Member must satisfy enum value set: ['Completed', 'Stopped', 'InProgress', 'Stopping', 'Failed']"
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["Error"]["Message"] == expected_error

    junk_next_token = "asdf"
    with pytest.raises(ClientError) as ex:
        client.list_training_jobs(NextToken=junk_next_token)
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert (
        ex.value.response["Error"]["Message"]
        == 'Invalid pagination token because "{0}".'
    )


@mock_sagemaker
def test_list_training_jobs_with_name_filters():
    client = boto3.client("sagemaker", region_name="us-east-1")
    for i in range(5):
        name = "xgboost-{}".format(i)
        arn = "arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar-{}".format(i)
        MyTrainingJobModel(training_job_name=name, role_arn=arn).save()
    for i in range(5):
        name = "vgg-{}".format(i)
        arn = "arn:aws:sagemaker:us-east-1:000000000000:x-x/barfoo-{}".format(i)
        MyTrainingJobModel(training_job_name=name, role_arn=arn).save()
    xgboost_training_jobs = client.list_training_jobs(NameContains="xgboost")
    assert len(xgboost_training_jobs["TrainingJobSummaries"]).should.equal(5)

    training_jobs_with_2 = client.list_training_jobs(NameContains="2")
    assert len(training_jobs_with_2["TrainingJobSummaries"]).should.equal(2)


@mock_sagemaker
def test_list_training_jobs_paginated():
    client = boto3.client("sagemaker", region_name="us-east-1")
    for i in range(5):
        name = "xgboost-{}".format(i)
        arn = "arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar-{}".format(i)
        MyTrainingJobModel(training_job_name=name, role_arn=arn).save()
    xgboost_training_job_1 = client.list_training_jobs(
        NameContains="xgboost", MaxResults=1
    )
    assert len(xgboost_training_job_1["TrainingJobSummaries"]).should.equal(1)
    assert xgboost_training_job_1["TrainingJobSummaries"][0][
        "TrainingJobName"
    ].should.equal("xgboost-0")
    assert xgboost_training_job_1.get("NextToken").should_not.be.none

    xgboost_training_job_next = client.list_training_jobs(
        NameContains="xgboost",
        MaxResults=1,
        NextToken=xgboost_training_job_1.get("NextToken"),
    )
    assert len(xgboost_training_job_next["TrainingJobSummaries"]).should.equal(1)
    assert xgboost_training_job_next["TrainingJobSummaries"][0][
        "TrainingJobName"
    ].should.equal("xgboost-1")
    assert xgboost_training_job_next.get("NextToken").should_not.be.none


@mock_sagemaker
def test_list_training_jobs_paginated_with_target_in_middle():
    client = boto3.client("sagemaker", region_name="us-east-1")
    for i in range(5):
        name = "xgboost-{}".format(i)
        arn = "arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar-{}".format(i)
        MyTrainingJobModel(training_job_name=name, role_arn=arn).save()
    for i in range(5):
        name = "vgg-{}".format(i)
        arn = "arn:aws:sagemaker:us-east-1:000000000000:x-x/barfoo-{}".format(i)
        MyTrainingJobModel(training_job_name=name, role_arn=arn).save()

    vgg_training_job_1 = client.list_training_jobs(NameContains="vgg", MaxResults=1)
    assert len(vgg_training_job_1["TrainingJobSummaries"]).should.equal(0)
    assert vgg_training_job_1.get("NextToken").should_not.be.none

    vgg_training_job_6 = client.list_training_jobs(NameContains="vgg", MaxResults=6)

    assert len(vgg_training_job_6["TrainingJobSummaries"]).should.equal(1)
    assert vgg_training_job_6["TrainingJobSummaries"][0][
        "TrainingJobName"
    ].should.equal("vgg-0")
    assert vgg_training_job_6.get("NextToken").should_not.be.none

    vgg_training_job_10 = client.list_training_jobs(NameContains="vgg", MaxResults=10)

    assert len(vgg_training_job_10["TrainingJobSummaries"]).should.equal(5)
    assert vgg_training_job_10["TrainingJobSummaries"][-1][
        "TrainingJobName"
    ].should.equal("vgg-4")
    assert vgg_training_job_10.get("NextToken").should.be.none


@mock_sagemaker
def test_list_training_jobs_paginated_with_fragmented_targets():
    client = boto3.client("sagemaker", region_name="us-east-1")
    for i in range(5):
        name = "xgboost-{}".format(i)
        arn = "arn:aws:sagemaker:us-east-1:000000000000:x-x/foobar-{}".format(i)
        MyTrainingJobModel(training_job_name=name, role_arn=arn).save()
    for i in range(5):
        name = "vgg-{}".format(i)
        arn = "arn:aws:sagemaker:us-east-1:000000000000:x-x/barfoo-{}".format(i)
        MyTrainingJobModel(training_job_name=name, role_arn=arn).save()

    training_jobs_with_2 = client.list_training_jobs(NameContains="2", MaxResults=8)
    assert len(training_jobs_with_2["TrainingJobSummaries"]).should.equal(2)
    assert training_jobs_with_2.get("NextToken").should_not.be.none

    training_jobs_with_2_next = client.list_training_jobs(
        NameContains="2", MaxResults=1, NextToken=training_jobs_with_2.get("NextToken")
    )
    assert len(training_jobs_with_2_next["TrainingJobSummaries"]).should.equal(0)
    assert training_jobs_with_2_next.get("NextToken").should_not.be.none

    training_jobs_with_2_next_next = client.list_training_jobs(
        NameContains="2",
        MaxResults=1,
        NextToken=training_jobs_with_2_next.get("NextToken"),
    )
    assert len(training_jobs_with_2_next_next["TrainingJobSummaries"]).should.equal(0)
    assert training_jobs_with_2_next_next.get("NextToken").should.be.none


@mock_sagemaker
def test_add_tags_to_training_job():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)
    name = "blah"
    resource_arn = f"arn:aws:sagemaker:us-east-1:000000000000:training-job/{name}"
    test_training_job = MyTrainingJobModel(
        training_job_name=name, role_arn=resource_arn
    )
    test_training_job.save()

    tags = [
        {"Key": "myKey", "Value": "myValue"},
    ]
    response = client.add_tags(ResourceArn=resource_arn, Tags=tags)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = client.list_tags(ResourceArn=resource_arn)
    assert response["Tags"] == tags


@mock_sagemaker
def test_delete_tags_from_training_job():
    client = boto3.client("sagemaker", region_name=TEST_REGION_NAME)
    name = "blah"
    resource_arn = f"arn:aws:sagemaker:us-east-1:000000000000:training-job/{name}"
    test_training_job = MyTrainingJobModel(
        training_job_name=name, role_arn=resource_arn
    )
    test_training_job.save()

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
