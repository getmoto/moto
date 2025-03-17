"""Unit tests for kinesisanalyticsv2-supported APIs."""

import boto3
from typing import Any, Dict, List, Tuple

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_application():
    region="us-east-2"
    client = boto3.client("kinesisanalyticsv2", region_name=region)

    resp = client.create_application(
        ApplicationName="test_application",
        ApplicationDescription="test application description",
        RuntimeEnvironment="FLINK-1_20",
        ServiceExecutionRole=f"arn:aws:iam::{ACCOUNT_ID}:role/application_role",
        Tags=[
            {
                "Key": "key1",
                "Value": "value1"
            },
            {
                "Key": "key2",
                "Value": "value2"
            }
        ]
    )

    app = resp.get("ApplicationDetail")
    app_arn = app.get("ApplicationARN")
    # required parameters
    assert app_arn
    assert (
        app.get("ApplicationDescription")
        == "test application description"
    )

    assert app.get("RuntimeEnvironment") == "FLINK-1_20"
    assert (
        app.get("ServiceExecutionRole") ==
        f"arn:aws:iam::{ACCOUNT_ID}:role/application_role"
    )

    tags_resp = client.list_tags_for_resource(ResourceARN=app_arn)
    assert len(tags_resp["Tags"]) == 2

    # import pytest; pytest.set_trace()

    # assert app.get("CloudWatchLoggingOptions") == [
    #     {

    #     }
    # ]





    # raise Exception("NotYetImplemented")

        # ApplicationConfiguration={
        #     'FlinkApplicationConfiguration': {
        #         'CheckpointConfiguration': {
        #             'ConfigurationType': 'DEFAULT',
        #         },
        #         'MonitoringConfiguration': {
        #             'ConfigurationType': 'DEFAULT',
        #         },
        #         'ParallelismConfiguration': {
        #             'ConfigurationType': 'DEFAULT',
        #         }
        #     },
        #     'EnvironmentProperties': {
        #         'PropertyGroups': [
        #             {
        #                 'PropertyGroupId': 'test',
        #                 'PropertyMap': {
        #                     'string': 'string'
        #                 }
        #             },
        #         ]
        #     },
        #     'ApplicationCodeConfiguration': {
        #         'CodeContent': {
        #             'TextContent': 'string',
        #             'ZipFileContent': b'bytes',
        #             'S3ContentLocation': {
        #                 'BucketARN': 'string',
        #                 'FileKey': 'string',
        #                 'ObjectVersion': 'string'
        #             }
        #         },
        #         'CodeContentType': 'PLAINTEXT'|'ZIPFILE'
        #     },
        #     'ApplicationSnapshotConfiguration': {
        #         'SnapshotsEnabled': True|False
        #     },
        #     'ApplicationSystemRollbackConfiguration': {
        #         'RollbackEnabled': True|False
        #     },
        #     'VpcConfigurations': [
        #         {
        #             'SubnetIds': [
        #                 'string',
        #             ],
        #             'SecurityGroupIds': [
        #                 'string',
        #             ]
        #         },
        #     ],
        #     'ZeppelinApplicationConfiguration': {
        #         'MonitoringConfiguration': {
        #             'LogLevel': 'INFO'|'WARN'|'ERROR'|'DEBUG'
        #         },
        #         'CatalogConfiguration': {
        #             'GlueDataCatalogConfiguration': {
        #                 'DatabaseARN': 'string'
        #             }
        #         },
        #         'DeployAsApplicationConfiguration': {
        #             'S3ContentLocation': {
        #                 'BucketARN': 'string',
        #                 'BasePath': 'string'
        #             }
        #         },
        #         'CustomArtifactsConfiguration': [
        #             {
        #                 'ArtifactType': 'UDF'|'DEPENDENCY_JAR',
        #                 'S3ContentLocation': {
        #                     'BucketARN': 'string',
        #                     'FileKey': 'string',
        #                     'ObjectVersion': 'string'
        #                 },
        #                 'MavenReference': {
        #                     'GroupId': 'string',
        #                     'ArtifactId': 'string',
        #                     'Version': 'string'
        #                 }
        #             },
        #         ]
        #     }
        # }


# @mock_aws
# def test_list_tags_for_resource(self, resource_arn: str, tags: List[Dict[str, str]]) -> None:
#     client = boto3.client("kinesisanalyticsv2", region_name="us-east-2")
#     resp = client.list_tags_for_resource()

#     raise Exception("NotYetImplemented")

@mock_aws
def test_tag_resource():
    region="us-east-2"
    client = boto3.client("kinesisanalyticsv2", region_name=region)
    app_resp = client.create_application(
        ApplicationName="test_application",
        RuntimeEnvironment="FLINK-1_20",
        ServiceExecutionRole=f"arn:aws:iam::{ACCOUNT_ID}:role/application_role"
    )
    app = app_resp.get("ApplicationDetail")
    app_arn = app.get("ApplicationARN")
    client.tag_resource(
        ResourceARN=app_arn,
        Tags=[
            {"Key": "key2", "Value": "value2"},
        ]
    )

    tags_resp = client.list_tags_for_resource(ResourceARN=app_arn)
    # import pytest; pytest.set_trace()

    assert tags_resp["Tags"] == [{"Key": "key2", "Value": "value2"}]

