"""Unit tests for sagemaker-supported APIs."""
from unittest import SkipTest

import boto3
from freezegun import freeze_time

from moto import mock_sagemaker, settings

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_sagemaker
def test_list_model_packages():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageDescription="test-model-package-description",
    )
    client.create_model_package(
        ModelPackageName="test-model-package-2",
        ModelPackageDescription="test-model-package-description-2",
    )
    resp = client.list_model_packages()

    assert (
        resp["ModelPackageSummaryList"][0]["ModelPackageName"] == "test-model-package"
    )
    assert "ModelPackageDescription" in resp["ModelPackageSummaryList"][0]
    assert (
        resp["ModelPackageSummaryList"][0]["ModelPackageDescription"]
        == "test-model-package-description"
    )
    assert (
        resp["ModelPackageSummaryList"][1]["ModelPackageName"] == "test-model-package-2"
    )
    assert "ModelPackageDescription" in resp["ModelPackageSummaryList"][1]
    assert (
        resp["ModelPackageSummaryList"][1]["ModelPackageDescription"]
        == "test-model-package-description-2"
    )


@mock_sagemaker
def test_list_model_packages_creation_time_before():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("sagemaker", region_name="eu-west-1")
    with freeze_time("2020-01-01 00:00:00"):
        client.create_model_package(
            ModelPackageName="test-model-package",
            ModelPackageDescription="test-model-package-description",
        )
    with freeze_time("2021-01-01 00:00:00"):
        client.create_model_package(
            ModelPackageName="test-model-package-2",
            ModelPackageDescription="test-model-package-description-2",
        )
    resp = client.list_model_packages(CreationTimeBefore="2020-01-01T02:00:00Z")

    assert len(resp["ModelPackageSummaryList"]) == 1


@mock_sagemaker
def test_list_model_packages_creation_time_after():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("sagemaker", region_name="eu-west-1")
    with freeze_time("2020-01-01 00:00:00"):
        client.create_model_package(
            ModelPackageName="test-model-package",
            ModelPackageDescription="test-model-package-description",
        )
    with freeze_time("2021-01-01 00:00:00"):
        client.create_model_package(
            ModelPackageName="test-model-package-2",
            ModelPackageDescription="test-model-package-description-2",
        )
    resp = client.list_model_packages(CreationTimeAfter="2020-01-02T00:00:00Z")

    assert len(resp["ModelPackageSummaryList"]) == 1


@mock_sagemaker
def test_list_model_packages_name_contains():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageDescription="test-model-package-description",
    )
    client.create_model_package(
        ModelPackageName="test-model-package-2",
        ModelPackageDescription="test-model-package-description-2",
    )
    client.create_model_package(
        ModelPackageName="another-model-package",
        ModelPackageDescription="test-model-package-description-3",
    )
    resp = client.list_model_packages(NameContains="test-model-package")

    assert len(resp["ModelPackageSummaryList"]) == 2


@mock_sagemaker
def test_list_model_packages_approval_status():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageDescription="test-model-package-description",
        ModelApprovalStatus="Approved",
    )
    client.create_model_package(
        ModelPackageName="test-model-package-2",
        ModelPackageDescription="test-model-package-description-2",
        ModelApprovalStatus="Rejected",
    )
    resp = client.list_model_packages(ModelApprovalStatus="Approved")

    assert len(resp["ModelPackageSummaryList"]) == 1


@mock_sagemaker
def test_list_model_packages_model_package_group_name():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageDescription="test-model-package-description",
        ModelPackageGroupName="test-model-package-group",
    )
    client.create_model_package(
        ModelPackageName="test-model-package-2",
        ModelPackageDescription="test-model-package-description-2",
        ModelPackageGroupName="test-model-package-group",
    )
    resp = client.list_model_packages(ModelPackageGroupName="test-model-package-group")

    assert len(resp["ModelPackageSummaryList"]) == 2


@mock_sagemaker
def test_list_model_packages_model_package_type():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageDescription="test-model-package-description",
        ModelPackageGroupName="test-model-package-group",
    )
    client.create_model_package(
        ModelPackageName="test-model-package-2",
        ModelPackageDescription="test-model-package-description-2",
    )
    resp = client.list_model_packages(ModelPackageType="Versioned")

    assert len(resp["ModelPackageSummaryList"]) == 1


@mock_sagemaker
def test_list_model_packages_sort_by():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageDescription="test-model-package-description",
    )
    client.create_model_package(
        ModelPackageName="test-model-package-2",
        ModelPackageDescription="test-model-package-description-2",
    )
    resp = client.list_model_packages(SortBy="CreationTime")

    assert (
        resp["ModelPackageSummaryList"][0]["ModelPackageName"] == "test-model-package"
    )
    assert (
        resp["ModelPackageSummaryList"][1]["ModelPackageName"] == "test-model-package-2"
    )


@mock_sagemaker
def test_list_model_packages_sort_order():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageDescription="test-model-package-description",
    )
    client.create_model_package(
        ModelPackageName="test-model-package-2",
        ModelPackageDescription="test-model-package-description-2",
    )
    resp = client.list_model_packages(SortOrder="Descending")

    assert (
        resp["ModelPackageSummaryList"][0]["ModelPackageName"] == "test-model-package-2"
    )
    assert (
        resp["ModelPackageSummaryList"][1]["ModelPackageName"] == "test-model-package"
    )


@mock_sagemaker
def test_describe_model_package():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageDescription="test-model-package-description",
    )
    resp = client.describe_model_package(ModelPackageName="test-model-package")
    assert resp["ModelPackageName"] == "test-model-package"
    assert resp["ModelPackageDescription"] == "test-model-package-description"


@mock_sagemaker
def test_create_model_package():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    resp = client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageDescription="test-model-package-description",
    )
    assert (
        resp["ModelPackageArn"]
        == "arn:aws:sagemaker:eu-west-1:123456789012:model-package/test-model-package"
    )


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
