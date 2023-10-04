"""Unit tests for sagemaker-supported APIs."""
from unittest import SkipTest

import boto3
from freezegun import freeze_time

from moto import mock_sagemaker, settings

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_sagemaker
def test_create_model_package_group():
    client = boto3.client("sagemaker", region_name="us-east-2")
    resp = client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group",
        ModelPackageGroupDescription="test-model-package-group-description",
        Tags=[
            {"Key": "test-key", "Value": "test-value"},
        ],
    )
    assert (
        resp["ModelPackageGroupArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:model-package-group/test-model-package-group"
    )


@mock_sagemaker
def test_list_model_package_groups():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-1",
        ModelPackageGroupDescription="test-model-package-group-description-1",
    )
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-2",
        ModelPackageGroupDescription="test-model-package-group-description-2",
    )
    resp = client.list_model_package_groups()

    assert (
        resp["ModelPackageGroupSummaryList"][0]["ModelPackageGroupName"]
        == "test-model-package-group-1"
    )
    assert "ModelPackageGroupDescription" in resp["ModelPackageGroupSummaryList"][0]
    assert (
        resp["ModelPackageGroupSummaryList"][0]["ModelPackageGroupDescription"]
        == "test-model-package-group-description-1"
    )
    assert (
        resp["ModelPackageGroupSummaryList"][1]["ModelPackageGroupName"]
        == "test-model-package-group-2"
    )
    assert "ModelPackageGroupDescription" in resp["ModelPackageGroupSummaryList"][1]
    assert (
        resp["ModelPackageGroupSummaryList"][1]["ModelPackageGroupDescription"]
        == "test-model-package-group-description-2"
    )


@mock_sagemaker
def test_list_model_package_groups_creation_time_before():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("sagemaker", region_name="eu-west-1")
    with freeze_time("2020-01-01 00:00:00"):
        client.create_model_package_group(
            ModelPackageGroupName="test-model-package-group-1",
            ModelPackageGroupDescription="test-model-package-group-description-1",
        )
    with freeze_time("2021-01-01 00:00:00"):
        client.create_model_package_group(
            ModelPackageGroupName="test-model-package-group-2",
            ModelPackageGroupDescription="test-model-package-group-description-2",
        )
    resp = client.list_model_package_groups(CreationTimeBefore="2020-01-01T02:00:00Z")

    assert len(resp["ModelPackageGroupSummaryList"]) == 1


@mock_sagemaker
def test_list_model_package_groups_creation_time_after():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("sagemaker", region_name="eu-west-1")
    with freeze_time("2020-01-01 00:00:00"):
        client.create_model_package_group(
            ModelPackageGroupName="test-model-package-group-1",
            ModelPackageGroupDescription="test-model-package-group-description-1",
        )
    with freeze_time("2021-01-01 00:00:00"):
        client.create_model_package_group(
            ModelPackageGroupName="test-model-package-group-2",
            ModelPackageGroupDescription="test-model-package-group-description-2",
        )
    resp = client.list_model_package_groups(CreationTimeAfter="2020-01-02T00:00:00Z")

    assert len(resp["ModelPackageGroupSummaryList"]) == 1


@mock_sagemaker
def test_list_model_package_groups_name_contains():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-1",
        ModelPackageGroupDescription="test-model-package-group-description-1",
    )
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-2",
        ModelPackageGroupDescription="test-model-package-group-description-2",
    )
    client.create_model_package_group(
        ModelPackageGroupName="another-model-package-group",
        ModelPackageGroupDescription="another-model-package-group-description",
    )
    resp = client.list_model_package_groups(NameContains="test-model-package")

    assert len(resp["ModelPackageGroupSummaryList"]) == 2


@mock_sagemaker
def test_list_model_package_groups_sort_by():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-1",
        ModelPackageGroupDescription="test-model-package-group-description-1",
    )
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-2",
        ModelPackageGroupDescription="test-model-package-group-description-2",
    )
    resp = client.list_model_package_groups(SortBy="CreationTime")

    assert (
        resp["ModelPackageGroupSummaryList"][0]["ModelPackageGroupName"]
        == "test-model-package-group-1"
    )
    assert (
        resp["ModelPackageGroupSummaryList"][1]["ModelPackageGroupName"]
        == "test-model-package-group-2"
    )


@mock_sagemaker
def test_list_model_package_groups_sort_order():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-1",
        ModelPackageGroupDescription="test-model-package-group-description-1",
    )
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-2",
        ModelPackageGroupDescription="test-model-package-group-description-2",
    )
    resp = client.list_model_package_groups(SortOrder="Descending")

    assert (
        resp["ModelPackageGroupSummaryList"][0]["ModelPackageGroupName"]
        == "test-model-package-group-2"
    )
    assert (
        resp["ModelPackageGroupSummaryList"][1]["ModelPackageGroupName"]
        == "test-model-package-group-1"
    )
