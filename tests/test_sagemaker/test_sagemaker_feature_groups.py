"""Unit tests for sagemaker-supported APIs."""

import re
from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_feature_group():
    client = boto3.client("sagemaker", region_name="us-east-2")
    resp = client.create_feature_group(
        FeatureGroupName="some-feature-group-name",
        RecordIdentifierFeatureName="some_record_identifier",
        EventTimeFeatureName="EventTime",
        FeatureDefinitions=[
            {"FeatureName": "some_feature", "FeatureType": "String"},
            {"FeatureName": "EventTime", "FeatureType": "Fractional"},
            {"FeatureName": "some_record_identifier", "FeatureType": "String"},
        ],
        RoleArn="arn:aws:iam::123456789012:role/AWSFeatureStoreAccess",
        OfflineStoreConfig={
            "DisableGlueTableCreation": False,
            "S3StorageConfig": {"S3Uri": "s3://mybucket"},
        },
    )

    assert (
        resp["FeatureGroupArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:feature-group/some-feature-group-name"
    )

    with pytest.raises(ClientError) as raised_exception:
        client.create_feature_group(
            FeatureGroupName="some-feature-group-name",
            RecordIdentifierFeatureName="some_record_identifier",
            EventTimeFeatureName="EventTime",
            FeatureDefinitions=[
                {"FeatureName": "some_feature", "FeatureType": "String"},
                {"FeatureName": "EventTime", "FeatureType": "Fractional"},
                {"FeatureName": "some_record_identifier", "FeatureType": "String"},
            ],
            RoleArn="arn:aws:iam::123456789012:role/AWSFeatureStoreAccess",
            OfflineStoreConfig={
                "DisableGlueTableCreation": False,
                "S3StorageConfig": {"S3Uri": "s3://mybucket"},
            },
        )

    assert raised_exception.value.response["Error"]["Code"] == "ResourceInUse"
    assert (
        raised_exception.value.response["Error"]["Message"]
        == "An error occurred (ResourceInUse) when calling the CreateFeatureGroup operation: Resource Already Exists: FeatureGroup with name some-feature-group-name already exists. Choose a different name.\nInfo: Feature Group 'some-feature-group-name' already exists."
    )


@mock_aws
def test_describe_feature_group():
    client = boto3.client("sagemaker", region_name="us-east-2")
    feature_group_name = "some-feature-group-name"
    record_identifier_feature_name = "some_record_identifier"
    event_time_feature_name = "EventTime"
    role_arn = "arn:aws:iam::123456789012:role/AWSFeatureStoreAccess"
    feature_definitions = [
        {"FeatureName": "some_feature", "FeatureType": "String"},
        {"FeatureName": event_time_feature_name, "FeatureType": "Fractional"},
        {"FeatureName": record_identifier_feature_name, "FeatureType": "String"},
    ]
    client.create_feature_group(
        FeatureGroupName=feature_group_name,
        RecordIdentifierFeatureName=record_identifier_feature_name,
        EventTimeFeatureName=event_time_feature_name,
        FeatureDefinitions=feature_definitions,
        RoleArn=role_arn,
        OfflineStoreConfig={
            "DisableGlueTableCreation": False,
            "S3StorageConfig": {"S3Uri": "s3://mybucket/some-folder/some-subfolder"},
        },
    )
    resp = client.describe_feature_group(FeatureGroupName=feature_group_name)

    assert resp["FeatureGroupName"] == feature_group_name
    assert (
        resp["FeatureGroupArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:feature-group/some-feature-group-name"
    )
    assert resp["RecordIdentifierFeatureName"] == record_identifier_feature_name
    assert resp["EventTimeFeatureName"] == event_time_feature_name
    assert resp["FeatureDefinitions"] == feature_definitions
    assert resp["RoleArn"] == role_arn
    assert re.match(
        f"^{feature_group_name.replace('-', '_')}_[0-9]+$",
        resp["OfflineStoreConfig"]["DataCatalogConfig"]["TableName"],
    )
    assert (
        resp["OfflineStoreConfig"]["DataCatalogConfig"]["Catalog"] == "AwsDataCatalog"
    )
    assert (
        resp["OfflineStoreConfig"]["DataCatalogConfig"]["Database"]
        == "sagemaker_featurestore"
    )
    assert (
        resp["OfflineStoreConfig"]["S3StorageConfig"]["S3Uri"]
        == "s3://mybucket/some-folder/some-subfolder"
    )
    assert re.match(
        f"^s3://mybucket/some-folder/some-subfolder/123456789012/us-east-2/offline-store/{feature_group_name}-[0-9]+/data$",
        resp["OfflineStoreConfig"]["S3StorageConfig"]["ResolvedOutputS3Uri"],
    )
    assert isinstance(resp["CreationTime"], datetime)
    assert resp["FeatureGroupStatus"] == "Created"
