"""Unit tests for sagemaker-supported APIs."""

import datetime

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_hyper_parameter_tuning_job():
    client = boto3.client("sagemaker", region_name="us-east-2")
    resp = client.create_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="testhyperparametertuningjob",
        HyperParameterTuningJobConfig={
            "Strategy": "Bayesian",
            "ResourceLimits": {
                "MaxNumberOfTrainingJobs": 123,
                "MaxParallelTrainingJobs": 123,
                "MaxRuntimeInSeconds": 123,
            },
        },
    )

    assert (
        resp["HyperParameterTuningJobArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:hyper-parameter-tuning-job/testhyperparametertuningjob"
    )


@mock_aws
def test_describe_hyper_parameter_tuning_job_defaults():
    client = boto3.client("sagemaker", region_name="us-east-2")
    client.create_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="testhyperparametertuningjob",
        HyperParameterTuningJobConfig={
            "Strategy": "Bayesian",
            "ResourceLimits": {
                "MaxNumberOfTrainingJobs": 123,
                "MaxParallelTrainingJobs": 123,
                "MaxRuntimeInSeconds": 123,
            },
        },
    )
    resp = client.describe_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="testhyperparametertuningjob"
    )
    assert resp["HyperParameterTuningJobName"] == "testhyperparametertuningjob"
    assert (
        resp["HyperParameterTuningJobArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:hyper-parameter-tuning-job/testhyperparametertuningjob"
    )
    assert resp["HyperParameterTuningJobConfig"] == {
        "Strategy": "Bayesian",
        "ResourceLimits": {
            "MaxNumberOfTrainingJobs": 123,
            "MaxParallelTrainingJobs": 123,
            "MaxRuntimeInSeconds": 123,
        },
    }
    assert resp["HyperParameterTuningJobStatus"] == "Completed"
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert isinstance(resp["HyperParameterTuningEndTime"], datetime.datetime)
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)
    assert resp["TrainingJobStatusCounters"] == {
        "Completed": 1,
        "InProgress": 0,
        "NonRetryableError": 0,
        "RetryableError": 0,
        "Stopped": 0,
    }
    assert resp["ObjectiveStatusCounters"] == {
        "Failed": 0,
        "Pending": 0,
        "Succeeded": 1,
    }
    assert resp["BestTrainingJob"] == {
        "TrainingJobDefinitionName": "string",
        "TrainingJobName": "FakeTrainingJobName",
        "TrainingJobArn": "FakeTrainingJobArn",
        "TuningJobName": "FakeTuningJobName",
        "CreationTime": datetime.datetime(2024, 1, 1),
        "TrainingStartTime": datetime.datetime(2024, 1, 1),
        "TrainingEndTime": datetime.datetime(2024, 1, 1),
        "TrainingJobStatus": "Completed",
        "TunedHyperParameters": {"string": "TunedHyperParameters"},
        "FailureReason": "string",
        "FinalHyperParameterTuningJobObjectiveMetric": {
            "Type": "Maximize",
            "MetricName": "Accuracy",
            "Value": 1,
        },
        "ObjectiveStatus": "Succeeded",
    }
    assert resp["OverallBestTrainingJob"] == {
        "TrainingJobDefinitionName": "FakeTrainingJobDefinitionName",
        "TrainingJobName": "FakeTrainingJobName",
        "TrainingJobArn": "FakeTrainingJobArn",
        "TuningJobName": "FakeTuningJobName",
        "CreationTime": datetime.datetime(2024, 1, 1),
        "TrainingStartTime": datetime.datetime(2024, 1, 1),
        "TrainingEndTime": datetime.datetime(2024, 1, 1),
        "TrainingJobStatus": "Completed",
        "TunedHyperParameters": {"string": "FakeTunedHyperParameters"},
        "FailureReason": "FakeFailureReason",
        "FinalHyperParameterTuningJobObjectiveMetric": {
            "Type": "Maximize",
            "MetricName": "Acccuracy",
            "Value": 1,
        },
        "ObjectiveStatus": "Succeeded",
    }
    assert resp["FailureReason"] == ""
    assert resp["TuningJobCompletionDetails"] == {
        "NumberOfTrainingJobsObjectiveNotImproving": 123,
        "ConvergenceDetectedTime": datetime.datetime(2024, 1, 1),
    }
    assert resp["ConsumedResources"] == {"RuntimeInSeconds": 123}


@mock_aws
def test_describe_hyper_parameter_tuning_job():
    client = boto3.client("sagemaker", region_name="us-east-2")
    client.create_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="testhyperparametertuningjob",
        HyperParameterTuningJobConfig={
            "Strategy": "Bayesian",
            "ResourceLimits": {
                "MaxNumberOfTrainingJobs": 123,
                "MaxParallelTrainingJobs": 123,
                "MaxRuntimeInSeconds": 123,
            },
            "StrategyConfig": {
                "HyperbandStrategyConfig": {"MinResource": 123, "MaxResource": 123}
            },
            "HyperParameterTuningJobObjective": {
                "Type": "Maximize",
                "MetricName": "string",
            },
            "ParameterRanges": {
                "IntegerParameterRanges": [
                    {
                        "Name": "string",
                        "MinValue": "string",
                        "MaxValue": "string",
                        "ScalingType": "Auto",
                    },
                ],
            },
            "TrainingJobEarlyStoppingType": "Auto",
            "TuningJobCompletionCriteria": {
                "TargetObjectiveMetricValue": 123,
                "BestObjectiveNotImproving": {
                    "MaxNumberOfTrainingJobsNotImproving": 123
                },
                "ConvergenceDetected": {"CompleteOnConvergence": "Enabled"},
            },
            "RandomSeed": 123,
        },
        TrainingJobDefinition={
            "DefinitionName": "string",
            "TuningObjective": {"Type": "Maximize", "MetricName": "string"},
            "HyperParameterRanges": {
                "IntegerParameterRanges": [
                    {
                        "Name": "string",
                        "MinValue": "string",
                        "MaxValue": "string",
                        "ScalingType": "Auto",
                    },
                ],
                "ContinuousParameterRanges": [
                    {
                        "Name": "string",
                        "MinValue": "string",
                        "MaxValue": "string",
                        "ScalingType": "Auto",
                    },
                ],
                "CategoricalParameterRanges": [
                    {
                        "Name": "string",
                        "Values": [
                            "string",
                        ],
                    },
                ],
                "AutoParameters": [
                    {"Name": "string", "ValueHint": "string"},
                ],
            },
            "StaticHyperParameters": {"string": "string"},
            "AlgorithmSpecification": {
                "TrainingImage": "string",
                "TrainingInputMode": "Pipe",
                "AlgorithmName": "string",
                "MetricDefinitions": [
                    {"Name": "string", "Regex": "string"},
                ],
            },
            "RoleArn": f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
            "InputDataConfig": [
                {
                    "ChannelName": "string",
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            "S3Uri": "string",
                            "S3DataDistributionType": "FullyReplicated",
                            "AttributeNames": [
                                "string",
                            ],
                            "InstanceGroupNames": [
                                "string",
                            ],
                        },
                        "FileSystemDataSource": {
                            "FileSystemId": "testfilesystemid",
                            "FileSystemAccessMode": "rw",
                            "FileSystemType": "EFS",
                            "DirectoryPath": "string",
                        },
                    },
                    "ContentType": "string",
                    "CompressionType": "Gzip",
                    "RecordWrapperType": "RecordIO",
                    "InputMode": "Pipe",
                    "ShuffleConfig": {"Seed": 123},
                },
            ],
            "VpcConfig": {
                "SecurityGroupIds": [
                    "string",
                ],
                "Subnets": [
                    "string",
                ],
            },
            "OutputDataConfig": {
                "KmsKeyId": "string",
                "S3OutputPath": "string",
                "CompressionType": "GZIP",
            },
            "ResourceConfig": {
                "InstanceType": "ml.m4.xlarge",
                "InstanceCount": 123,
                "VolumeSizeInGB": 123,
                "VolumeKmsKeyId": "string",
                "KeepAlivePeriodInSeconds": 123,
                "InstanceGroups": [
                    {
                        "InstanceType": "ml.m4.xlarge",
                        "InstanceCount": 123,
                        "InstanceGroupName": "string",
                    },
                ],
            },
            "HyperParameterTuningResourceConfig": {
                "InstanceType": "ml.m4.xlarge",
                "InstanceCount": 123,
                "VolumeSizeInGB": 123,
                "VolumeKmsKeyId": "string",
                "AllocationStrategy": "Prioritized",
                "InstanceConfigs": [
                    {
                        "InstanceType": "ml.m4.xlarge",
                        "InstanceCount": 123,
                        "VolumeSizeInGB": 123,
                    },
                ],
            },
            "StoppingCondition": {
                "MaxRuntimeInSeconds": 123,
                "MaxWaitTimeInSeconds": 123,
                "MaxPendingTimeInSeconds": 7200,
            },
            "EnableNetworkIsolation": True,
            "EnableInterContainerTrafficEncryption": True,
            "EnableManagedSpotTraining": True,
            "CheckpointConfig": {"S3Uri": "string", "LocalPath": "string"},
            "RetryStrategy": {"MaximumRetryAttempts": 123},
            "Environment": {"string": "string"},
        },
        TrainingJobDefinitions=[
            {
                "DefinitionName": "string",
                "TuningObjective": {
                    "Type": "Maximize",
                    "MetricName": "string",
                },
                "HyperParameterRanges": {
                    "IntegerParameterRanges": [
                        {
                            "Name": "string",
                            "MinValue": "string",
                            "MaxValue": "string",
                            "ScalingType": "Auto",
                        },
                    ],
                    "ContinuousParameterRanges": [
                        {
                            "Name": "string",
                            "MinValue": "string",
                            "MaxValue": "string",
                            "ScalingType": "Auto",
                        },
                    ],
                    "CategoricalParameterRanges": [
                        {
                            "Name": "string",
                            "Values": [
                                "string",
                            ],
                        },
                    ],
                    "AutoParameters": [
                        {"Name": "string", "ValueHint": "string"},
                    ],
                },
                "StaticHyperParameters": {"string": "string"},
                "AlgorithmSpecification": {
                    "TrainingImage": "string",
                    "TrainingInputMode": "Pipe",
                    "AlgorithmName": "string",
                    "MetricDefinitions": [
                        {"Name": "string", "Regex": "string"},
                    ],
                },
                "RoleArn": f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
                "InputDataConfig": [
                    {
                        "ChannelName": "string",
                        "DataSource": {
                            "S3DataSource": {
                                "S3DataType": "ManifestFile",
                                "S3Uri": "string",
                                "S3DataDistributionType": "FullyReplicated",
                                "AttributeNames": [
                                    "string",
                                ],
                                "InstanceGroupNames": [
                                    "string",
                                ],
                            },
                            "FileSystemDataSource": {
                                "FileSystemId": "testfilesystemid",
                                "FileSystemAccessMode": "rw",
                                "FileSystemType": "EFS",
                                "DirectoryPath": "string",
                            },
                        },
                        "ContentType": "string",
                        "CompressionType": "Gzip",
                        "RecordWrapperType": "RecordIO",
                        "InputMode": "Pipe",
                        "ShuffleConfig": {"Seed": 123},
                    },
                ],
                "VpcConfig": {
                    "SecurityGroupIds": [
                        "string",
                    ],
                    "Subnets": [
                        "string",
                    ],
                },
                "OutputDataConfig": {
                    "KmsKeyId": "string",
                    "S3OutputPath": "string",
                    "CompressionType": "GZIP",
                },
                "ResourceConfig": {
                    "InstanceType": "ml.m4.xlarge",
                    "InstanceCount": 123,
                    "VolumeSizeInGB": 123,
                    "VolumeKmsKeyId": "string",
                    "KeepAlivePeriodInSeconds": 123,
                    "InstanceGroups": [
                        {
                            "InstanceType": "ml.m4.xlarge",
                            "InstanceCount": 123,
                            "InstanceGroupName": "string",
                        },
                    ],
                },
                "HyperParameterTuningResourceConfig": {
                    "InstanceType": "ml.m4.xlarge",
                    "InstanceCount": 123,
                    "VolumeSizeInGB": 123,
                    "VolumeKmsKeyId": "string",
                    "AllocationStrategy": "Prioritized",
                    "InstanceConfigs": [
                        {
                            "InstanceType": "ml.m4.xlarge",
                            "InstanceCount": 123,
                            "VolumeSizeInGB": 123,
                        },
                    ],
                },
                "StoppingCondition": {
                    "MaxRuntimeInSeconds": 123,
                    "MaxWaitTimeInSeconds": 123,
                    "MaxPendingTimeInSeconds": 8000,
                },
                "EnableNetworkIsolation": True,
                "EnableInterContainerTrafficEncryption": True,
                "EnableManagedSpotTraining": True,
                "CheckpointConfig": {"S3Uri": "string", "LocalPath": "string"},
                "RetryStrategy": {"MaximumRetryAttempts": 123},
                "Environment": {"string": "string"},
            },
        ],
        WarmStartConfig={
            "ParentHyperParameterTuningJobs": [
                {"HyperParameterTuningJobName": "string"},
            ],
            "WarmStartType": "IdenticalDataAndAlgorithm",
        },
        Tags=[
            {"Key": "string", "Value": "string"},
        ],
        Autotune={"Mode": "Enabled"},
    )
    resp = client.describe_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="testhyperparametertuningjob"
    )
    assert resp["HyperParameterTuningJobName"] == "testhyperparametertuningjob"
    assert (
        resp["HyperParameterTuningJobArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:hyper-parameter-tuning-job/testhyperparametertuningjob"
    )
    assert resp["HyperParameterTuningJobConfig"] == {
        "Strategy": "Bayesian",
        "ResourceLimits": {
            "MaxNumberOfTrainingJobs": 123,
            "MaxParallelTrainingJobs": 123,
            "MaxRuntimeInSeconds": 123,
        },
        "StrategyConfig": {
            "HyperbandStrategyConfig": {"MinResource": 123, "MaxResource": 123}
        },
        "HyperParameterTuningJobObjective": {
            "Type": "Maximize",
            "MetricName": "string",
        },
        "ParameterRanges": {
            "IntegerParameterRanges": [
                {
                    "Name": "string",
                    "MinValue": "string",
                    "MaxValue": "string",
                    "ScalingType": "Auto",
                },
            ],
        },
        "TrainingJobEarlyStoppingType": "Auto",
        "TuningJobCompletionCriteria": {
            "TargetObjectiveMetricValue": 123,
            "BestObjectiveNotImproving": {"MaxNumberOfTrainingJobsNotImproving": 123},
            "ConvergenceDetected": {"CompleteOnConvergence": "Enabled"},
        },
        "RandomSeed": 123,
    }
    assert resp["TrainingJobDefinition"] == {
        "DefinitionName": "string",
        "TuningObjective": {"Type": "Maximize", "MetricName": "string"},
        "HyperParameterRanges": {
            "IntegerParameterRanges": [
                {
                    "Name": "string",
                    "MinValue": "string",
                    "MaxValue": "string",
                    "ScalingType": "Auto",
                },
            ],
            "ContinuousParameterRanges": [
                {
                    "Name": "string",
                    "MinValue": "string",
                    "MaxValue": "string",
                    "ScalingType": "Auto",
                },
            ],
            "CategoricalParameterRanges": [
                {
                    "Name": "string",
                    "Values": [
                        "string",
                    ],
                },
            ],
            "AutoParameters": [
                {"Name": "string", "ValueHint": "string"},
            ],
        },
        "StaticHyperParameters": {"string": "string"},
        "AlgorithmSpecification": {
            "TrainingImage": "string",
            "TrainingInputMode": "Pipe",
            "AlgorithmName": "string",
            "MetricDefinitions": [
                {"Name": "string", "Regex": "string"},
            ],
        },
        "RoleArn": f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
        "InputDataConfig": [
            {
                "ChannelName": "string",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": "string",
                        "S3DataDistributionType": "FullyReplicated",
                        "AttributeNames": [
                            "string",
                        ],
                        "InstanceGroupNames": [
                            "string",
                        ],
                    },
                    "FileSystemDataSource": {
                        "FileSystemId": "testfilesystemid",
                        "FileSystemAccessMode": "rw",
                        "FileSystemType": "EFS",
                        "DirectoryPath": "string",
                    },
                },
                "ContentType": "string",
                "CompressionType": "Gzip",
                "RecordWrapperType": "RecordIO",
                "InputMode": "Pipe",
                "ShuffleConfig": {"Seed": 123},
            },
        ],
        "VpcConfig": {
            "SecurityGroupIds": [
                "string",
            ],
            "Subnets": [
                "string",
            ],
        },
        "OutputDataConfig": {
            "KmsKeyId": "string",
            "S3OutputPath": "string",
            "CompressionType": "GZIP",
        },
        "ResourceConfig": {
            "InstanceType": "ml.m4.xlarge",
            "InstanceCount": 123,
            "VolumeSizeInGB": 123,
            "VolumeKmsKeyId": "string",
            "KeepAlivePeriodInSeconds": 123,
            "InstanceGroups": [
                {
                    "InstanceType": "ml.m4.xlarge",
                    "InstanceCount": 123,
                    "InstanceGroupName": "string",
                },
            ],
        },
        "HyperParameterTuningResourceConfig": {
            "InstanceType": "ml.m4.xlarge",
            "InstanceCount": 123,
            "VolumeSizeInGB": 123,
            "VolumeKmsKeyId": "string",
            "AllocationStrategy": "Prioritized",
            "InstanceConfigs": [
                {
                    "InstanceType": "ml.m4.xlarge",
                    "InstanceCount": 123,
                    "VolumeSizeInGB": 123,
                },
            ],
        },
        "StoppingCondition": {
            "MaxRuntimeInSeconds": 123,
            "MaxWaitTimeInSeconds": 123,
            "MaxPendingTimeInSeconds": 7200,
        },
        "EnableNetworkIsolation": True,
        "EnableInterContainerTrafficEncryption": True,
        "EnableManagedSpotTraining": True,
        "CheckpointConfig": {"S3Uri": "string", "LocalPath": "string"},
        "RetryStrategy": {"MaximumRetryAttempts": 123},
        "Environment": {"string": "string"},
    }
    assert resp["TrainingJobDefinitions"] == [
        {
            "DefinitionName": "string",
            "TuningObjective": {
                "Type": "Maximize",
                "MetricName": "string",
            },
            "HyperParameterRanges": {
                "IntegerParameterRanges": [
                    {
                        "Name": "string",
                        "MinValue": "string",
                        "MaxValue": "string",
                        "ScalingType": "Auto",
                    },
                ],
                "ContinuousParameterRanges": [
                    {
                        "Name": "string",
                        "MinValue": "string",
                        "MaxValue": "string",
                        "ScalingType": "Auto",
                    },
                ],
                "CategoricalParameterRanges": [
                    {
                        "Name": "string",
                        "Values": [
                            "string",
                        ],
                    },
                ],
                "AutoParameters": [
                    {"Name": "string", "ValueHint": "string"},
                ],
            },
            "StaticHyperParameters": {"string": "string"},
            "AlgorithmSpecification": {
                "TrainingImage": "string",
                "TrainingInputMode": "Pipe",
                "AlgorithmName": "string",
                "MetricDefinitions": [
                    {"Name": "string", "Regex": "string"},
                ],
            },
            "RoleArn": f"arn:aws:iam::{ACCOUNT_ID}:role/FakeRole",
            "InputDataConfig": [
                {
                    "ChannelName": "string",
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "ManifestFile",
                            "S3Uri": "string",
                            "S3DataDistributionType": "FullyReplicated",
                            "AttributeNames": [
                                "string",
                            ],
                            "InstanceGroupNames": [
                                "string",
                            ],
                        },
                        "FileSystemDataSource": {
                            "FileSystemId": "testfilesystemid",
                            "FileSystemAccessMode": "rw",
                            "FileSystemType": "EFS",
                            "DirectoryPath": "string",
                        },
                    },
                    "ContentType": "string",
                    "CompressionType": "Gzip",
                    "RecordWrapperType": "RecordIO",
                    "InputMode": "Pipe",
                    "ShuffleConfig": {"Seed": 123},
                },
            ],
            "VpcConfig": {
                "SecurityGroupIds": [
                    "string",
                ],
                "Subnets": [
                    "string",
                ],
            },
            "OutputDataConfig": {
                "KmsKeyId": "string",
                "S3OutputPath": "string",
                "CompressionType": "GZIP",
            },
            "ResourceConfig": {
                "InstanceType": "ml.m4.xlarge",
                "InstanceCount": 123,
                "VolumeSizeInGB": 123,
                "VolumeKmsKeyId": "string",
                "KeepAlivePeriodInSeconds": 123,
                "InstanceGroups": [
                    {
                        "InstanceType": "ml.m4.xlarge",
                        "InstanceCount": 123,
                        "InstanceGroupName": "string",
                    },
                ],
            },
            "HyperParameterTuningResourceConfig": {
                "InstanceType": "ml.m4.xlarge",
                "InstanceCount": 123,
                "VolumeSizeInGB": 123,
                "VolumeKmsKeyId": "string",
                "AllocationStrategy": "Prioritized",
                "InstanceConfigs": [
                    {
                        "InstanceType": "ml.m4.xlarge",
                        "InstanceCount": 123,
                        "VolumeSizeInGB": 123,
                    },
                ],
            },
            "StoppingCondition": {
                "MaxRuntimeInSeconds": 123,
                "MaxWaitTimeInSeconds": 123,
                "MaxPendingTimeInSeconds": 8000,
            },
            "EnableNetworkIsolation": True,
            "EnableInterContainerTrafficEncryption": True,
            "EnableManagedSpotTraining": True,
            "CheckpointConfig": {"S3Uri": "string", "LocalPath": "string"},
            "RetryStrategy": {"MaximumRetryAttempts": 123},
            "Environment": {"string": "string"},
        },
    ]
    assert resp["HyperParameterTuningJobStatus"] == "Completed"
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert isinstance(resp["HyperParameterTuningEndTime"], datetime.datetime)
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)
    assert resp["TrainingJobStatusCounters"] == {
        "Completed": 1,
        "InProgress": 0,
        "NonRetryableError": 0,
        "RetryableError": 0,
        "Stopped": 0,
    }
    assert resp["ObjectiveStatusCounters"] == {
        "Failed": 0,
        "Pending": 0,
        "Succeeded": 1,
    }
    assert resp["BestTrainingJob"] == {
        "TrainingJobDefinitionName": "string",
        "TrainingJobName": "FakeTrainingJobName",
        "TrainingJobArn": "FakeTrainingJobArn",
        "TuningJobName": "FakeTuningJobName",
        "CreationTime": datetime.datetime(2024, 1, 1),
        "TrainingStartTime": datetime.datetime(2024, 1, 1),
        "TrainingEndTime": datetime.datetime(2024, 1, 1),
        "TrainingJobStatus": "Completed",
        "TunedHyperParameters": {"string": "TunedHyperParameters"},
        "FailureReason": "string",
        "FinalHyperParameterTuningJobObjectiveMetric": {
            "Type": "Maximize",
            "MetricName": "Accuracy",
            "Value": 1,
        },
        "ObjectiveStatus": "Succeeded",
    }
    assert resp["OverallBestTrainingJob"] == {
        "TrainingJobDefinitionName": "FakeTrainingJobDefinitionName",
        "TrainingJobName": "FakeTrainingJobName",
        "TrainingJobArn": "FakeTrainingJobArn",
        "TuningJobName": "FakeTuningJobName",
        "CreationTime": datetime.datetime(2024, 1, 1),
        "TrainingStartTime": datetime.datetime(2024, 1, 1),
        "TrainingEndTime": datetime.datetime(2024, 1, 1),
        "TrainingJobStatus": "Completed",
        "TunedHyperParameters": {"string": "FakeTunedHyperParameters"},
        "FailureReason": "FakeFailureReason",
        "FinalHyperParameterTuningJobObjectiveMetric": {
            "Type": "Maximize",
            "MetricName": "Acccuracy",
            "Value": 1,
        },
        "ObjectiveStatus": "Succeeded",
    }
    assert resp["WarmStartConfig"] == {
        "ParentHyperParameterTuningJobs": [
            {"HyperParameterTuningJobName": "string"},
        ],
        "WarmStartType": "IdenticalDataAndAlgorithm",
    }
    assert resp["Autotune"] == {"Mode": "Enabled"}
    assert resp["FailureReason"] == ""
    assert resp["TuningJobCompletionDetails"] == {
        "NumberOfTrainingJobsObjectiveNotImproving": 123,
        "ConvergenceDetectedTime": datetime.datetime(2024, 1, 1),
    }
    assert resp["ConsumedResources"] == {"RuntimeInSeconds": 123}


@mock_aws
def test_list_hyper_parameter_tuning_jobs():
    client = boto3.client("sagemaker", region_name="us-east-2")
    client.create_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="testhyperparametertuningjob",
        HyperParameterTuningJobConfig={
            "Strategy": "Bayesian",
            "ResourceLimits": {
                "MaxNumberOfTrainingJobs": 123,
                "MaxParallelTrainingJobs": 123,
                "MaxRuntimeInSeconds": 123,
            },
        },
    )
    client.create_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="testhyperparametertuningjob2",
        HyperParameterTuningJobConfig={
            "Strategy": "Bayesian",
            "ResourceLimits": {
                "MaxNumberOfTrainingJobs": 123,
                "MaxParallelTrainingJobs": 123,
                "MaxRuntimeInSeconds": 123,
            },
        },
    )
    resp = client.list_hyper_parameter_tuning_jobs()["HyperParameterTuningJobSummaries"]
    assert resp[0]["HyperParameterTuningJobName"] == "testhyperparametertuningjob"
    assert (
        resp[0]["HyperParameterTuningJobArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:hyper-parameter-tuning-job/testhyperparametertuningjob"
    )
    assert resp[0]["HyperParameterTuningJobStatus"] == "Completed"
    assert resp[0]["Strategy"] == "Bayesian"
    assert isinstance(resp[0]["CreationTime"], datetime.datetime)
    assert isinstance(resp[0]["HyperParameterTuningEndTime"], datetime.datetime)
    assert isinstance(resp[0]["LastModifiedTime"], datetime.datetime)
    assert resp[0]["TrainingJobStatusCounters"] == {
        "Completed": 1,
        "InProgress": 0,
        "NonRetryableError": 0,
        "RetryableError": 0,
        "Stopped": 0,
    }
    assert resp[0]["ObjectiveStatusCounters"] == {
        "Failed": 0,
        "Pending": 0,
        "Succeeded": 1,
    }
    assert resp[0]["ResourceLimits"] == {
        "MaxNumberOfTrainingJobs": 123,
        "MaxParallelTrainingJobs": 123,
        "MaxRuntimeInSeconds": 123,
    }
    assert resp[1]["HyperParameterTuningJobName"] == "testhyperparametertuningjob2"
    assert (
        resp[1]["HyperParameterTuningJobArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:hyper-parameter-tuning-job/testhyperparametertuningjob2"
    )
    assert resp[1]["HyperParameterTuningJobStatus"] == "Completed"
    assert resp[1]["Strategy"] == "Bayesian"
    assert isinstance(resp[1]["CreationTime"], datetime.datetime)
    assert isinstance(resp[1]["HyperParameterTuningEndTime"], datetime.datetime)
    assert isinstance(resp[1]["LastModifiedTime"], datetime.datetime)
    assert resp[1]["TrainingJobStatusCounters"] == {
        "Completed": 1,
        "InProgress": 0,
        "NonRetryableError": 0,
        "RetryableError": 0,
        "Stopped": 0,
    }
    assert resp[1]["ObjectiveStatusCounters"] == {
        "Failed": 0,
        "Pending": 0,
        "Succeeded": 1,
    }
    assert resp[1]["ResourceLimits"] == {
        "MaxNumberOfTrainingJobs": 123,
        "MaxParallelTrainingJobs": 123,
        "MaxRuntimeInSeconds": 123,
    }


@mock_aws
def test_list_hyper_parameter_tuning_jobs_filters():
    client = boto3.client("sagemaker", region_name="us-east-2")
    client.create_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="testhyperparametertuningjob",
        HyperParameterTuningJobConfig={
            "Strategy": "Bayesian",
            "ResourceLimits": {
                "MaxNumberOfTrainingJobs": 123,
                "MaxParallelTrainingJobs": 123,
                "MaxRuntimeInSeconds": 123,
            },
        },
    )
    client.create_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="anothername",
        HyperParameterTuningJobConfig={
            "Strategy": "Bayesian",
            "ResourceLimits": {
                "MaxNumberOfTrainingJobs": 124,
                "MaxParallelTrainingJobs": 122,
                "MaxRuntimeInSeconds": 125,
            },
        },
    )
    client.create_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="testhyperparametertuningjob2",
        HyperParameterTuningJobConfig={
            "Strategy": "Bayesian",
            "ResourceLimits": {
                "MaxNumberOfTrainingJobs": 126,
                "MaxParallelTrainingJobs": 125,
                "MaxRuntimeInSeconds": 128,
            },
        },
    )
    resp = client.list_hyper_parameter_tuning_jobs(
        SortBy="CreationTime",
        SortOrder="Ascending",
        NameContains="testhyperparametertuningjob",
        CreationTimeAfter=datetime.datetime(2024, 1, 1),
        CreationTimeBefore=datetime.datetime(2100, 1, 1),
        LastModifiedTimeAfter=datetime.datetime(2024, 1, 1),
        LastModifiedTimeBefore=datetime.datetime(2100, 1, 1),
        StatusEquals="Completed",
    )["HyperParameterTuningJobSummaries"]
    assert len(resp) == 2
    assert resp[0]["HyperParameterTuningJobName"] == "testhyperparametertuningjob"
    assert (
        resp[0]["HyperParameterTuningJobArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:hyper-parameter-tuning-job/testhyperparametertuningjob"
    )
    assert resp[0]["HyperParameterTuningJobStatus"] == "Completed"
    assert resp[0]["Strategy"] == "Bayesian"
    assert isinstance(resp[0]["CreationTime"], datetime.datetime)
    assert isinstance(resp[0]["HyperParameterTuningEndTime"], datetime.datetime)
    assert isinstance(resp[0]["LastModifiedTime"], datetime.datetime)
    assert resp[0]["TrainingJobStatusCounters"] == {
        "Completed": 1,
        "InProgress": 0,
        "NonRetryableError": 0,
        "RetryableError": 0,
        "Stopped": 0,
    }
    assert resp[0]["ObjectiveStatusCounters"] == {
        "Failed": 0,
        "Pending": 0,
        "Succeeded": 1,
    }
    assert resp[0]["ResourceLimits"] == {
        "MaxNumberOfTrainingJobs": 123,
        "MaxParallelTrainingJobs": 123,
        "MaxRuntimeInSeconds": 123,
    }
    assert resp[1]["HyperParameterTuningJobName"] == "testhyperparametertuningjob2"
    assert (
        resp[1]["HyperParameterTuningJobArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:hyper-parameter-tuning-job/testhyperparametertuningjob2"
    )
    assert resp[1]["HyperParameterTuningJobStatus"] == "Completed"
    assert resp[1]["Strategy"] == "Bayesian"
    assert isinstance(resp[1]["CreationTime"], datetime.datetime)
    assert isinstance(resp[1]["HyperParameterTuningEndTime"], datetime.datetime)
    assert isinstance(resp[1]["LastModifiedTime"], datetime.datetime)
    assert resp[1]["TrainingJobStatusCounters"] == {
        "Completed": 1,
        "InProgress": 0,
        "NonRetryableError": 0,
        "RetryableError": 0,
        "Stopped": 0,
    }
    assert resp[1]["ObjectiveStatusCounters"] == {
        "Failed": 0,
        "Pending": 0,
        "Succeeded": 1,
    }
    assert resp[1]["ResourceLimits"] == {
        "MaxNumberOfTrainingJobs": 126,
        "MaxParallelTrainingJobs": 125,
        "MaxRuntimeInSeconds": 128,
    }


@mock_aws
def test_delete_hyper_parameter_tuning_job():
    client = boto3.client("sagemaker", region_name="us-east-2")
    client.create_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="testhyperparametertuningjob",
        HyperParameterTuningJobConfig={
            "Strategy": "Bayesian",
            "ResourceLimits": {
                "MaxNumberOfTrainingJobs": 123,
                "MaxParallelTrainingJobs": 123,
                "MaxRuntimeInSeconds": 123,
            },
        },
    )
    client.create_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="anothername",
        HyperParameterTuningJobConfig={
            "Strategy": "Bayesian",
            "ResourceLimits": {
                "MaxNumberOfTrainingJobs": 124,
                "MaxParallelTrainingJobs": 122,
                "MaxRuntimeInSeconds": 125,
            },
        },
    )
    client.delete_hyper_parameter_tuning_job(HyperParameterTuningJobName="anothername")
    resp = client.list_hyper_parameter_tuning_jobs()["HyperParameterTuningJobSummaries"]
    assert len(resp) == 1
    assert resp[0]["HyperParameterTuningJobName"] == "testhyperparametertuningjob"
    assert (
        resp[0]["HyperParameterTuningJobArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:hyper-parameter-tuning-job/testhyperparametertuningjob"
    )
    assert resp[0]["HyperParameterTuningJobStatus"] == "Completed"
    assert resp[0]["Strategy"] == "Bayesian"
    assert isinstance(resp[0]["CreationTime"], datetime.datetime)
    assert isinstance(resp[0]["HyperParameterTuningEndTime"], datetime.datetime)
    assert isinstance(resp[0]["LastModifiedTime"], datetime.datetime)
    assert resp[0]["TrainingJobStatusCounters"] == {
        "Completed": 1,
        "InProgress": 0,
        "NonRetryableError": 0,
        "RetryableError": 0,
        "Stopped": 0,
    }
    assert resp[0]["ObjectiveStatusCounters"] == {
        "Failed": 0,
        "Pending": 0,
        "Succeeded": 1,
    }
    assert resp[0]["ResourceLimits"] == {
        "MaxNumberOfTrainingJobs": 123,
        "MaxParallelTrainingJobs": 123,
        "MaxRuntimeInSeconds": 123,
    }


@mock_aws
def test_tag_hyper_parameter_tuning_job():
    client = boto3.client("sagemaker", region_name="us-east-2")
    arn = client.create_hyper_parameter_tuning_job(
        HyperParameterTuningJobName="testhyperparametertuningjob",
        HyperParameterTuningJobConfig={
            "Strategy": "Bayesian",
            "ResourceLimits": {
                "MaxNumberOfTrainingJobs": 123,
                "MaxParallelTrainingJobs": 123,
                "MaxRuntimeInSeconds": 123,
            },
        },
        Tags=[{"Key": "testkey", "Value": "testvalue"}],
    )["HyperParameterTuningJobArn"]

    resp1 = client.list_tags(ResourceArn=arn)["Tags"]
    assert resp1 == [
        {"Key": "testkey", "Value": "testvalue"},
    ]
    client.add_tags(
        ResourceArn=arn,
        Tags=[
            {"Key": "testkey2", "Value": "testvalue2"},
        ],
    )
    resp2 = client.list_tags(ResourceArn=arn)["Tags"]
    assert resp2 == [
        {"Key": "testkey", "Value": "testvalue"},
        {"Key": "testkey2", "Value": "testvalue2"},
    ]
    client.delete_tags(
        ResourceArn=arn,
        TagKeys=[
            "testkey",
        ],
    )
    resp3 = client.list_tags(ResourceArn=arn)["Tags"]
    assert resp3 == [{"Key": "testkey2", "Value": "testvalue2"}]
