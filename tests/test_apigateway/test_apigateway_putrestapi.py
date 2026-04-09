import os

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_put_rest_api__api_details_are_persisted():
    client = boto3.client("apigateway", region_name="us-west-2")

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api.json", "rb") as api_json:
        response = client.put_rest_api(
            restApiId=api_id,
            mode="overwrite",
            failOnWarnings=True,
            body=api_json.read(),
        )

    assert response["id"] == api_id
    assert response["name"] == "my_api"
    assert response["description"] == "this is my api"


@mock_aws
def test_put_rest_api__methods_are_created():
    client = boto3.client("apigateway", region_name="us-east-2")

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api.json", "rb") as api_json:
        client.put_rest_api(restApiId=api_id, body=api_json.read())

    resources = client.get_resources(restApiId=api_id)
    root_id = [res for res in resources["items"] if res["path"] == "/"][0]["id"]

    # We have a GET-method
    resp = client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")
    assert resp["methodResponses"] == {"200": {"statusCode": "200"}}

    # We have a POST on /test
    test_path_id = [res for res in resources["items"] if res["path"] == "/test"][0][
        "id"
    ]
    resp = client.get_method(
        restApiId=api_id, resourceId=test_path_id, httpMethod="POST"
    )
    assert resp["methodResponses"] == {"201": {"statusCode": "201"}}


@mock_aws
def test_put_rest_api__existing_methods_are_overwritten():
    client = boto3.client("apigateway", region_name="us-east-2")

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="POST",
        authorizationType="none",
    )

    response = client.get_method(
        restApiId=api_id, resourceId=root_id, httpMethod="POST"
    )
    assert response["httpMethod"] == "POST"

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api.json", "rb") as api_json:
        client.put_rest_api(
            restApiId=api_id,
            mode="overwrite",
            failOnWarnings=True,
            body=api_json.read(),
        )

    # Since we chose mode=overwrite, the root_id is different
    resources = client.get_resources(restApiId=api_id)
    new_root_id = [
        resource for resource in resources["items"] if resource["path"] == "/"
    ][0]["id"]

    assert new_root_id != root_id

    # Our POST-method should be gone
    with pytest.raises(ClientError) as exc:
        client.get_method(restApiId=api_id, resourceId=new_root_id, httpMethod="POST")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"

    # We just have a GET-method, as defined in the JSON
    client.get_method(restApiId=api_id, resourceId=new_root_id, httpMethod="GET")


@mock_aws
def test_put_rest_api__existing_methods_still_exist():
    client = boto3.client("apigateway", region_name="us-east-2")

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="POST",
        authorizationType="none",
    )

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api.json", "rb") as api_json:
        client.put_rest_api(
            restApiId=api_id,
            mode="merge",
            failOnWarnings=True,
            body=api_json.read(),
        )

    response = client.get_method(
        restApiId=api_id, resourceId=root_id, httpMethod="POST"
    )
    assert response["httpMethod"] == "POST"


@mock_aws
def test_put_rest_api__fail_on_invalid_spec():
    client = boto3.client("apigateway", region_name="us-east-2")

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api_invalid.json", "rb") as api_json:
        with pytest.raises(ClientError) as exc:
            client.put_rest_api(
                restApiId=api_id, failOnWarnings=True, body=api_json.read()
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "BadRequestException"
        assert (
            err["Message"]
            == "Failed to parse the uploaded OpenAPI document due to: 'paths' is a required property"
        )


@mock_aws
def test_put_rest_api__fail_on_invalid_version():
    client = boto3.client("apigateway", region_name="us-east-2")

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api_invalid_version.json", "rb") as api_json:
        with pytest.raises(ClientError) as exc:
            client.put_rest_api(
                restApiId=api_id, failOnWarnings=True, body=api_json.read()
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "BadRequestException"
        assert err["Message"] == "Only OpenAPI 3.x.x are currently supported"


@mock_aws
def test_put_rest_api__fail_on_invalid_mode():
    client = boto3.client("apigateway", region_name="us-east-2")

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api.json", "rb") as api_json:
        with pytest.raises(ClientError) as exc:
            client.put_rest_api(restApiId=api_id, mode="unknown", body=api_json.read())
        err = exc.value.response["Error"]
        assert err["Code"] == "BadRequestException"
        assert (
            err["Message"]
            == 'Enumeration value of OpenAPI import mode must be "overwrite" or "merge"'
        )


@mock_aws
def test_put_rest_api__as_yaml():
    client = boto3.client("apigateway", region_name="us-west-2")

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api.yaml", "rb") as api_yaml:
        response = client.put_rest_api(
            restApiId=api_id,
            mode="overwrite",
            failOnWarnings=True,
            body=api_yaml.read(),
        )

    assert response["id"] == api_id
    assert response["name"] == "my_api"
    assert response["description"] == "this is my api"


@mock_aws
def test_put_rest_api__as_yaml_with_integrations():
    client = boto3.client("apigateway", region_name="us-west-2")

    response = client.create_rest_api(
        name="my_api_with_integrations", description="this is my api with integrations"
    )
    api_id = response["id"]

    path = os.path.dirname(os.path.abspath(__file__))
    with open(path + "/resources/test_api_integration.yaml", "rb") as api_yaml:
        response = client.put_rest_api(
            restApiId=api_id,
            mode="overwrite",
            failOnWarnings=True,
            body=api_yaml.read(),
        )

    # Basic assertions that the API has been updated
    assert response["id"] == api_id
    assert response["name"] == "my_api_with_integrations"
    assert response["description"] == "this is my api with integrations"

    # Check some of the details of one of the integrations to check we've called all the
    # right functions (the integration side of things is more fully tested in
    # tests/test_apigateway/test_apigateway_integration.py)
    resources = client.get_resources(
        restApiId=api_id,
    )
    root_resource = next(
        (
            item
            for item in resources.get("items", [])
            if item.get("path") == "/" and "GET" in item.get("resourceMethods", {})
        ),
        None,
    )
    assert root_resource, "Expected a root level resource with a GET"
    assert "GET" in root_resource["resourceMethods"]

    root_get_method = root_resource["resourceMethods"]["GET"]
    assert root_get_method["httpMethod"] == "GET"

    root_integration = root_get_method.get("methodIntegration")
    assert root_integration, "Expected root level GET resource to have an integration"
    assert root_integration.get("type") == "HTTP"
    assert root_integration.get("httpMethod") == "GET"
    assert root_integration.get("uri") == "https://nlb.example.com:8080/api/"
    assert root_integration.get("connectionType") == "VPC_LINK"

    assert "integrationResponses" in root_integration
    assert "200" in root_integration["integrationResponses"]
    default_integration_response = root_integration["integrationResponses"]["200"]
    assert default_integration_response["statusCode"] == "200"
    assert not default_integration_response.get("selectionPattern"), (
        "Default integration response does not have a selection pattern"
    )

    # Create a deployment - this should succeed without error as we have integrations
    client.create_deployment(
        restApiId=api_id,
        description="Test deployment",
    )
