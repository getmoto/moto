# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import boto3
import datetime
import sure  # noqa

from moto import mock_sagemaker
from moto.sts.models import ACCOUNT_ID

FAKE_ROLE_ARN = "arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID)
TEST_REGION_NAME = "us-east-1"


@mock_sagemaker
def test_create_training_job():
    sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    training_job_name = "MyTrainingJob"
    container = "382416733822.dkr.ecr.us-east-1.amazonaws.com/linear-learner:1"
    bucket = "my-bucket"
    prefix = "sagemaker/DEMO-breast-cancer-prediction/"

    params = {
        "RoleArn": FAKE_ROLE_ARN,
        "TrainingJobName": training_job_name,
        "AlgorithmSpecification": {
            "TrainingImage": container,
            "TrainingInputMode": "File",
        },
        "ResourceConfig": {
            "InstanceCount": 1,
            "InstanceType": "ml.c4.2xlarge",
            "VolumeSizeInGB": 10,
        },
        "InputDataConfig": [
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
        ],
        "OutputDataConfig": {"S3OutputPath": "s3://{}/{}/".format(bucket, prefix)},
        "HyperParameters": {
            "feature_dim": "30",
            "mini_batch_size": "100",
            "predictor_type": "regressor",
            "epochs": "10",
            "num_models": "32",
            "loss": "absolute_loss",
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": 60 * 60},
    }

    resp = sagemaker.create_training_job(**params)
    resp["TrainingJobArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:training-job/{}$".format(training_job_name)
    )

    resp = sagemaker.describe_training_job(TrainingJobName=training_job_name)
    resp["TrainingJobName"].should.equal(training_job_name)
    resp["TrainingJobArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:training-job/{}$".format(training_job_name)
    )
    assert resp["ModelArtifacts"]["S3ModelArtifacts"].startswith(
        params["OutputDataConfig"]["S3OutputPath"]
    )
    assert training_job_name in (resp["ModelArtifacts"]["S3ModelArtifacts"])
    assert resp["ModelArtifacts"]["S3ModelArtifacts"].endswith("output/model.tar.gz")
    assert resp["TrainingJobStatus"] == "Completed"
    assert resp["SecondaryStatus"] == "Completed"
    assert resp["HyperParameters"] == params["HyperParameters"]
    assert (
        resp["AlgorithmSpecification"]["TrainingImage"]
        == params["AlgorithmSpecification"]["TrainingImage"]
    )
    assert (
        resp["AlgorithmSpecification"]["TrainingInputMode"]
        == params["AlgorithmSpecification"]["TrainingInputMode"]
    )
    assert "MetricDefinitions" in resp["AlgorithmSpecification"]
    assert "Name" in resp["AlgorithmSpecification"]["MetricDefinitions"][0]
    assert "Regex" in resp["AlgorithmSpecification"]["MetricDefinitions"][0]
    assert resp["RoleArn"] == FAKE_ROLE_ARN
    assert resp["InputDataConfig"] == params["InputDataConfig"]
    assert resp["OutputDataConfig"] == params["OutputDataConfig"]
    assert resp["ResourceConfig"] == params["ResourceConfig"]
    assert resp["StoppingCondition"] == params["StoppingCondition"]
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
