"""Unit tests for kinesisanalyticsv2-supported APIs."""

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

FAKE_SECURITY_GROUP_IDS = ["sg-0123456789abcdef0"]
FAKE_SUBNET_IDS = ["subnet-0123456789abcdef0", "subnet-abcdef0123456789"]
FAKE_TAGS = [
    {"Key": "TestKey", "Value": "TestValue"},
    {"Key": "TestKey2", "Value": "TestValue2"},
]
FAKE_VPC_ID = "vpc-0123456789abcdef0"
FAKE_BUCKET_ARN = "arn:aws:s3:::test"
FAKE_FILE_KEY = "testfile.jar"


@mock_aws
def test_create_application():
    region = "us-east-2"
    client = boto3.client("kinesisanalyticsv2", region_name=region)
    log_stream = f"arn:aws:logs:{region}:{ACCOUNT_ID}:log-group:/aws/kinesis-analytics/log-stream:test-log-stream"

    resp = client.create_application(
        ApplicationName="test_application",
        ApplicationDescription="test application description",
        RuntimeEnvironment="FLINK-1_20",
        ServiceExecutionRole=f"arn:aws:iam::{ACCOUNT_ID}:role/application_role",
        Tags=FAKE_TAGS,
        CloudWatchLoggingOptions=[{"LogStreamARN": log_stream}],
    )

    app = resp.get("ApplicationDetail")
    app_arn = app.get("ApplicationARN")
    # required parameters
    assert app_arn
    assert app.get("ApplicationDescription") == "test application description"

    assert app.get("RuntimeEnvironment") == "FLINK-1_20"
    assert (
        app.get("ServiceExecutionRole")
        == f"arn:aws:iam::{ACCOUNT_ID}:role/application_role"
    )

    tags_resp = client.list_tags_for_resource(ResourceARN=app_arn)
    assert len(tags_resp.get("Tags")) == 2
    assert tags_resp.get("Tags") == FAKE_TAGS
    assert len(app.get("CloudWatchLoggingOptionDescriptions")[0]) == 2


@mock_aws
def test_create_application_with_appconfig():
    region = "us-east-2"
    client = boto3.client("kinesisanalyticsv2", region_name=region)

    resp = client.create_application(
        ApplicationName="test_application",
        RuntimeEnvironment="FLINK-1_20",
        ServiceExecutionRole=f"arn:aws:iam::{ACCOUNT_ID}:role/application_role",
        ApplicationConfiguration={
            "FlinkApplicationConfiguration": {
                "CheckpointConfiguration": {"ConfigurationType": "DEFAULT"},
                "MonitoringConfiguration": {"ConfigurationType": "DEFAULT"},
                "ParallelismConfiguration": {"ConfigurationType": "DEFAULT"},
            },
            "EnvironmentProperties": {
                "PropertyGroups": [
                    {
                        "PropertyGroupId": "TEST",
                        "PropertyMap": {
                            "aws.region": "us-east-2",
                            "AggregationEnabled": "false",
                        },
                    },
                    {
                        "PropertyGroupId": "TEST2",
                        "PropertyMap": {
                            "aws.region": "us-west-2",
                        },
                    },
                ]
            },
            "ApplicationCodeConfiguration": {
                "CodeContent": {
                    "S3ContentLocation": {
                        "BucketARN": FAKE_BUCKET_ARN,
                        "FileKey": FAKE_FILE_KEY,
                        "ObjectVersion": "1",
                    }
                },
                "CodeContentType": "ZIPFILE",
            },
            "ApplicationSnapshotConfiguration": {"SnapshotsEnabled": False},
            "ApplicationSystemRollbackConfiguration": {"RollbackEnabled": False},
            "VpcConfigurations": [
                {"SubnetIds": FAKE_SUBNET_IDS, "SecurityGroupIds": FAKE_SUBNET_IDS}
            ],
            "ZeppelinApplicationConfiguration": {
                "MonitoringConfiguration": {"LogLevel": "INFO"},
                "CatalogConfiguration": {
                    "GlueDataCatalogConfiguration": {
                        "DatabaseARN": f"arn:aws:glue:{region}:{ACCOUNT_ID}:database/test"
                    }
                },
                "DeployAsApplicationConfiguration": {
                    "S3ContentLocation": {
                        "BucketARN": FAKE_BUCKET_ARN,
                        "BasePath": "test/app",
                    }
                },
                "CustomArtifactsConfiguration": [
                    {
                        "ArtifactType": "DEPENDENCY_JAR",
                        "S3ContentLocation": {
                            "BucketARN": FAKE_BUCKET_ARN,
                            "FileKey": FAKE_FILE_KEY,
                            "ObjectVersion": "1.0",
                        },
                        "MavenReference": {
                            "GroupId": "org.apache.flink",
                            "ArtifactId": "flink-connector-kafka_2.12",
                            "Version": "1.13.2",
                        },
                    },
                ],
            },
        },
    )
    app = resp.get("ApplicationDetail")
    app_config = app.get("ApplicationConfigurationDescription")

    assert app_config["FlinkApplicationConfigurationDescription"] == {
        "CheckpointConfigurationDescription": {
            "ConfigurationType": "DEFAULT",
            "CheckpointingEnabled": True,
            "CheckpointInterval": 60000,
            "MinPauseBetweenCheckpoints": 5000,
        },
        "MonitoringConfigurationDescription": {
            "ConfigurationType": "DEFAULT",
            "MetricsLevel": "APPLICATION",
            "LogLevel": "INFO",
        },
        "ParallelismConfigurationDescription": {
            "ConfigurationType": "DEFAULT",
            "Parallelism": 1,
            "ParallelismPerKPU": 1,
            "AutoScalingEnabled": False,
            "CurrentParallelism": 1,
        },
    }

    assert app_config["EnvironmentPropertyDescriptions"] == {
        "PropertyGroupDescriptions": [
            {
                "PropertyGroupId": "TEST",
                "PropertyMap": {
                    "aws.region": "us-east-2",
                    "AggregationEnabled": "false",
                },
            },
            {
                "PropertyGroupId": "TEST2",
                "PropertyMap": {
                    "aws.region": "us-west-2",
                },
            },
        ]
    }

    assert app_config == {
        "FlinkApplicationConfigurationDescription": {
            "CheckpointConfigurationDescription": {
                "ConfigurationType": "DEFAULT",
                "CheckpointingEnabled": True,
                "CheckpointInterval": 60000,
                "MinPauseBetweenCheckpoints": 5000,
            },
            "MonitoringConfigurationDescription": {
                "ConfigurationType": "DEFAULT",
                "MetricsLevel": "APPLICATION",
                "LogLevel": "INFO",
            },
            "ParallelismConfigurationDescription": {
                "ConfigurationType": "DEFAULT",
                "Parallelism": 1,
                "ParallelismPerKPU": 1,
                "AutoScalingEnabled": False,
                "CurrentParallelism": 1,
            },
        },
        "EnvironmentPropertyDescriptions": {
            "PropertyGroupDescriptions": [
                {
                    "PropertyGroupId": "TEST",
                    "PropertyMap": {
                        "aws.region": "us-east-2",
                        "AggregationEnabled": "false",
                    },
                },
                {
                    "PropertyGroupId": "TEST2",
                    "PropertyMap": {
                        "aws.region": "us-west-2",
                    },
                },
            ]
        },
        "ApplicationCodeConfigurationDescription": {
            "CodeContentDescription": {
                "CodeMD5": "fakechecksum",
                "CodeSize": 123,
                "S3ApplicationCodeLocationDescription": {
                    "BucketARN": FAKE_BUCKET_ARN,
                    "FileKey": FAKE_FILE_KEY,
                    "ObjectVersion": "1",
                },
            },
            "CodeContentType": "ZIPFILE",
        },
        "ApplicationSnapshotConfigurationDescription": {"SnapshotsEnabled": False},
        "ApplicationSystemRollbackConfigurationDescription": {"RollbackEnabled": False},
        "VpcConfigurationDescriptions": [
            {
                "VpcConfigurationId": "1.1",
                "VpcId": FAKE_VPC_ID,
                "SubnetIds": FAKE_SUBNET_IDS,
                "SecurityGroupIds": FAKE_SUBNET_IDS,
            }
        ],
        "ZeppelinApplicationConfigurationDescription": {
            "MonitoringConfigurationDescription": {"LogLevel": "INFO"},
            "CatalogConfigurationDescription": {
                "GlueDataCatalogConfigurationDescription": {
                    "DatabaseARN": f"arn:aws:glue:{region}:{ACCOUNT_ID}:database/test"
                }
            },
            "DeployAsApplicationConfigurationDescription": {
                "S3ContentLocationDescription": {
                    "BucketARN": FAKE_BUCKET_ARN,
                    "BasePath": "test/app",
                }
            },
            "CustomArtifactsConfigurationDescription": [
                {
                    "ArtifactType": "DEPENDENCY_JAR",
                    "S3ContentLocationDescription": {
                        "BucketARN": FAKE_BUCKET_ARN,
                        "FileKey": FAKE_FILE_KEY,
                        "ObjectVersion": "1.0",
                    },
                    "MavenReferenceDescription": {
                        "GroupId": "org.apache.flink",
                        "ArtifactId": "flink-connector-kafka_2.12",
                        "Version": "1.13.2",
                    },
                },
            ],
        },
    }
    # import pytest; pytest.set_trace()
    # Test CUSTOM flink app configurations
    resp = client.create_application(
        ApplicationName="test_application",
        RuntimeEnvironment="FLINK-1_20",
        ServiceExecutionRole=f"arn:aws:iam::{ACCOUNT_ID}:role/application_role",
        ApplicationConfiguration={
            "FlinkApplicationConfiguration": {
                "CheckpointConfiguration": {"ConfigurationType": "DEFAULT"},
                "MonitoringConfiguration": {"ConfigurationType": "DEFAULT"},
                "ParallelismConfiguration": {"ConfigurationType": "DEFAULT"},
            }
        }

@mock_aws
def test_tag_resource():
    region = "us-east-2"
    client = boto3.client("kinesisanalyticsv2", region_name=region)
    app_resp = client.create_application(
        ApplicationName="test_application",
        RuntimeEnvironment="FLINK-1_20",
        ServiceExecutionRole=f"arn:aws:iam::{ACCOUNT_ID}:role/application_role",
    )
    app = app_resp.get("ApplicationDetail")
    app_arn = app.get("ApplicationARN")
    client.tag_resource(
        ResourceARN=app_arn,
        Tags=[
            {"Key": "key2", "Value": "value2"},
        ],
    )

    tags_resp = client.list_tags_for_resource(ResourceARN=app_arn)
    assert tags_resp["Tags"] == [{"Key": "key2", "Value": "value2"}]
