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
        },
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


@mock_aws
def test_describe_function():
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

    response = client.describe_function(Name="test-function")
    function_summary = response["FunctionSummary"]
    assert function_summary["Name"] == "test-function"
    assert function_summary["FunctionConfig"] == config
    assert function_summary["FunctionMetadata"]["FunctionARN"].endswith(
        "function/test-function"
    )


@mock_aws
def test_describe_function_not_found():
    client = boto3.client("cloudfront", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.describe_function(Name="non-existent-function")

    error = exc.value.response["Error"]
    assert error["Code"] == "NoSuchFunctionExists"


@mock_aws
def test_get_function():
    client = boto3.client("cloudfront", region_name="us-east-1")
    code = b"function handler(event) { return event; }"

    create_response = client.create_function(
        Name="test-function",
        FunctionConfig={"Comment": "Test function", "Runtime": "cloudfront-js-1.0"},
        FunctionCode=code,
    )

    response = client.get_function(Name="test-function")
    assert response["FunctionCode"].read() == code
    assert response["ETag"] == create_response["ETag"]


@mock_aws
def test_get_function_with_stage():
    client = boto3.client("cloudfront", region_name="us-east-1")
    code = b"function handler(event) { return event; }"

    client.create_function(
        Name="test-function",
        FunctionConfig={"Comment": "Test function", "Runtime": "cloudfront-js-1.0"},
        FunctionCode=code,
    )

    response = client.get_function(Name="test-function", Stage="DEVELOPMENT")
    assert response["FunctionCode"].read() == code


@mock_aws
def test_get_function_not_found():
    client = boto3.client("cloudfront", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_function(Name="non-existent-function")

    error = exc.value.response["Error"]
    assert error["Code"] == "NoSuchFunctionExists"


@mock_aws
def test_list_functions():
    client = boto3.client("cloudfront", region_name="us-east-1")
    config1 = {
        "Comment": "Test function 1",
        "Runtime": "cloudfront-js-1.0",
    }
    config2 = {
        "Comment": "Test function 2",
        "Runtime": "cloudfront-js-1.0",
    }

    client.create_function(
        Name="test-function-1",
        FunctionConfig=config1,
        FunctionCode=b"function handler(event) { return event; }",
    )
    client.create_function(
        Name="test-function-2",
        FunctionConfig=config2,
        FunctionCode=b"function handler(event) { return event; }",
    )

    response = client.list_functions()
    functions = response["FunctionList"]["Items"]
    assert len(functions) == 2
    assert any(f["Name"] == "test-function-1" for f in functions)
    assert any(f["Name"] == "test-function-2" for f in functions)


@mock_aws
def test_delete_function():
    client = boto3.client("cloudfront", region_name="us-east-1")
    config = {
        "Comment": "Test function",
        "Runtime": "cloudfront-js-1.0",
    }

    create_response = client.create_function(
        Name="test-function",
        FunctionConfig=config,
        FunctionCode=b"function handler(event) { return event; }",
    )
    etag = create_response["ETag"]

    client.delete_function(Name="test-function", IfMatch=etag)

    assert client.list_functions()["FunctionList"]["Quantity"] == 0
    with pytest.raises(ClientError) as exc:
        client.describe_function(Name="test-function")

    error = exc.value.response["Error"]
    assert error["Code"] == "NoSuchFunctionExists"


@mock_aws
def test_delete_function_not_found():
    client = boto3.client("cloudfront", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.delete_function(Name="non-existent-function", IfMatch="etag")

    error = exc.value.response["Error"]
    assert error["Code"] == "NoSuchFunctionExists"


@mock_aws
def test_delete_function_without_if_match():
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
        client.delete_function(Name="test-function", IfMatch="")

    error = exc.value.response["Error"]
    assert error["Code"] == "InvalidIfMatchVersion"


@mock_aws
def test_list_functions_paginate():
    seen_tokens = set()
    client = boto3.client("cloudfront", region_name="us-east-1")
    expected_names = {f"test-function-{index}" for index in range(101)}
    for name in expected_names:
        client.create_function(
            Name=name,
            FunctionConfig={"Comment": name, "Runtime": "cloudfront-js-1.0"},
            FunctionCode=b"function handler(event) { return event; }",
        )
    response = client.list_functions()["FunctionList"]
    pages = [response["Items"]]
    assert len(pages[0]) == 100
    while response.get("NextMarker"):
        next_marker = response["NextMarker"]
        assert next_marker not in seen_tokens
        seen_tokens.add(next_marker)
        response = client.list_functions(Marker=next_marker)["FunctionList"]
        pages.append(response["Items"])
    names = [function["Name"] for page in pages for function in page]
    assert [len(page) for page in pages] == [100, 1]
    assert len(names) == 101
    assert set(names) == expected_names
