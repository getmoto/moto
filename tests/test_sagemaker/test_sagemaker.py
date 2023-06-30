"""Unit tests for sagemaker-supported APIs."""
import boto3

from moto import mock_sagemaker

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
