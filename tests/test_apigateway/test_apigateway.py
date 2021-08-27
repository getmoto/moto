from __future__ import unicode_literals

import json

import boto3
from freezegun import freeze_time
import requests
import sure  # noqa
from botocore.exceptions import ClientError

from moto import mock_apigateway, mock_cognitoidp, settings
from moto.apigateway.exceptions import NoIntegrationDefined
from moto.core import ACCOUNT_ID
from moto.core.models import responses_mock
import pytest


@freeze_time("2015-01-01")
@mock_apigateway
def test_create_and_get_rest_api():
    client = boto3.client("apigateway", region_name="us-west-2")

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)

    response.pop("ResponseMetadata")
    response.pop("createdDate")
    response.should.equal(
        {
            "id": api_id,
            "name": "my_api",
            "description": "this is my api",
            "version": "V1",
            "binaryMediaTypes": [],
            "apiKeySource": "HEADER",
            "endpointConfiguration": {"types": ["EDGE"]},
            "tags": {},
            "disableExecuteApiEndpoint": False,
        }
    )


@mock_apigateway
def test_upate_rest_api():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    patchOperations = [
        {"op": "replace", "path": "/name", "value": "new-name"},
        {"op": "replace", "path": "/description", "value": "new-description"},
        {"op": "replace", "path": "/apiKeySource", "value": "AUTHORIZER"},
        {"op": "replace", "path": "/binaryMediaTypes", "value": "image/jpeg"},
        {"op": "replace", "path": "/disableExecuteApiEndpoint", "value": "True"},
    ]

    response = client.update_rest_api(restApiId=api_id, patchOperations=patchOperations)
    response.pop("ResponseMetadata")
    response.pop("createdDate")
    response.pop("binaryMediaTypes")
    response.should.equal(
        {
            "id": api_id,
            "name": "new-name",
            "version": "V1",
            "description": "new-description",
            "apiKeySource": "AUTHORIZER",
            "endpointConfiguration": {"types": ["EDGE"]},
            "tags": {},
            "disableExecuteApiEndpoint": True,
        }
    )
    # should fail with wrong apikeysoruce
    patchOperations = [
        {"op": "replace", "path": "/apiKeySource", "value": "Wrong-value-AUTHORIZER"}
    ]
    with pytest.raises(ClientError) as ex:
        response = client.update_rest_api(
            restApiId=api_id, patchOperations=patchOperations
        )

    ex.value.response["Error"]["Message"].should.equal(
        "1 validation error detected: Value 'Wrong-value-AUTHORIZER' at 'createRestApiInput.apiKeySource' failed to satisfy constraint: Member must satisfy enum value set: [AUTHORIZER, HEADER]"
    )
    ex.value.response["Error"]["Code"].should.equal("ValidationException")


@mock_apigateway
def test_upate_rest_api_invalid_api_id():
    client = boto3.client("apigateway", region_name="us-west-2")
    patchOperations = [
        {"op": "replace", "path": "/apiKeySource", "value": "AUTHORIZER"}
    ]
    with pytest.raises(ClientError) as ex:
        client.update_rest_api(restApiId="api_id", patchOperations=patchOperations)
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")


@mock_apigateway
def test_list_and_delete_apis():
    client = boto3.client("apigateway", region_name="us-west-2")

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    client.create_rest_api(name="my_api2", description="this is my api2")

    response = client.get_rest_apis()
    len(response["items"]).should.equal(2)

    client.delete_rest_api(restApiId=api_id)

    response = client.get_rest_apis()
    len(response["items"]).should.equal(1)


@mock_apigateway
def test_create_rest_api_with_tags():
    client = boto3.client("apigateway", region_name="us-west-2")

    response = client.create_rest_api(
        name="my_api", description="this is my api", tags={"MY_TAG1": "MY_VALUE1"}
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)

    assert "tags" in response
    response["tags"].should.equal({"MY_TAG1": "MY_VALUE1"})


@mock_apigateway
def test_create_rest_api_with_policy():
    client = boto3.client("apigateway", region_name="us-west-2")

    policy = '{"Version": "2012-10-17","Statement": []}'
    response = client.create_rest_api(
        name="my_api", description="this is my api", policy=policy
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)

    assert "policy" in response
    response["policy"].should.equal(policy)


@mock_apigateway
def test_create_rest_api_invalid_apikeysource():
    client = boto3.client("apigateway", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        client.create_rest_api(
            name="my_api",
            description="this is my api",
            apiKeySource="not a valid api key source",
        )
    ex.value.response["Error"]["Code"].should.equal("ValidationException")


@mock_apigateway
def test_create_rest_api_valid_apikeysources():
    client = boto3.client("apigateway", region_name="us-west-2")

    # 1. test creating rest api with HEADER apiKeySource
    response = client.create_rest_api(
        name="my_api", description="this is my api", apiKeySource="HEADER",
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)
    response["apiKeySource"].should.equal("HEADER")

    # 2. test creating rest api with AUTHORIZER apiKeySource
    response = client.create_rest_api(
        name="my_api2", description="this is my api", apiKeySource="AUTHORIZER",
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)
    response["apiKeySource"].should.equal("AUTHORIZER")


@mock_apigateway
def test_create_rest_api_invalid_endpointconfiguration():
    client = boto3.client("apigateway", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        client.create_rest_api(
            name="my_api",
            description="this is my api",
            endpointConfiguration={"types": ["INVALID"]},
        )
    ex.value.response["Error"]["Code"].should.equal("ValidationException")


@mock_apigateway
def test_create_rest_api_valid_endpointconfigurations():
    client = boto3.client("apigateway", region_name="us-west-2")

    # 1. test creating rest api with PRIVATE endpointConfiguration
    response = client.create_rest_api(
        name="my_api",
        description="this is my api",
        endpointConfiguration={"types": ["PRIVATE"]},
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)
    response["endpointConfiguration"].should.equal(
        {"types": ["PRIVATE"],}
    )

    # 2. test creating rest api with REGIONAL endpointConfiguration
    response = client.create_rest_api(
        name="my_api2",
        description="this is my api",
        endpointConfiguration={"types": ["REGIONAL"]},
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)
    response["endpointConfiguration"].should.equal(
        {"types": ["REGIONAL"],}
    )

    # 3. test creating rest api with EDGE endpointConfiguration
    response = client.create_rest_api(
        name="my_api3",
        description="this is my api",
        endpointConfiguration={"types": ["EDGE"]},
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)
    response["endpointConfiguration"].should.equal(
        {"types": ["EDGE"],}
    )


@mock_apigateway
def test_create_resource__validate_name():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    invalid_names = ["/users", "users/", "users/{user_id}", "us{er", "us+er"]
    valid_names = ["users", "{user_id}", "{proxy+}", "user_09", "good-dog"]
    # All invalid names should throw an exception
    for name in invalid_names:
        with pytest.raises(ClientError) as ex:
            client.create_resource(restApiId=api_id, parentId=root_id, pathPart=name)
        ex.value.response["Error"]["Code"].should.equal("BadRequestException")
        ex.value.response["Error"]["Message"].should.equal(
            "Resource's path part only allow a-zA-Z0-9._- and curly braces at the beginning and the end and an optional plus sign before the closing brace."
        )
    # All valid names  should go through
    for name in valid_names:
        client.create_resource(restApiId=api_id, parentId=root_id, pathPart=name)


@mock_apigateway
def test_create_resource():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    root_resource = client.get_resource(restApiId=api_id, resourceId=root_id)
    # this is hard to match against, so remove it
    root_resource["ResponseMetadata"].pop("HTTPHeaders", None)
    root_resource["ResponseMetadata"].pop("RetryAttempts", None)
    root_resource.should.equal(
        {"path": "/", "id": root_id, "ResponseMetadata": {"HTTPStatusCode": 200},}
    )

    client.create_resource(restApiId=api_id, parentId=root_id, pathPart="users")

    resources = client.get_resources(restApiId=api_id)["items"]
    len(resources).should.equal(2)
    non_root_resource = [resource for resource in resources if resource["path"] != "/"][
        0
    ]

    client.delete_resource(restApiId=api_id, resourceId=non_root_resource["id"])

    len(client.get_resources(restApiId=api_id)["items"]).should.equal(1)


@mock_apigateway
def test_child_resource():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    response = client.create_resource(
        restApiId=api_id, parentId=root_id, pathPart="users"
    )
    users_id = response["id"]

    response = client.create_resource(
        restApiId=api_id, parentId=users_id, pathPart="tags"
    )
    tags_id = response["id"]

    child_resource = client.get_resource(restApiId=api_id, resourceId=tags_id)
    # this is hard to match against, so remove it
    child_resource["ResponseMetadata"].pop("HTTPHeaders", None)
    child_resource["ResponseMetadata"].pop("RetryAttempts", None)
    child_resource.should.equal(
        {
            "path": "/users/tags",
            "pathPart": "tags",
            "parentId": users_id,
            "id": tags_id,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
    )


@mock_apigateway
def test_create_method():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", authorizationType="none"
    )

    response = client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "httpMethod": "GET",
            "authorizationType": "none",
            "apiKeyRequired": False,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
    )


@mock_apigateway
def test_create_method_apikeyrequired():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="GET",
        authorizationType="none",
        apiKeyRequired=True,
    )

    response = client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "httpMethod": "GET",
            "authorizationType": "none",
            "apiKeyRequired": True,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
    )


@mock_apigateway
def test_create_method_response():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", authorizationType="none"
    )

    response = client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")

    response = client.put_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {"ResponseMetadata": {"HTTPStatusCode": 200}, "statusCode": "200"}
    )

    response = client.get_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {"ResponseMetadata": {"HTTPStatusCode": 200}, "statusCode": "200"}
    )

    response = client.delete_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal({"ResponseMetadata": {"HTTPStatusCode": 200}})


@mock_apigateway
def test_integrations():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", authorizationType="none"
    )

    client.put_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )

    response = client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="GET",
        type="HTTP",
        uri="http://httpbin.org/robots.txt",
        integrationHttpMethod="POST",
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "httpMethod": "POST",
            "type": "HTTP",
            "uri": "http://httpbin.org/robots.txt",
        }
    )

    response = client.get_integration(
        restApiId=api_id, resourceId=root_id, httpMethod="GET"
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "httpMethod": "POST",
            "type": "HTTP",
            "uri": "http://httpbin.org/robots.txt",
        }
    )

    response = client.get_resource(restApiId=api_id, resourceId=root_id)
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response["resourceMethods"]["GET"]["httpMethod"].should.equal("GET")
    response["resourceMethods"]["GET"]["authorizationType"].should.equal("none")
    response["resourceMethods"]["GET"]["methodIntegration"].should.equal(
        {"httpMethod": "POST", "type": "HTTP", "uri": "http://httpbin.org/robots.txt",}
    )

    client.delete_integration(restApiId=api_id, resourceId=root_id, httpMethod="GET")

    response = client.get_resource(restApiId=api_id, resourceId=root_id)
    response["resourceMethods"]["GET"].shouldnt.contain("methodIntegration")

    # Create a new integration with a requestTemplates config

    client.put_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="POST",
        authorizationType="none",
    )

    templates = {
        # example based on
        # http://docs.aws.amazon.com/apigateway/latest/developerguide/api-as-kinesis-proxy-export-swagger-with-extensions.html
        "application/json": '{\n    "StreamName": "$input.params(\'stream-name\')",\n    "Records": []\n}'
    }
    test_uri = "http://example.com/foobar.txt"
    response = client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="POST",
        type="HTTP",
        uri=test_uri,
        requestTemplates=templates,
        integrationHttpMethod="POST",
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response["ResponseMetadata"].should.equal({"HTTPStatusCode": 200})

    response = client.get_integration(
        restApiId=api_id, resourceId=root_id, httpMethod="POST"
    )
    response["uri"].should.equal(test_uri)
    response["requestTemplates"].should.equal(templates)


@mock_apigateway
def test_integration_response():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", authorizationType="none"
    )

    client.put_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )

    client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="GET",
        type="HTTP",
        uri="http://httpbin.org/robots.txt",
        integrationHttpMethod="POST",
    )

    response = client.put_integration_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="GET",
        statusCode="200",
        selectionPattern="foobar",
        responseTemplates={},
    )

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "statusCode": "200",
            "selectionPattern": "foobar",
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "responseTemplates": {},  # Note: TF compatibility
        }
    )

    response = client.get_integration_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "statusCode": "200",
            "selectionPattern": "foobar",
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "responseTemplates": {},  # Note: TF compatibility
        }
    )

    response = client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response["methodIntegration"]["integrationResponses"].should.equal(
        {
            "200": {
                "responseTemplates": {},  # Note: TF compatibility
                "selectionPattern": "foobar",
                "statusCode": "200",
            }
        }
    )

    response = client.delete_integration_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )

    response = client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")
    response["methodIntegration"]["integrationResponses"].should.equal({})

    # adding a new method and perfomring put intergration with contentHandling as CONVERT_TO_BINARY
    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="PUT", authorizationType="none"
    )

    client.put_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="PUT", statusCode="200"
    )

    client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="PUT",
        type="HTTP",
        uri="http://httpbin.org/robots.txt",
        integrationHttpMethod="POST",
    )

    response = client.put_integration_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="PUT",
        statusCode="200",
        selectionPattern="foobar",
        responseTemplates={},
        contentHandling="CONVERT_TO_BINARY",
    )

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "statusCode": "200",
            "selectionPattern": "foobar",
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "responseTemplates": {},  # Note: TF compatibility
            "contentHandling": "CONVERT_TO_BINARY",
        }
    )

    response = client.get_integration_response(
        restApiId=api_id, resourceId=root_id, httpMethod="PUT", statusCode="200"
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "statusCode": "200",
            "selectionPattern": "foobar",
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "responseTemplates": {},  # Note: TF compatibility
            "contentHandling": "CONVERT_TO_BINARY",
        }
    )


@mock_apigateway
@mock_cognitoidp
def test_update_authorizer_configuration():
    client = boto3.client("apigateway", region_name="us-west-2")
    authorizer_name = "my_authorizer"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    cognito_client = boto3.client("cognito-idp", region_name="us-west-2")
    user_pool_arn = cognito_client.create_user_pool(PoolName="my_cognito_pool")[
        "UserPool"
    ]["Arn"]

    response = client.create_authorizer(
        restApiId=api_id,
        name=authorizer_name,
        type="COGNITO_USER_POOLS",
        providerARNs=[user_pool_arn],
        identitySource="method.request.header.Authorization",
    )
    authorizer_id = response["id"]

    response = client.get_authorizer(restApiId=api_id, authorizerId=authorizer_id)
    # createdDate is hard to match against, remove it
    response.pop("createdDate", None)
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "id": authorizer_id,
            "name": authorizer_name,
            "type": "COGNITO_USER_POOLS",
            "providerARNs": [user_pool_arn],
            "identitySource": "method.request.header.Authorization",
            "authorizerResultTtlInSeconds": 300,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
    )

    client.update_authorizer(
        restApiId=api_id,
        authorizerId=authorizer_id,
        patchOperations=[{"op": "replace", "path": "/type", "value": "TOKEN"}],
    )

    authorizer = client.get_authorizer(restApiId=api_id, authorizerId=authorizer_id)

    authorizer.should.have.key("type").which.should.equal("TOKEN")

    client.update_authorizer(
        restApiId=api_id,
        authorizerId=authorizer_id,
        patchOperations=[{"op": "replace", "path": "/type", "value": "REQUEST"}],
    )

    authorizer = client.get_authorizer(restApiId=api_id, authorizerId=authorizer_id)

    authorizer.should.have.key("type").which.should.equal("REQUEST")

    # TODO: implement mult-update tests

    try:
        client.update_authorizer(
            restApiId=api_id,
            authorizerId=authorizer_id,
            patchOperations=[
                {"op": "add", "path": "/notasetting", "value": "eu-west-1"}
            ],
        )
        assert False.should.be.ok  # Fail, should not be here
    except Exception:
        assert True.should.be.ok


@mock_apigateway
def test_non_existent_authorizer():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    client.get_authorizer.when.called_with(
        restApiId=api_id, authorizerId="xxx"
    ).should.throw(ClientError)


@mock_apigateway
@mock_cognitoidp
def test_create_authorizer():
    client = boto3.client("apigateway", region_name="us-west-2")
    authorizer_name = "my_authorizer"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    cognito_client = boto3.client("cognito-idp", region_name="us-west-2")
    user_pool_arn = cognito_client.create_user_pool(PoolName="my_cognito_pool")[
        "UserPool"
    ]["Arn"]

    response = client.create_authorizer(
        restApiId=api_id,
        name=authorizer_name,
        type="COGNITO_USER_POOLS",
        providerARNs=[user_pool_arn],
        identitySource="method.request.header.Authorization",
    )
    authorizer_id = response["id"]

    response = client.get_authorizer(restApiId=api_id, authorizerId=authorizer_id)
    # createdDate is hard to match against, remove it
    response.pop("createdDate", None)
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "id": authorizer_id,
            "name": authorizer_name,
            "type": "COGNITO_USER_POOLS",
            "providerARNs": [user_pool_arn],
            "identitySource": "method.request.header.Authorization",
            "authorizerResultTtlInSeconds": 300,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
    )

    authorizer_name2 = "my_authorizer2"
    response = client.create_authorizer(
        restApiId=api_id,
        name=authorizer_name2,
        type="COGNITO_USER_POOLS",
        providerARNs=[user_pool_arn],
        identitySource="method.request.header.Authorization",
    )
    authorizer_id2 = response["id"]

    response = client.get_authorizers(restApiId=api_id)

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)

    response["items"][0]["id"].should.match(
        r"{0}|{1}".format(authorizer_id2, authorizer_id)
    )
    response["items"][1]["id"].should.match(
        r"{0}|{1}".format(authorizer_id2, authorizer_id)
    )

    new_authorizer_name_with_vars = "authorizer_with_vars"
    response = client.create_authorizer(
        restApiId=api_id,
        name=new_authorizer_name_with_vars,
        type="COGNITO_USER_POOLS",
        providerARNs=[user_pool_arn],
        identitySource="method.request.header.Authorization",
    )
    authorizer_id3 = response["id"]

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)

    response.should.equal(
        {
            "name": new_authorizer_name_with_vars,
            "id": authorizer_id3,
            "type": "COGNITO_USER_POOLS",
            "providerARNs": [user_pool_arn],
            "identitySource": "method.request.header.Authorization",
            "authorizerResultTtlInSeconds": 300,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
    )

    stage = client.get_authorizer(restApiId=api_id, authorizerId=authorizer_id3)
    stage["name"].should.equal(new_authorizer_name_with_vars)
    stage["id"].should.equal(authorizer_id3)
    stage["type"].should.equal("COGNITO_USER_POOLS")
    stage["providerARNs"].should.equal([user_pool_arn])
    stage["identitySource"].should.equal("method.request.header.Authorization")
    stage["authorizerResultTtlInSeconds"].should.equal(300)


@mock_apigateway
@mock_cognitoidp
def test_delete_authorizer():
    client = boto3.client("apigateway", region_name="us-west-2")
    authorizer_name = "my_authorizer"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    cognito_client = boto3.client("cognito-idp", region_name="us-west-2")
    user_pool_arn = cognito_client.create_user_pool(PoolName="my_cognito_pool")[
        "UserPool"
    ]["Arn"]

    response = client.create_authorizer(
        restApiId=api_id,
        name=authorizer_name,
        type="COGNITO_USER_POOLS",
        providerARNs=[user_pool_arn],
        identitySource="method.request.header.Authorization",
    )
    authorizer_id = response["id"]

    response = client.get_authorizer(restApiId=api_id, authorizerId=authorizer_id)
    # createdDate is hard to match against, remove it
    response.pop("createdDate", None)
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "id": authorizer_id,
            "name": authorizer_name,
            "type": "COGNITO_USER_POOLS",
            "providerARNs": [user_pool_arn],
            "identitySource": "method.request.header.Authorization",
            "authorizerResultTtlInSeconds": 300,
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
    )

    authorizer_name2 = "my_authorizer2"
    response = client.create_authorizer(
        restApiId=api_id,
        name=authorizer_name2,
        type="COGNITO_USER_POOLS",
        providerARNs=[user_pool_arn],
        identitySource="method.request.header.Authorization",
    )
    authorizer_id2 = response["id"]

    authorizers = client.get_authorizers(restApiId=api_id)["items"]
    sorted([authorizer["name"] for authorizer in authorizers]).should.equal(
        sorted([authorizer_name2, authorizer_name])
    )
    # delete stage
    response = client.delete_authorizer(restApiId=api_id, authorizerId=authorizer_id2)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(202)
    # verify other stage still exists
    authorizers = client.get_authorizers(restApiId=api_id)["items"]
    sorted([authorizer["name"] for authorizer in authorizers]).should.equal(
        sorted([authorizer_name])
    )


@mock_apigateway
def test_update_stage_configuration():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)

    response = client.create_deployment(
        restApiId=api_id, stageName=stage_name, description="1.0.1"
    )
    deployment_id = response["id"]

    response = client.get_deployment(restApiId=api_id, deploymentId=deployment_id)
    # createdDate is hard to match against, remove it
    response.pop("createdDate", None)
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "id": deployment_id,
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "description": "1.0.1",
        }
    )

    response = client.create_deployment(
        restApiId=api_id, stageName=stage_name, description="1.0.2"
    )
    deployment_id2 = response["id"]

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)
    stage["stageName"].should.equal(stage_name)
    stage["deploymentId"].should.equal(deployment_id2)
    stage.shouldnt.have.key("cacheClusterSize")

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {"op": "replace", "path": "/cacheClusterEnabled", "value": "True"}
        ],
    )

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)

    stage.should.have.key("cacheClusterSize").which.should.equal("0.5")

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {"op": "replace", "path": "/cacheClusterSize", "value": "1.6"}
        ],
    )

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)

    stage.should.have.key("cacheClusterSize").which.should.equal("1.6")

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {"op": "replace", "path": "/deploymentId", "value": deployment_id},
            {"op": "replace", "path": "/variables/environment", "value": "dev"},
            {"op": "replace", "path": "/variables/region", "value": "eu-west-1"},
            {"op": "replace", "path": "/*/*/caching/dataEncrypted", "value": "True"},
            {"op": "replace", "path": "/cacheClusterEnabled", "value": "True"},
            {
                "op": "replace",
                "path": "/description",
                "value": "stage description update",
            },
            {"op": "replace", "path": "/cacheClusterSize", "value": "1.6"},
        ],
    )

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {"op": "remove", "path": "/variables/region", "value": "eu-west-1"}
        ],
    )

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)

    stage["description"].should.match("stage description update")
    stage["cacheClusterSize"].should.equal("1.6")
    stage["variables"]["environment"].should.match("dev")
    stage["variables"].should_not.have.key("region")
    stage["cacheClusterEnabled"].should.be.true
    stage["deploymentId"].should.match(deployment_id)
    stage["methodSettings"].should.have.key("*/*")
    stage["methodSettings"]["*/*"].should.have.key(
        "cacheDataEncrypted"
    ).which.should.be.true

    try:
        client.update_stage(
            restApiId=api_id,
            stageName=stage_name,
            patchOperations=[
                {"op": "add", "path": "/notasetting", "value": "eu-west-1"}
            ],
        )
        assert False.should.be.ok  # Fail, should not be here
    except Exception:
        assert True.should.be.ok


@mock_apigateway
def test_non_existent_stage():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    client.get_stage.when.called_with(restApiId=api_id, stageName="xxx").should.throw(
        ClientError
    )


@mock_apigateway
def test_create_stage():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    create_method_integration(client, api_id)
    response = client.create_deployment(restApiId=api_id, stageName=stage_name)
    deployment_id = response["id"]

    response = client.get_deployment(restApiId=api_id, deploymentId=deployment_id)
    # createdDate is hard to match against, remove it
    response.pop("createdDate", None)
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "id": deployment_id,
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "description": "",
        }
    )

    response = client.create_deployment(restApiId=api_id, stageName=stage_name)

    deployment_id2 = response["id"]

    response = client.get_deployments(restApiId=api_id)

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)

    response["items"][0].pop("createdDate")
    response["items"][1].pop("createdDate")
    response["items"][0]["id"].should.match(
        r"{0}|{1}".format(deployment_id2, deployment_id)
    )
    response["items"][1]["id"].should.match(
        r"{0}|{1}".format(deployment_id2, deployment_id)
    )

    new_stage_name = "current"
    response = client.create_stage(
        restApiId=api_id, stageName=new_stage_name, deploymentId=deployment_id2
    )

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)

    response.should.equal(
        {
            "stageName": new_stage_name,
            "deploymentId": deployment_id2,
            "methodSettings": {},
            "variables": {},
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "description": "",
            "cacheClusterEnabled": False,
        }
    )

    stage = client.get_stage(restApiId=api_id, stageName=new_stage_name)
    stage["stageName"].should.equal(new_stage_name)
    stage["deploymentId"].should.equal(deployment_id2)

    new_stage_name_with_vars = "stage_with_vars"
    response = client.create_stage(
        restApiId=api_id,
        stageName=new_stage_name_with_vars,
        deploymentId=deployment_id2,
        variables={"env": "dev"},
    )

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)

    response.should.equal(
        {
            "stageName": new_stage_name_with_vars,
            "deploymentId": deployment_id2,
            "methodSettings": {},
            "variables": {"env": "dev"},
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "description": "",
            "cacheClusterEnabled": False,
        }
    )

    stage = client.get_stage(restApiId=api_id, stageName=new_stage_name_with_vars)
    stage["stageName"].should.equal(new_stage_name_with_vars)
    stage["deploymentId"].should.equal(deployment_id2)
    stage["variables"].should.have.key("env").which.should.match("dev")

    new_stage_name = "stage_with_vars_and_cache_settings"
    response = client.create_stage(
        restApiId=api_id,
        stageName=new_stage_name,
        deploymentId=deployment_id2,
        variables={"env": "dev"},
        cacheClusterEnabled=True,
        description="hello moto",
    )

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)

    response.should.equal(
        {
            "stageName": new_stage_name,
            "deploymentId": deployment_id2,
            "methodSettings": {},
            "variables": {"env": "dev"},
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "description": "hello moto",
            "cacheClusterEnabled": True,
            "cacheClusterSize": "0.5",
        }
    )

    stage = client.get_stage(restApiId=api_id, stageName=new_stage_name)

    stage["cacheClusterSize"].should.equal("0.5")

    new_stage_name = "stage_with_vars_and_cache_settings_and_size"
    response = client.create_stage(
        restApiId=api_id,
        stageName=new_stage_name,
        deploymentId=deployment_id2,
        variables={"env": "dev"},
        cacheClusterEnabled=True,
        cacheClusterSize="1.6",
        description="hello moto",
    )

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)

    response.should.equal(
        {
            "stageName": new_stage_name,
            "deploymentId": deployment_id2,
            "methodSettings": {},
            "variables": {"env": "dev"},
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "description": "hello moto",
            "cacheClusterEnabled": True,
            "cacheClusterSize": "1.6",
        }
    )

    stage = client.get_stage(restApiId=api_id, stageName=new_stage_name)
    stage["stageName"].should.equal(new_stage_name)
    stage["deploymentId"].should.equal(deployment_id2)
    stage["variables"].should.have.key("env").which.should.match("dev")
    stage["cacheClusterSize"].should.equal("1.6")


@mock_apigateway
def test_create_deployment_requires_REST_methods():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    with pytest.raises(ClientError) as ex:
        client.create_deployment(restApiId=api_id, stageName=stage_name)["id"]
    ex.value.response["Error"]["Code"].should.equal("BadRequestException")
    ex.value.response["Error"]["Message"].should.equal(
        "The REST API doesn't contain any methods"
    )


@mock_apigateway
def test_create_deployment_requires_REST_method_integrations():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", authorizationType="NONE"
    )

    with pytest.raises(ClientError) as ex:
        client.create_deployment(restApiId=api_id, stageName=stage_name)["id"]
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")
    ex.value.response["Error"]["Message"].should.equal(
        "No integration defined for method"
    )


@mock_apigateway
def test_create_simple_deployment_with_get_method():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)
    deployment = client.create_deployment(restApiId=api_id, stageName=stage_name)
    assert "id" in deployment


@mock_apigateway
def test_create_simple_deployment_with_post_method():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id, httpMethod="POST")
    deployment = client.create_deployment(restApiId=api_id, stageName=stage_name)
    assert "id" in deployment


@mock_apigateway
# https://github.com/aws/aws-sdk-js/issues/2588
def test_put_integration_response_requires_responseTemplate():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", authorizationType="NONE"
    )
    client.put_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )
    client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="GET",
        type="HTTP",
        uri="http://httpbin.org/robots.txt",
        integrationHttpMethod="POST",
    )

    with pytest.raises(ClientError) as ex:
        client.put_integration_response(
            restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
        )
    ex.value.response["Error"]["Code"].should.equal("BadRequestException")
    ex.value.response["Error"]["Message"].should.equal("Invalid request input")

    # Works fine if responseTemplate is defined
    client.put_integration_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="GET",
        statusCode="200",
        responseTemplates={},
    )


@mock_apigateway
def test_put_integration_response_with_response_template():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", authorizationType="NONE"
    )
    client.put_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )
    client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="GET",
        type="HTTP",
        uri="http://httpbin.org/robots.txt",
        integrationHttpMethod="POST",
    )

    with pytest.raises(ClientError) as ex:
        client.put_integration_response(
            restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
        )

    ex.value.response["Error"]["Code"].should.equal("BadRequestException")
    ex.value.response["Error"]["Message"].should.equal("Invalid request input")

    client.put_integration_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="GET",
        statusCode="200",
        selectionPattern="foobar",
        responseTemplates={"application/json": json.dumps({"data": "test"})},
    )

    response = client.get_integration_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "statusCode": "200",
            "selectionPattern": "foobar",
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "responseTemplates": {"application/json": json.dumps({"data": "test"})},
        }
    )


@mock_apigateway
def test_put_integration_validation():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", authorizationType="NONE"
    )
    client.put_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )

    http_types = ["HTTP", "HTTP_PROXY"]
    aws_types = ["AWS", "AWS_PROXY"]
    types_requiring_integration_method = http_types + aws_types
    types_not_requiring_integration_method = ["MOCK"]

    for type in types_requiring_integration_method:
        # Ensure that integrations of these types fail if no integrationHttpMethod is provided
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                httpMethod="GET",
                type=type,
                uri="http://httpbin.org/robots.txt",
            )
        ex.value.response["Error"]["Code"].should.equal("BadRequestException")
        ex.value.response["Error"]["Message"].should.equal(
            "Enumeration value for HttpMethod must be non-empty"
        )
    for type in types_not_requiring_integration_method:
        # Ensure that integrations of these types do not need the integrationHttpMethod
        client.put_integration(
            restApiId=api_id,
            resourceId=root_id,
            httpMethod="GET",
            type=type,
            uri="http://httpbin.org/robots.txt",
        )
    for type in http_types:
        # Ensure that it works fine when providing the integrationHttpMethod-argument
        client.put_integration(
            restApiId=api_id,
            resourceId=root_id,
            httpMethod="GET",
            type=type,
            uri="http://httpbin.org/robots.txt",
            integrationHttpMethod="POST",
        )
    for type in ["AWS"]:
        # Ensure that it works fine when providing the integrationHttpMethod + credentials
        client.put_integration(
            restApiId=api_id,
            resourceId=root_id,
            credentials="arn:aws:iam::{}:role/service-role/testfunction-role-oe783psq".format(
                ACCOUNT_ID
            ),
            httpMethod="GET",
            type=type,
            uri="arn:aws:apigateway:us-west-2:s3:path/b/k",
            integrationHttpMethod="POST",
        )
    for type in aws_types:
        # Ensure that credentials are not required when URI points to a Lambda stream
        client.put_integration(
            restApiId=api_id,
            resourceId=root_id,
            httpMethod="GET",
            type=type,
            uri="arn:aws:apigateway:eu-west-1:lambda:path/2015-03-31/functions/arn:aws:lambda:eu-west-1:012345678901:function:MyLambda/invocations",
            integrationHttpMethod="POST",
        )
    for type in ["AWS_PROXY"]:
        # Ensure that aws_proxy does not support S3
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                credentials="arn:aws:iam::{}:role/service-role/testfunction-role-oe783psq".format(
                    ACCOUNT_ID
                ),
                httpMethod="GET",
                type=type,
                uri="arn:aws:apigateway:us-west-2:s3:path/b/k",
                integrationHttpMethod="POST",
            )
        ex.value.response["Error"]["Code"].should.equal("BadRequestException")
        ex.value.response["Error"]["Message"].should.equal(
            "Integrations of type 'AWS_PROXY' currently only supports Lambda function and Firehose stream invocations."
        )
    for type in aws_types:
        # Ensure that the Role ARN is for the current account
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                credentials="arn:aws:iam::000000000000:role/service-role/testrole",
                httpMethod="GET",
                type=type,
                uri="arn:aws:apigateway:us-west-2:s3:path/b/k",
                integrationHttpMethod="POST",
            )
        ex.value.response["Error"]["Code"].should.equal("AccessDeniedException")
        ex.value.response["Error"]["Message"].should.equal(
            "Cross-account pass role is not allowed."
        )
    for type in ["AWS"]:
        # Ensure that the Role ARN is specified for aws integrations
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                httpMethod="GET",
                type=type,
                uri="arn:aws:apigateway:us-west-2:s3:path/b/k",
                integrationHttpMethod="POST",
            )
        ex.value.response["Error"]["Code"].should.equal("BadRequestException")
        ex.value.response["Error"]["Message"].should.equal(
            "Role ARN must be specified for AWS integrations"
        )
    for type in http_types:
        # Ensure that the URI is valid HTTP
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                httpMethod="GET",
                type=type,
                uri="non-valid-http",
                integrationHttpMethod="POST",
            )
        ex.value.response["Error"]["Code"].should.equal("BadRequestException")
        ex.value.response["Error"]["Message"].should.equal(
            "Invalid HTTP endpoint specified for URI"
        )
    for type in aws_types:
        # Ensure that the URI is an ARN
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                httpMethod="GET",
                type=type,
                uri="non-valid-arn",
                integrationHttpMethod="POST",
            )
        ex.value.response["Error"]["Code"].should.equal("BadRequestException")
        ex.value.response["Error"]["Message"].should.equal(
            "Invalid ARN specified in the request"
        )
    for type in aws_types:
        # Ensure that the URI is a valid ARN
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                httpMethod="GET",
                type=type,
                uri="arn:aws:iam::0000000000:role/service-role/asdf",
                integrationHttpMethod="POST",
            )
        ex.value.response["Error"]["Code"].should.equal("BadRequestException")
        ex.value.response["Error"]["Message"].should.equal(
            "AWS ARN for integration must contain path or action"
        )


@mock_apigateway
def test_delete_stage():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)
    deployment_id1 = client.create_deployment(restApiId=api_id, stageName=stage_name)[
        "id"
    ]
    deployment_id2 = client.create_deployment(restApiId=api_id, stageName=stage_name)[
        "id"
    ]

    new_stage_name = "current"
    client.create_stage(
        restApiId=api_id, stageName=new_stage_name, deploymentId=deployment_id1
    )

    new_stage_name_with_vars = "stage_with_vars"
    client.create_stage(
        restApiId=api_id,
        stageName=new_stage_name_with_vars,
        deploymentId=deployment_id2,
        variables={"env": "dev"},
    )
    stages = client.get_stages(restApiId=api_id)["item"]
    sorted([stage["stageName"] for stage in stages]).should.equal(
        sorted([new_stage_name, new_stage_name_with_vars, stage_name])
    )
    # delete stage
    response = client.delete_stage(restApiId=api_id, stageName=new_stage_name_with_vars)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(202)
    # verify other stage still exists
    stages = client.get_stages(restApiId=api_id)["item"]
    sorted([stage["stageName"] for stage in stages]).should.equal(
        sorted([new_stage_name, stage_name])
    )


@mock_apigateway
def test_deployment():
    client = boto3.client("apigateway", region_name="us-west-2")
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    create_method_integration(client, api_id)

    response = client.create_deployment(restApiId=api_id, stageName=stage_name)
    deployment_id = response["id"]

    response = client.get_deployment(restApiId=api_id, deploymentId=deployment_id)
    # createdDate is hard to match against, remove it
    response.pop("createdDate", None)
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    response.should.equal(
        {
            "id": deployment_id,
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "description": "",
        }
    )

    response = client.get_deployments(restApiId=api_id)

    response["items"][0].pop("createdDate")
    response["items"].should.equal([{"id": deployment_id, "description": ""}])

    client.delete_deployment(restApiId=api_id, deploymentId=deployment_id)

    response = client.get_deployments(restApiId=api_id)
    len(response["items"]).should.equal(0)

    # test deployment stages

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)
    stage["stageName"].should.equal(stage_name)
    stage["deploymentId"].should.equal(deployment_id)

    client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {"op": "replace", "path": "/description", "value": "_new_description_"}
        ],
    )

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)
    stage["stageName"].should.equal(stage_name)
    stage["deploymentId"].should.equal(deployment_id)
    stage["description"].should.equal("_new_description_")


@mock_apigateway
def test_create_domain_names():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    test_certificate_private_key = "testPrivateKey"
    # success case with valid params
    response = client.create_domain_name(
        domainName=domain_name,
        certificateName=test_certificate_name,
        certificatePrivateKey=test_certificate_private_key,
    )
    response["domainName"].should.equal(domain_name)
    response["certificateName"].should.equal(test_certificate_name)
    # without domain name it should throw BadRequestException
    with pytest.raises(ClientError) as ex:
        client.create_domain_name(domainName="")

    ex.value.response["Error"]["Message"].should.equal("No Domain Name specified")
    ex.value.response["Error"]["Code"].should.equal("BadRequestException")


@mock_apigateway
def test_get_domain_names():
    client = boto3.client("apigateway", region_name="us-west-2")
    # without any domain names already present
    result = client.get_domain_names()
    result["items"].should.equal([])
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    response = client.create_domain_name(
        domainName=domain_name, certificateName=test_certificate_name
    )

    response["domainName"].should.equal(domain_name)
    response["certificateName"].should.equal(test_certificate_name)
    response["domainNameStatus"].should.equal("AVAILABLE")
    # after adding a new domain name
    result = client.get_domain_names()
    result["items"][0]["domainName"].should.equal(domain_name)
    result["items"][0]["certificateName"].should.equal(test_certificate_name)
    result["items"][0]["domainNameStatus"].should.equal("AVAILABLE")


@mock_apigateway
def test_get_domain_name():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    # adding a domain name
    client.create_domain_name(domainName=domain_name)
    # retrieving the data of added domain name.
    result = client.get_domain_name(domainName=domain_name)
    result["domainName"].should.equal(domain_name)
    result["domainNameStatus"].should.equal("AVAILABLE")


@mock_apigateway
def test_create_model():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    rest_api_id = response["id"]
    dummy_rest_api_id = "a12b3c4d"
    model_name = "testModel"
    description = "test model"
    content_type = "application/json"
    # success case with valid params
    response = client.create_model(
        restApiId=rest_api_id,
        name=model_name,
        description=description,
        contentType=content_type,
    )
    response["name"].should.equal(model_name)
    response["description"].should.equal(description)

    # with an invalid rest_api_id it should throw NotFoundException
    with pytest.raises(ClientError) as ex:
        client.create_model(
            restApiId=dummy_rest_api_id,
            name=model_name,
            description=description,
            contentType=content_type,
        )
    ex.value.response["Error"]["Message"].should.equal("Invalid Rest API Id specified")
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")

    with pytest.raises(ClientError) as ex:
        client.create_model(
            restApiId=rest_api_id,
            name="",
            description=description,
            contentType=content_type,
        )

    ex.value.response["Error"]["Message"].should.equal("No Model Name specified")
    ex.value.response["Error"]["Code"].should.equal("BadRequestException")


@mock_apigateway
def test_get_api_models():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    rest_api_id = response["id"]
    model_name = "testModel"
    description = "test model"
    content_type = "application/json"
    # when no models are present
    result = client.get_models(restApiId=rest_api_id)
    result["items"].should.equal([])
    # add a model
    client.create_model(
        restApiId=rest_api_id,
        name=model_name,
        description=description,
        contentType=content_type,
    )
    # get models after adding
    result = client.get_models(restApiId=rest_api_id)
    result["items"][0]["name"] = model_name
    result["items"][0]["description"] = description


@mock_apigateway
def test_get_model_by_name():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    rest_api_id = response["id"]
    dummy_rest_api_id = "a12b3c4d"
    model_name = "testModel"
    description = "test model"
    content_type = "application/json"
    # add a model
    client.create_model(
        restApiId=rest_api_id,
        name=model_name,
        description=description,
        contentType=content_type,
    )
    # get models after adding
    result = client.get_model(restApiId=rest_api_id, modelName=model_name)
    result["name"] = model_name
    result["description"] = description

    with pytest.raises(ClientError) as ex:
        client.get_model(restApiId=dummy_rest_api_id, modelName=model_name)
    ex.value.response["Error"]["Message"].should.equal("Invalid Rest API Id specified")
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")


@mock_apigateway
def test_get_model_with_invalid_name():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    rest_api_id = response["id"]
    # test with an invalid model name
    with pytest.raises(ClientError) as ex:
        client.get_model(restApiId=rest_api_id, modelName="fake")
    ex.value.response["Error"]["Message"].should.equal("Invalid Model Name specified")
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")


@mock_apigateway
def test_http_proxying_integration():
    responses_mock.add(
        responses_mock.GET, "http://httpbin.org/robots.txt", body="a fake response"
    )

    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", authorizationType="none"
    )

    client.put_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )

    response = client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="GET",
        type="HTTP",
        uri="http://httpbin.org/robots.txt",
        integrationHttpMethod="GET",
    )

    stage_name = "staging"
    client.create_deployment(restApiId=api_id, stageName=stage_name)

    deploy_url = "https://{api_id}.execute-api.{region_name}.amazonaws.com/{stage_name}".format(
        api_id=api_id, region_name=region_name, stage_name=stage_name
    )

    if not settings.TEST_SERVER_MODE:
        requests.get(deploy_url).content.should.equal(b"a fake response")


@mock_apigateway
def test_api_key_value_min_length():
    region_name = "us-east-1"
    client = boto3.client("apigateway", region_name=region_name)

    apikey_value = "12345"
    apikey_name = "TESTKEY1"
    payload = {"value": apikey_value, "name": apikey_name}

    with pytest.raises(ClientError) as e:
        client.create_api_key(**payload)
    ex = e.value
    ex.operation_name.should.equal("CreateApiKey")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("BadRequestException")
    ex.response["Error"]["Message"].should.equal(
        "API Key value should be at least 20 characters"
    )


@mock_apigateway
def test_get_api_key_include_value():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)

    apikey_value = "01234567890123456789"
    apikey_name = "TESTKEY1"
    payload = {"value": apikey_value, "name": apikey_name}

    response = client.create_api_key(**payload)
    api_key_id_one = response["id"]

    response = client.get_api_key(apiKey=api_key_id_one, includeValue=True)
    response.should.have.key("value")

    response = client.get_api_key(apiKey=api_key_id_one)
    response.should_not.have.key("value")

    response = client.get_api_key(apiKey=api_key_id_one, includeValue=True)
    response.should.have.key("value")

    response = client.get_api_key(apiKey=api_key_id_one, includeValue=False)
    response.should_not.have.key("value")

    response = client.get_api_key(apiKey=api_key_id_one, includeValue=True)
    response.should.have.key("value")


@mock_apigateway
def test_get_api_keys_include_values():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)

    apikey_value = "01234567890123456789"
    apikey_name = "TESTKEY1"
    payload = {"value": apikey_value, "name": apikey_name}

    apikey_value2 = "01234567890123456789123"
    apikey_name2 = "TESTKEY1"
    payload2 = {"value": apikey_value2, "name": apikey_name2}

    client.create_api_key(**payload)
    client.create_api_key(**payload2)

    response = client.get_api_keys()
    len(response["items"]).should.equal(2)
    for api_key in response["items"]:
        api_key.should_not.have.key("value")

    response = client.get_api_keys(includeValues=True)
    len(response["items"]).should.equal(2)
    for api_key in response["items"]:
        api_key.should.have.key("value")

    response = client.get_api_keys(includeValues=False)
    len(response["items"]).should.equal(2)
    for api_key in response["items"]:
        api_key.should_not.have.key("value")


@mock_apigateway
def test_create_api_key():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)

    apikey_value = "01234567890123456789"
    apikey_name = "TESTKEY1"
    payload = {"value": apikey_value, "name": apikey_name}

    response = client.create_api_key(**payload)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)
    response["name"].should.equal(apikey_name)
    response["value"].should.equal(apikey_value)
    response["enabled"].should.equal(False)
    response["stageKeys"].should.equal([])

    response = client.get_api_keys()
    len(response["items"]).should.equal(1)

    client.create_api_key.when.called_with(**payload).should.throw(ClientError)


@mock_apigateway
def test_create_api_headers():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)

    apikey_value = "01234567890123456789"
    apikey_name = "TESTKEY1"
    payload = {"value": apikey_value, "name": apikey_name}

    client.create_api_key(**payload)
    with pytest.raises(ClientError) as ex:
        client.create_api_key(**payload)
    ex.value.response["Error"]["Code"].should.equal("ConflictException")
    if not settings.TEST_SERVER_MODE:
        ex.value.response["ResponseMetadata"]["HTTPHeaders"].should.equal({})


@mock_apigateway
def test_api_keys():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)
    response = client.get_api_keys()
    len(response["items"]).should.equal(0)

    apikey_value = "01234567890123456789"
    apikey_name = "TESTKEY1"
    payload = {
        "value": apikey_value,
        "name": apikey_name,
        "tags": {"tag1": "test_tag1", "tag2": "1"},
    }
    response = client.create_api_key(**payload)
    apikey_id = response["id"]
    apikey = client.get_api_key(apiKey=response["id"], includeValue=True)
    apikey["name"].should.equal(apikey_name)
    apikey["value"].should.equal(apikey_value)
    apikey["tags"]["tag1"].should.equal("test_tag1")
    apikey["tags"]["tag2"].should.equal("1")

    patch_operations = [
        {"op": "replace", "path": "/name", "value": "TESTKEY3_CHANGE"},
        {"op": "replace", "path": "/customerId", "value": "12345"},
        {"op": "replace", "path": "/description", "value": "APIKEY UPDATE TEST"},
        {"op": "replace", "path": "/enabled", "value": "false"},
    ]
    response = client.update_api_key(apiKey=apikey_id, patchOperations=patch_operations)
    response["name"].should.equal("TESTKEY3_CHANGE")
    response["customerId"].should.equal("12345")
    response["description"].should.equal("APIKEY UPDATE TEST")
    response["enabled"].should.equal(False)

    updated_api_key = client.get_api_key(apiKey=apikey_id)
    updated_api_key["name"].should.equal("TESTKEY3_CHANGE")
    updated_api_key["customerId"].should.equal("12345")
    updated_api_key["description"].should.equal("APIKEY UPDATE TEST")
    updated_api_key["enabled"].should.equal(False)

    response = client.get_api_keys()
    len(response["items"]).should.equal(1)

    payload = {"name": apikey_name}
    client.create_api_key(**payload)

    response = client.get_api_keys()
    len(response["items"]).should.equal(2)

    response = client.delete_api_key(apiKey=apikey_id)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(202)

    response = client.get_api_keys()
    len(response["items"]).should.equal(1)


@mock_apigateway
def test_usage_plans():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)
    response = client.get_usage_plans()
    len(response["items"]).should.equal(0)

    # # Try to get info about a non existing usage
    with pytest.raises(ClientError) as ex:
        client.get_usage_plan(usagePlanId="not_existing")
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")
    ex.value.response["Error"]["Message"].should.equal(
        "Invalid Usage Plan ID specified"
    )

    usage_plan_name = "TEST-PLAN"
    payload = {"name": usage_plan_name}
    response = client.create_usage_plan(**payload)
    usage_plan = client.get_usage_plan(usagePlanId=response["id"])
    usage_plan["name"].should.equal(usage_plan_name)
    usage_plan["apiStages"].should.equal([])

    payload = {
        "name": "TEST-PLAN-2",
        "description": "Description",
        "quota": {"limit": 10, "period": "DAY", "offset": 0},
        "throttle": {"rateLimit": 2, "burstLimit": 1},
        "apiStages": [{"apiId": "foo", "stage": "bar"}],
        "tags": {"tag_key": "tag_value"},
    }
    response = client.create_usage_plan(**payload)
    usage_plan_id = response["id"]
    usage_plan = client.get_usage_plan(usagePlanId=usage_plan_id)

    # The payload should remain unchanged
    for key, value in payload.items():
        usage_plan.should.have.key(key).which.should.equal(value)

    # Status code should be 200
    usage_plan["ResponseMetadata"].should.have.key("HTTPStatusCode").which.should.equal(
        200
    )

    # An Id should've been generated
    usage_plan.should.have.key("id").which.should_not.be.none

    response = client.get_usage_plans()
    len(response["items"]).should.equal(2)

    client.delete_usage_plan(usagePlanId=usage_plan_id)

    response = client.get_usage_plans()
    len(response["items"]).should.equal(1)


@mock_apigateway
def test_update_usage_plan():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)

    payload = {
        "name": "TEST-PLAN-2",
        "description": "Description",
        "quota": {"limit": 10, "period": "DAY", "offset": 0},
        "throttle": {"rateLimit": 2, "burstLimit": 1},
        "apiStages": [{"apiId": "foo", "stage": "bar"}],
        "tags": {"tag_key": "tag_value"},
    }
    response = client.create_usage_plan(**payload)
    usage_plan_id = response["id"]
    response = client.update_usage_plan(
        usagePlanId=usage_plan_id,
        patchOperations=[
            {"op": "replace", "path": "/quota/limit", "value": "1000"},
            {"op": "replace", "path": "/quota/period", "value": "MONTH"},
            {"op": "replace", "path": "/throttle/rateLimit", "value": "500"},
            {"op": "replace", "path": "/throttle/burstLimit", "value": "1500"},
            {"op": "replace", "path": "/name", "value": "new-name"},
            {"op": "replace", "path": "/description", "value": "new-description"},
            {"op": "replace", "path": "/productCode", "value": "new-productionCode"},
        ],
    )
    response["quota"]["limit"].should.equal("1000")
    response["quota"]["period"].should.equal("MONTH")
    response["quota"]["limit"].should.equal("1000")
    response["name"].should.equal("new-name")
    response["description"].should.equal("new-description")
    response["productCode"].should.equal("new-productionCode")


@mock_apigateway
def test_usage_plan_keys():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)
    usage_plan_id = "test"

    # Create an API key so we can use it
    key_name = "test-api-key"
    response = client.create_api_key(name=key_name)
    key_id = response["id"]
    key_value = response["value"]

    # Get current plan keys (expect none)
    response = client.get_usage_plan_keys(usagePlanId=usage_plan_id)
    len(response["items"]).should.equal(0)

    # Create usage plan key
    key_type = "API_KEY"
    payload = {"usagePlanId": usage_plan_id, "keyId": key_id, "keyType": key_type}
    response = client.create_usage_plan_key(**payload)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equals(201)
    usage_plan_key_id = response["id"]

    # Get current plan keys (expect 1)
    response = client.get_usage_plan_keys(usagePlanId=usage_plan_id)
    len(response["items"]).should.equal(1)

    # Get a single usage plan key and check it matches the created one
    usage_plan_key = client.get_usage_plan_key(
        usagePlanId=usage_plan_id, keyId=usage_plan_key_id
    )
    usage_plan_key["name"].should.equal(key_name)
    usage_plan_key["id"].should.equal(key_id)
    usage_plan_key["type"].should.equal(key_type)
    usage_plan_key["value"].should.equal(key_value)

    # Delete usage plan key
    client.delete_usage_plan_key(usagePlanId=usage_plan_id, keyId=key_id)

    # Get current plan keys (expect none)
    response = client.get_usage_plan_keys(usagePlanId=usage_plan_id)
    len(response["items"]).should.equal(0)

    # Try to get info about a non existing api key
    with pytest.raises(ClientError) as ex:
        client.get_usage_plan_key(usagePlanId=usage_plan_id, keyId="not_existing_key")
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")
    ex.value.response["Error"]["Message"].should.equal(
        "Invalid API Key identifier specified"
    )

    # Try to get info about an existing api key that has not jet added to a valid usage plan
    with pytest.raises(ClientError) as ex:
        client.get_usage_plan_key(usagePlanId=usage_plan_id, keyId=key_id)
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")
    ex.value.response["Error"]["Message"].should.equal(
        "Invalid Usage Plan ID specified"
    )

    # Try to get info about an existing api key that has not jet added to a valid usage plan
    with pytest.raises(ClientError) as ex:
        client.get_usage_plan_key(usagePlanId="not_existing_plan_id", keyId=key_id)
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")
    ex.value.response["Error"]["Message"].should.equal(
        "Invalid Usage Plan ID specified"
    )


@mock_apigateway
def test_create_usage_plan_key_non_existent_api_key():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)
    usage_plan_id = "test"

    # Attempt to create a usage plan key for a API key that doesn't exists
    payload = {
        "usagePlanId": usage_plan_id,
        "keyId": "non-existent",
        "keyType": "API_KEY",
    }
    client.create_usage_plan_key.when.called_with(**payload).should.throw(ClientError)


@mock_apigateway
def test_get_usage_plans_using_key_id():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)

    # Create 2 Usage Plans
    # one will be attached to an API Key, the other will remain unattached
    attached_plan = client.create_usage_plan(name="Attached")
    unattached_plan = client.create_usage_plan(name="Unattached")

    # Create an API key
    # to attach to the usage plan
    key_name = "test-api-key"
    response = client.create_api_key(name=key_name)
    key_id = response["id"]

    # Create a Usage Plan Key
    # Attached the Usage Plan and API Key
    key_type = "API_KEY"
    payload = {"usagePlanId": attached_plan["id"], "keyId": key_id, "keyType": key_type}
    response = client.create_usage_plan_key(**payload)

    # All usage plans should be returned when keyId is not included
    all_plans = client.get_usage_plans()
    len(all_plans["items"]).should.equal(2)

    # Only the usage plan attached to the given api key are included
    only_plans_with_key = client.get_usage_plans(keyId=key_id)
    len(only_plans_with_key["items"]).should.equal(1)
    only_plans_with_key["items"][0]["name"].should.equal(attached_plan["name"])
    only_plans_with_key["items"][0]["id"].should.equal(attached_plan["id"])


def create_method_integration(client, api_id, httpMethod="GET"):
    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]
    client.put_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod=httpMethod,
        authorizationType="NONE",
    )
    client.put_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod=httpMethod, statusCode="200"
    )
    client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod=httpMethod,
        type="HTTP",
        uri="http://httpbin.org/robots.txt",
        integrationHttpMethod="POST",
    )
    client.put_integration_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod=httpMethod,
        statusCode="200",
        responseTemplates={},
    )
    return root_id


@mock_apigateway
def test_get_integration_response_unknown_response():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    root_id = create_method_integration(client, api_id)
    client.get_integration_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )
    with pytest.raises(ClientError) as ex:
        client.get_integration_response(
            restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="300"
        )

    ex.value.response["Error"]["Message"].should.equal(
        "Invalid Response status code specified"
    )
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")


@mock_apigateway
def test_delete_stage_unknown_stage():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    with pytest.raises(ClientError) as ex:
        client.delete_stage(restApiId=api_id, stageName="unknown")

    ex.value.response["Error"]["Message"].should.equal(
        "Invalid stage identifier specified"
    )
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")


@mock_apigateway
def test_get_api_key_unknown_apikey():
    client = boto3.client("apigateway", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.get_api_key(apiKey="unknown")

    ex.value.response["Error"]["Message"].should.equal(
        "Invalid API Key identifier specified"
    )
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")


@mock_apigateway
def test_get_domain_name_unknown_domainname():
    client = boto3.client("apigateway", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.get_domain_name(domainName="www.google.com")

    ex.value.response["Error"]["Message"].should.equal(
        "Invalid domain name identifier specified"
    )
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")


@mock_apigateway
def test_update_domain_name_unknown_domainname():
    client = boto3.client("apigateway", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.update_domain_name(domainName="www.google.fr", patchOperations=[])

    ex.value.response["Error"]["Message"].should.equal(
        "Invalid domain name identifier specified"
    )
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")


@mock_apigateway
def test_delete_domain_name_unknown_domainname():
    client = boto3.client("apigateway", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.delete_domain_name(domainName="www.google.com")

    ex.value.response["Error"]["Message"].should.equal(
        "Invalid domain name identifier specified"
    )
    ex.value.response["Error"]["Code"].should.equal("NotFoundException")
