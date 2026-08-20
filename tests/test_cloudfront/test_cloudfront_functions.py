import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_function():
    client = boto3.client("cloudfront", region_name="us-east-1")

    response = client.create_function(
        Name="test-function",
        FunctionConfig={
            "Comment": "Test function",
            "Runtime": "cloudfront-js-1.0",
        },
        FunctionCode=b"function handler(event) { return event; }",
        Tags={
            "Items": [
                {"Key": "Environment", "Value": "Test"},
            ]
        }
    )

    function_summary = response["FunctionSummary"]
    assert function_summary["Name"] == "test-function"
    assert function_summary["FunctionConfig"] == {
        "Comment": "Test function",
        "Runtime": "cloudfront-js-1.0",
    }
    assert function_summary["FunctionMetadata"]["FunctionARN"].endswith(
        "function/test-function"
    )
    assert (
        response["Location"]
        == "https://cloudfront.amazonaws.com/2020-05-31/function/test-function"
    )
    arn = response["FunctionSummary"]["FunctionMetadata"]["FunctionARN"]

    assert response["ETag"]
    tags = client.list_tags_for_resource(Resource=arn)["Tags"]["Items"]
    assert tags == [{"Key": "Environment", "Value": "Test"}]


@mock_aws
def test_create_function_already_exists():
    client = boto3.client("cloudfront", region_name="us-east-1")
    config = {
        "Comment": "Test function",
        "Runtime": "cloudfront-js-1.0",
    }

    client.create_function(
        Name="test-function",
        FunctionConfig=config,
        FunctionCode=b"function handler(event) { return event; }",
    )

    with pytest.raises(ClientError) as exc:
        client.create_function(
            Name="test-function",
            FunctionConfig=config,
            FunctionCode=b"function handler(event) { return event; }",
        )

    error = exc.value.response["Error"]
    assert error["Code"] == "FunctionAlreadyExists"
