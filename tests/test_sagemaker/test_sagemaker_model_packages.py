"""Unit tests for sagemaker-supported APIs."""
from datetime import datetime
from unittest import SkipTest

import boto3
from freezegun import freeze_time
from dateutil.tz import tzutc  # type: ignore

from moto import mock_sagemaker, settings

import pytest

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html
from moto.sagemaker.exceptions import ValidationError
from moto.sagemaker.utils import validate_model_approval_status


@mock_sagemaker
def test_list_model_packages():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageDescription="test-model-package-description-v1",
    )
    client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageDescription="test-model-package-description-v2",
    )
    client.create_model_package(
        ModelPackageName="test-model-package-2",
        ModelPackageDescription="test-model-package-description-v1-2",
    )
    resp = client.list_model_packages()

    assert (
        resp["ModelPackageSummaryList"][0]["ModelPackageName"] == "test-model-package"
    )
    assert "ModelPackageDescription" in resp["ModelPackageSummaryList"][0]
    assert (
        resp["ModelPackageSummaryList"][0]["ModelPackageDescription"]
        == "test-model-package-description-v2"
    )
    assert (
        resp["ModelPackageSummaryList"][1]["ModelPackageName"] == "test-model-package-2"
    )
    assert "ModelPackageDescription" in resp["ModelPackageSummaryList"][1]
    assert (
        resp["ModelPackageSummaryList"][1]["ModelPackageDescription"]
        == "test-model-package-description-v1-2"
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
        ModelPackageName="test-model-package",
        ModelPackageDescription="test-model-package-description-2",
        ModelPackageGroupName="test-model-package-group",
    )
    client.create_model_package(
        ModelPackageName="test-model-package-2",
        ModelPackageDescription="test-model-package-description-3",
        ModelPackageGroupName="test-model-package-group",
    )
    client.create_model_package(
        ModelPackageName="test-model-package-without-group",
        ModelPackageDescription="test-model-package-description-without-group",
    )
    resp = client.list_model_packages(ModelPackageGroupName="test-model-package-group")

    assert len(resp["ModelPackageSummaryList"]) == 3


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
def test_describe_model_package_default():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package_group(ModelPackageGroupName="test-model-package-group")
    with freeze_time("2015-01-01 00:00:00"):
        client.create_model_package(
            ModelPackageName="test-model-package",
            ModelPackageGroupName="test-model-package-group",
            ModelPackageDescription="test-model-package-description",
        )
    resp = client.describe_model_package(ModelPackageName="test-model-package")
    assert resp["ModelPackageName"] == "test-model-package"
    assert resp["ModelPackageGroupName"] == "test-model-package-group"
    assert resp["ModelPackageDescription"] == "test-model-package-description"
    assert (
            resp["ModelPackageArn"]
            == "arn:aws:sagemaker:eu-west-1:123456789012:model-package/test-model-package/1"
    )
    assert resp["CreationTime"] == datetime(2015, 1, 1, 0, 0, 0, tzinfo=tzutc())
    assert (
        resp["CreatedBy"]["UserProfileArn"]
        == "arn:aws:sagemaker:eu-west-1:123456789012:user-profile/fake-domain-id/fake-user-profile-name"
    )
    assert resp["CreatedBy"]["UserProfileName"] == "fake-user-profile-name"
    assert resp["CreatedBy"]["DomainId"] == "fake-domain-id"
    assert resp["ModelPackageStatus"] == "Completed"
    assert resp.get("ModelPackageStatusDetails") is not None
    assert resp["ModelPackageStatusDetails"]["ValidationStatuses"] == [{'Name': 'arn:aws:sagemaker:eu-west-1:123456789012:model-package/test-model-package/1', 'Status': 'Completed'}]
    assert resp["ModelPackageStatusDetails"]["ImageScanStatuses"] == [{'Name': 'arn:aws:sagemaker:eu-west-1:123456789012:model-package/test-model-package/1', 'Status': 'Completed'}]
    assert resp["CertifyForMarketplace"] is False


@mock_sagemaker
def test_describe_model_package_with_create_model_package_arguments():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package_group(ModelPackageGroupName="test-model-package-group")
    client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageGroupName="test-model-package-group",
        ModelPackageDescription="test-model-package-description",
        ModelApprovalStatus="PendingManualApproval",
        MetadataProperties={
            "CommitId": "test-commit-id",
            "GeneratedBy": "test-user",
            "ProjectId": "test-project-id",
            "Repository": "test-repo",
        },
        CertifyForMarketplace=True,
    )
    resp = client.describe_model_package(ModelPackageName="test-model-package")
    assert resp["ModelApprovalStatus"] == "PendingManualApproval"
    assert resp.get("ApprovalDescription") is None
    assert resp["CertifyForMarketplace"] is True
    assert resp["MetadataProperties"] is not None
    assert resp["MetadataProperties"]["CommitId"] == "test-commit-id"
    assert resp["MetadataProperties"]["GeneratedBy"] == "test-user"
    assert resp["MetadataProperties"]["ProjectId"] == "test-project-id"
    assert resp["MetadataProperties"]["Repository"] == "test-repo"


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


@pytest.mark.parametrize(
    "model_approval_status",
    ["Approved", "Rejected", "PendingManualApproval"],
)
def test_utils_validate_model_approval_status_should_not_raise_error_if_model_approval_status_is_correct(
    model_approval_status: str,
):
    validate_model_approval_status(model_approval_status)


def test_utils_validate_model_approval_status_should_raise_error_if_model_approval_status_is_incorrect():
    model_approval_status = "IncorrectStatus"
    with pytest.raises(ValidationError) as exc:
        validate_model_approval_status(model_approval_status)
    assert exc.value.code == 400
    assert (
        exc.value.message
        == "Value 'IncorrectStatus' at 'modelApprovalStatus' failed to satisfy constraint: Member must satisfy enum value set: [PendingManualApproval, Approved, Rejected]"
    )


@mock_sagemaker
def test_create_model_package_in_model_package_group():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package_group(ModelPackageGroupName="test-model-package-group")
    resp_version_1 = client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageGroupName="test-model-package-group",
        ModelPackageDescription="test-model-package-description",
    )
    resp_version_2 = client.create_model_package(
        ModelPackageName="test-model-package",
        ModelPackageGroupName="test-model-package-group",
        ModelPackageDescription="test-model-package-description",
    )
    assert (
        resp_version_1["ModelPackageArn"]
        == "arn:aws:sagemaker:eu-west-1:123456789012:model-package/test-model-package/1"
    )
    assert (
        resp_version_2["ModelPackageArn"]
        == "arn:aws:sagemaker:eu-west-1:123456789012:model-package/test-model-package/2"
    )
