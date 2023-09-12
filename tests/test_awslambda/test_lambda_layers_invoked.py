import boto3
import pkgutil

from moto import mock_lambda
from uuid import uuid4

from .utilities import get_role_name, _process_lambda

PYTHON_VERSION = "python3.11"
_lambda_region = "us-west-2"
boto3.setup_default_session(region_name=_lambda_region)


def get_requests_zip_file():
    pfunc = """
import requests
def lambda_handler(event, context):
    return requests.__version__
"""
    return _process_lambda(pfunc)


@mock_lambda
def test_invoke_local_lambda_layers():
    conn = boto3.client("lambda", _lambda_region)
    lambda_name = str(uuid4())[0:6]
    # https://api.klayers.cloud/api/v2/p3.11/layers/latest/us-east-1/json
    requests_location = (
        "resources/Klayers-p311-requests-a637a171-679b-4057-8a62-0a274b260710.zip"
    )
    requests_layer = pkgutil.get_data(__name__, requests_location)

    layer_arn = conn.publish_layer_version(
        LayerName=str(uuid4())[0:6],
        Content={"ZipFile": requests_layer},
        CompatibleRuntimes=["python3.11"],
        LicenseInfo="MIT",
    )["LayerArn"]

    bogus_layer_arn = conn.publish_layer_version(
        LayerName=str(uuid4())[0:6],
        Content={"ZipFile": b"zipfile"},
        CompatibleRuntimes=["python3.11"],
        LicenseInfo="MIT",
    )["LayerArn"]

    function_arn = conn.create_function(
        FunctionName=lambda_name,
        Runtime="python3.11",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_requests_zip_file()},
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Layers=[f"{layer_arn}:1", f"{bogus_layer_arn}:1"],
    )["FunctionArn"]

    success_result = conn.invoke(
        FunctionName=function_arn, Payload="{}", LogType="Tail"
    )
    msg = success_result["Payload"].read().decode("utf-8")
    assert msg == '"2.31.0"'
