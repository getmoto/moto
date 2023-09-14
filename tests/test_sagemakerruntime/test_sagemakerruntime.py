import boto3
import requests

from moto import mock_sagemakerruntime, settings

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_sagemakerruntime
def test_invoke_endpoint__default_results():
    client = boto3.client("sagemaker-runtime", region_name="ap-southeast-1")
    body = client.invoke_endpoint(
        EndpointName="asdf", Body="qwer", Accept="sth", TargetModel="tm"
    )

    assert body["Body"].read() == b"body"
    assert body["CustomAttributes"] == "custom_attributes"


@mock_sagemakerruntime
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
