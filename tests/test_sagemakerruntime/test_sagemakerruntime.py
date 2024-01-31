import json

import boto3
import requests

from moto import mock_aws, settings
from moto.s3.utils import bucket_and_name_from_url

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_invoke_endpoint__default_results():
    client = boto3.client("sagemaker-runtime", region_name="ap-southeast-1")
    body = client.invoke_endpoint(
        EndpointName="asdf", Body="qwer", Accept="sth", TargetModel="tm"
    )

    assert body["Body"].read() == b"body"
    assert body["CustomAttributes"] == "custom_attributes"


@mock_aws
def test_invoke_endpoint():
    client = boto3.client("sagemaker-runtime", region_name="us-east-1")
    base_url = (
        "localhost:5000" if settings.TEST_SERVER_MODE else "motoapi.amazonaws.com"
    )

    sagemaker_result = {
        "results": [
            {
                "Body": "first body",
                "ContentType": "text/xml",
                "InvokedProductionVariant": "prod",
                "CustomAttributes": "my_attr",
            },
            {"Body": "second body"},
        ]
    }
    requests.post(
        f"http://{base_url}/moto-api/static/sagemaker/endpoint-results",
        json=sagemaker_result,
    )

    # Return the first item from the list
    body = client.invoke_endpoint(EndpointName="asdf", Body="qwer")
    assert body["Body"].read() == b"first body"

    # Same input -> same output
    body = client.invoke_endpoint(EndpointName="asdf", Body="qwer")
    assert body["Body"].read() == b"first body"

    # Different input -> second item
    body = client.invoke_endpoint(
        EndpointName="asdf", Body="qwer", Accept="sth", TargetModel="tm"
    )
    assert body["Body"].read() == b"second body"


@mock_aws
def test_invoke_endpoint_async():
    client = boto3.client("sagemaker-runtime", region_name="us-east-1")
    base_url = (
        "localhost:5000" if settings.TEST_SERVER_MODE else "motoapi.amazonaws.com"
    )

    sagemaker_result = {
        "results": [
            {
                "Body": "first body",
                "ContentType": "text/xml",
                "InvokedProductionVariant": "prod",
                "CustomAttributes": "my_attr",
            },
            {"Body": "second body"},
        ]
    }
    requests.post(
        f"http://{base_url}/moto-api/static/sagemaker/endpoint-results",
        json=sagemaker_result,
    )

    # Return the first item from the list
    body = client.invoke_endpoint_async(EndpointName="asdf", InputLocation="qwer")
    first_output_location = body["OutputLocation"]

    # Same input -> same output
    body = client.invoke_endpoint_async(EndpointName="asdf", InputLocation="qwer")
    assert body["OutputLocation"] == first_output_location

    # Different input -> second item
    body = client.invoke_endpoint_async(
        EndpointName="asdf", InputLocation="asf", InferenceId="sth"
    )
    second_output_location = body["OutputLocation"]
    assert body["InferenceId"] == "sth"

    s3 = boto3.client("s3", "us-east-1")
    bucket_name, obj = bucket_and_name_from_url(second_output_location)
    resp = s3.get_object(Bucket=bucket_name, Key=obj)
    resp = json.loads(resp["Body"].read().decode("utf-8"))
    assert resp["Body"] == "second body"
