import boto3
import os
import pytest
import sys

from botocore.exceptions import ClientError
from moto import mock_apigateway, settings
from unittest import SkipTest


@mock_apigateway
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


@mock_apigateway
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


@mock_apigateway
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


@mock_apigateway
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


@mock_apigateway
def test_put_rest_api__fail_on_invalid_spec():
    if sys.version_info < (3, 8) or settings.TEST_SERVER_MODE:
        raise SkipTest("openapi-module throws an error in Py3.7")

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


@mock_apigateway
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


@mock_apigateway
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


@mock_apigateway
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
