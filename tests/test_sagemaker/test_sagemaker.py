"""Unit tests for sagemaker-supported APIs."""
import boto3

from moto import mock_sagemaker

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_sagemaker
def test_create_model_package_group():
    client = boto3.client("sagemaker", region_name="ap-southeast-1")
    resp = client.create_model_package_group()

    raise Exception("NotYetImplemented")


@mock_sagemaker
def test_describe_model_package_group():
    client = boto3.client("sagemaker", region_name="ap-southeast-1")
    resp = client.describe_model_package_group()

    raise Exception("NotYetImplemented")


@mock_sagemaker
def test_list_model_packages():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    resp = client.list_model_packages()

    raise Exception("NotYetImplemented")


@mock_sagemaker
def test_list_model_package_groups():
    client = boto3.client("sagemaker", region_name="ap-southeast-1")
    resp = client.list_model_package_groups()

    raise Exception("NotYetImplemented")


@mock_sagemaker
def test_describe_model_package():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    resp = client.describe_model_package()

    raise Exception("NotYetImplemented")
