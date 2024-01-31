import os
import sys
from unittest import SkipTest, mock
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.utilities.distutils_version import LooseVersion

from .utilities import get_role_name, get_test_zip_file1

PYTHON_VERSION = "python3.11"
_lambda_region = "us-west-2"

boto3_version = sys.modules["botocore"].__version__


@mock_aws
def test_publish_lambda_layers__without_content():
    conn = boto3.client("lambda", _lambda_region)
    layer_name = str(uuid4())[0:6]

    with pytest.raises(ClientError) as exc:
        conn.publish_layer_version(
            LayerName=layer_name,
            Content={},
            CompatibleRuntimes=["python3.6"],
            LicenseInfo="MIT",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValueException"
    assert err["Message"] == "Missing Content"


@mock_aws
@mock.patch.dict(os.environ, {"VALIDATE_LAMBDA_S3": "false"})
def test_publish_layer_with_unknown_s3_file():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only set env var in DecoratorMode")
    conn = boto3.client("lambda", _lambda_region)
    content = conn.publish_layer_version(
        LayerName=str(uuid4())[0:6],
        Content=dict(S3Bucket="my-bucket", S3Key="my-key.zip"),
    )["Content"]
    assert content["CodeSha256"] == ""
    assert content["CodeSize"] == 0


@mock_aws
@freeze_time("2015-01-01 00:00:00")
def test_get_lambda_layers():
    if LooseVersion(boto3_version) < LooseVersion("1.29.0"):
        raise SkipTest("Parameters only available in newer versions")
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    layer_name = str(uuid4())[0:6]

    conn.publish_layer_version(
        LayerName=layer_name,
        Content={"ZipFile": get_test_zip_file1()},
        CompatibleRuntimes=["python3.6"],
        LicenseInfo="MIT",
    )
    conn.publish_layer_version(
        LayerName=layer_name,
        Content={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        CompatibleRuntimes=["python3.6"],
        LicenseInfo="MIT",
    )

    result = conn.list_layer_versions(LayerName=layer_name)

    for version in result["LayerVersions"]:
        version.pop("CreatedDate")
    result["LayerVersions"].sort(key=lambda x: x["Version"])
    expected_arn = f"arn:aws:lambda:{_lambda_region}:{ACCOUNT_ID}:layer:{layer_name}:"
    assert result["LayerVersions"] == [
        {
            "Version": 1,
            "LayerVersionArn": expected_arn + "1",
            "CompatibleRuntimes": ["python3.6"],
            "Description": "",
            "LicenseInfo": "MIT",
            "CompatibleArchitectures": [],
        },
        {
            "Version": 2,
            "LayerVersionArn": expected_arn + "2",
            "CompatibleRuntimes": ["python3.6"],
            "Description": "",
            "LicenseInfo": "MIT",
            "CompatibleArchitectures": [],
        },
    ]

    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Environment={"Variables": {"test_variable": "test_value"}},
        Layers=[(expected_arn + "1")],
    )

    result = conn.get_function_configuration(FunctionName=function_name)
    assert result["Layers"] == [
        {"Arn": (expected_arn + "1"), "CodeSize": len(zip_content)}
    ]
    result = conn.update_function_configuration(
        FunctionName=function_name, Layers=[(expected_arn + "2")]
    )
    assert result["Layers"] == [
        {"Arn": (expected_arn + "2"), "CodeSize": len(zip_content)}
    ]

    # Test get layer versions for non existant layer
    result = conn.list_layer_versions(LayerName=f"{layer_name}2")
    assert result["LayerVersions"] == []

    # Test create function with non existant layer version
    function_name = str(uuid4())[0:6]  # Must be different than above
    with pytest.raises(ClientError) as exc:
        conn.create_function(
            FunctionName=function_name,
            Runtime=PYTHON_VERSION,
            Role=get_role_name(),
            Handler="lambda_function.lambda_handler",
            Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
            Environment={"Variables": {"test_variable": "test_value"}},
            Layers=[(expected_arn + "3")],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_layer_version():
    if LooseVersion(boto3_version) < LooseVersion("1.29.0"):
        raise SkipTest("Parameters only available in newer versions")
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    layer_name = str(uuid4())[0:6]

    resp = conn.publish_layer_version(
        LayerName=layer_name,
        Content={"ZipFile": get_test_zip_file1()},
        CompatibleRuntimes=["python3.6"],
        LicenseInfo="MIT",
        CompatibleArchitectures=["x86_64"],
    )
    layer_version = resp["Version"]

    resp = conn.get_layer_version(LayerName=layer_name, VersionNumber=layer_version)
    assert resp["Description"] == ""
    assert resp["Version"] == 1
    assert resp["CompatibleArchitectures"] == ["x86_64"]
    assert resp["CompatibleRuntimes"] == ["python3.6"]
    assert resp["LicenseInfo"] == "MIT"


@mock_aws
def test_get_layer_version__unknown():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    layer_name = str(uuid4())[0:6]

    # Delete Layer that never existed
    with pytest.raises(ClientError) as exc:
        conn.get_layer_version(LayerName=layer_name, VersionNumber=1)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"

    conn.publish_layer_version(
        LayerName=layer_name,
        Content={"ZipFile": get_test_zip_file1()},
        CompatibleRuntimes=["python3.6"],
        LicenseInfo="MIT",
    )

    # Delete Version that never existed
    with pytest.raises(ClientError) as exc:
        conn.get_layer_version(LayerName=layer_name, VersionNumber=999)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
@pytest.mark.parametrize("use_arn", [True, False])
def test_delete_layer_version(use_arn):
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": _lambda_region},
    )

    zip_content = get_test_zip_file1()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    layer_name = str(uuid4())[0:6]

    resp = conn.publish_layer_version(
        LayerName=layer_name,
        Content={"ZipFile": get_test_zip_file1()},
        CompatibleRuntimes=["python3.6"],
        LicenseInfo="MIT",
    )
    layer_arn = resp["LayerArn"]
    layer_version = resp["Version"]

    if use_arn:
        conn.get_layer_version(LayerName=layer_arn, VersionNumber=layer_version)
        conn.delete_layer_version(LayerName=layer_arn, VersionNumber=layer_version)
    else:
        conn.get_layer_version(LayerName=layer_name, VersionNumber=layer_version)
        conn.delete_layer_version(LayerName=layer_name, VersionNumber=layer_version)

    result = conn.list_layer_versions(LayerName=layer_name)["LayerVersions"]
    assert result == []


@mock_aws
def test_get_layer_with_no_layer_versions():
    def get_layer_by_layer_name_from_list_of_layer_dicts(layer_name, layer_list):
        for layer in layer_list:
            if layer["LayerName"] == layer_name:
                return layer
        return None

    conn = boto3.client("lambda", _lambda_region)
    layer_name = str(uuid4())[0:6]

    # Publish a new Layer and assert Layer exists and only version 1 is there
    conn.publish_layer_version(
        LayerName=layer_name,
        Content={"ZipFile": get_test_zip_file1()},
    )
    assert (
        get_layer_by_layer_name_from_list_of_layer_dicts(
            layer_name, conn.list_layers()["Layers"]
        )["LatestMatchingVersion"]["Version"]
        == 1
    )

    # Add a new version of that Layer then delete that version
    conn.publish_layer_version(
        LayerName=layer_name,
        Content={"ZipFile": get_test_zip_file1()},
    )
    assert (
        get_layer_by_layer_name_from_list_of_layer_dicts(
            layer_name, conn.list_layers()["Layers"]
        )["LatestMatchingVersion"]["Version"]
        == 2
    )

    conn.delete_layer_version(LayerName=layer_name, VersionNumber=2)
    assert (
        get_layer_by_layer_name_from_list_of_layer_dicts(
            layer_name, conn.list_layers()["Layers"]
        )["LatestMatchingVersion"]["Version"]
        == 1
    )

    # Delete the last layer_version and check that the Layer is still in the LayerStorage
    conn.delete_layer_version(LayerName=layer_name, VersionNumber=1)
    assert (
        get_layer_by_layer_name_from_list_of_layer_dicts(
            layer_name, conn.list_layers()["Layers"]
        )
        is None
    )

    # Assert _latest_version didn't decrement
    conn.publish_layer_version(
        LayerName=layer_name,
        Content={"ZipFile": get_test_zip_file1()},
    )
    assert (
        get_layer_by_layer_name_from_list_of_layer_dicts(
            layer_name, conn.list_layers()["Layers"]
        )["LatestMatchingVersion"]["Version"]
        == 3
    )
