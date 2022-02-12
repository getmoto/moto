import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from freezegun import freeze_time
from moto import mock_lambda, mock_s3
from moto.core.exceptions import RESTError
from moto.sts.models import ACCOUNT_ID
from uuid import uuid4

from .utilities import get_role_name, get_test_zip_file1

_lambda_region = "us-west-2"
boto3.setup_default_session(region_name=_lambda_region)


@mock_lambda
@mock_s3
@freeze_time("2015-01-01 00:00:00")
def test_get_lambda_layers():
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

    with pytest.raises((RESTError, ClientError)):
        conn.publish_layer_version(
            LayerName=layer_name,
            Content={},
            CompatibleRuntimes=["python3.6"],
            LicenseInfo="MIT",
        )
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
    expected_arn = "arn:aws:lambda:{0}:{1}:layer:{2}:".format(
        _lambda_region, ACCOUNT_ID, layer_name
    )
    result["LayerVersions"].should.equal(
        [
            {
                "Version": 1,
                "LayerVersionArn": expected_arn + "1",
                "CompatibleRuntimes": ["python3.6"],
                "Description": "",
                "LicenseInfo": "MIT",
            },
            {
                "Version": 2,
                "LayerVersionArn": expected_arn + "2",
                "CompatibleRuntimes": ["python3.6"],
                "Description": "",
                "LicenseInfo": "MIT",
            },
        ]
    )

    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
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
    result["Layers"].should.equal(
        [{"Arn": (expected_arn + "1"), "CodeSize": len(zip_content)}]
    )
    result = conn.update_function_configuration(
        FunctionName=function_name, Layers=[(expected_arn + "2")]
    )
    result["Layers"].should.equal(
        [{"Arn": (expected_arn + "2"), "CodeSize": len(zip_content)}]
    )

    # Test get layer versions for non existant layer
    result = conn.list_layer_versions(LayerName=f"{layer_name}2")
    result["LayerVersions"].should.equal([])

    # Test create function with non existant layer version
    with pytest.raises((ValueError, ClientError)):
        conn.create_function(
            FunctionName=function_name,
            Runtime="python2.7",
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
