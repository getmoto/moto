import json

import boto3
from freezegun import freeze_time
from botocore.exceptions import ClientError

from moto import mock_apigateway, mock_cognitoidp, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
import pytest

from tests import DEFAULT_ACCOUNT_ID


@freeze_time("2015-01-01")
@mock_apigateway
def test_create_and_get_rest_api():
    client = boto3.client("apigateway", region_name="us-west-2")

    response = client.create_rest_api(
        name="my_api", description="this is my api", disableExecuteApiEndpoint=True
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)

    response.pop("ResponseMetadata")
    response.pop("createdDate")
    assert response == {
        "id": api_id,
        "name": "my_api",
        "description": "this is my api",
        "version": "V1",
        "binaryMediaTypes": [],
        "apiKeySource": "HEADER",
        "endpointConfiguration": {"types": ["EDGE"]},
        "tags": {},
        "disableExecuteApiEndpoint": True,
    }


@mock_apigateway
def test_update_rest_api():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    patchOperations = [
        {"op": "replace", "path": "/name", "value": "new-name"},
        {"op": "replace", "path": "/description", "value": "new-description"},
        {"op": "replace", "path": "/apiKeySource", "value": "AUTHORIZER"},
        {"op": "replace", "path": "/binaryMediaTypes", "value": "image/jpeg"},
        {"op": "replace", "path": "/disableExecuteApiEndpoint", "value": "True"},
        {
            "op": "replace",
            "path": "/policy",
            "value": '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": "*", "Action": '
            '"execute-api:Invoke", "Resource": ["execute-api:/*"]}]}',
        },
    ]

    response = client.update_rest_api(restApiId=api_id, patchOperations=patchOperations)
    response.pop("ResponseMetadata")
    response.pop("createdDate")
    response.pop("binaryMediaTypes")
    assert response == {
        "id": api_id,
        "name": "new-name",
        "version": "V1",
        "description": "new-description",
        "apiKeySource": "AUTHORIZER",
        "policy": '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": "*", "Action": '
        '"execute-api:Invoke", "Resource": ["execute-api:/*"]}]}',
        "endpointConfiguration": {"types": ["EDGE"]},
        "tags": {},
        "disableExecuteApiEndpoint": True,
    }
    # should fail with wrong apikeysoruce
    patchOperations = [
        {"op": "replace", "path": "/apiKeySource", "value": "Wrong-value-AUTHORIZER"}
    ]
    with pytest.raises(ClientError) as ex:
        client.update_rest_api(restApiId=api_id, patchOperations=patchOperations)
    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == "1 validation error detected: Value 'Wrong-value-AUTHORIZER' at 'createRestApiInput.apiKeySource' failed to satisfy constraint: Member must satisfy enum value set: [AUTHORIZER, HEADER]"
    )
    assert err["Code"] == "ValidationException"


@mock_apigateway
def test_update_rest_api_invalid_api_id():
    client = boto3.client("apigateway", region_name="us-west-2")
    patchOperations = [
        {"op": "replace", "path": "/apiKeySource", "value": "AUTHORIZER"}
    ]
    with pytest.raises(ClientError) as ex:
        client.update_rest_api(restApiId="api_id", patchOperations=patchOperations)
    assert ex.value.response["Error"]["Code"] == "NotFoundException"


@mock_apigateway
def test_update_rest_api_operation_add_remove():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    patchOperations = [
        {"op": "add", "path": "/binaryMediaTypes", "value": "image/png"},
        {"op": "add", "path": "/binaryMediaTypes", "value": "image/jpeg"},
    ]
    response = client.update_rest_api(restApiId=api_id, patchOperations=patchOperations)
    assert response["binaryMediaTypes"] == ["image/png", "image/jpeg"]
    assert response["description"] == "this is my api"
    patchOperations = [
        {"op": "remove", "path": "/binaryMediaTypes", "value": "image/png"},
        {"op": "remove", "path": "/description"},
    ]
    response = client.update_rest_api(restApiId=api_id, patchOperations=patchOperations)
    assert response["binaryMediaTypes"] == ["image/jpeg"]
    assert response["description"] == ""


@mock_apigateway
def test_list_and_delete_apis():
    client = boto3.client("apigateway", region_name="us-west-2")

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    client.create_rest_api(name="my_api2", description="this is my api2")

    response = client.get_rest_apis()
    assert len(response["items"]) == 2

    client.delete_rest_api(restApiId=api_id)

    response = client.get_rest_apis()
    assert len(response["items"]) == 1


@mock_apigateway
def test_create_rest_api_with_tags():
    client = boto3.client("apigateway", region_name="us-west-2")

    response = client.create_rest_api(
        name="my_api", description="this is my api", tags={"MY_TAG1": "MY_VALUE1"}
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)

    assert "tags" in response
    assert response["tags"] == {"MY_TAG1": "MY_VALUE1"}


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
    assert response["policy"] == policy


@mock_apigateway
def test_create_rest_api_invalid_apikeysource():
    client = boto3.client("apigateway", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        client.create_rest_api(
            name="my_api",
            description="this is my api",
            apiKeySource="not a valid api key source",
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"


@mock_apigateway
def test_create_rest_api_valid_apikeysources():
    client = boto3.client("apigateway", region_name="us-west-2")

    # 1. test creating rest api with HEADER apiKeySource
    response = client.create_rest_api(
        name="my_api", description="this is my api", apiKeySource="HEADER"
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)
    assert response["apiKeySource"] == "HEADER"

    # 2. test creating rest api with AUTHORIZER apiKeySource
    response = client.create_rest_api(
        name="my_api2", description="this is my api", apiKeySource="AUTHORIZER"
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)
    assert response["apiKeySource"] == "AUTHORIZER"


@mock_apigateway
def test_create_rest_api_invalid_endpointconfiguration():
    client = boto3.client("apigateway", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        client.create_rest_api(
            name="my_api",
            description="this is my api",
            endpointConfiguration={"types": ["INVALID"]},
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"


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
    assert response["endpointConfiguration"] == {"types": ["PRIVATE"]}

    # 2. test creating rest api with REGIONAL endpointConfiguration
    response = client.create_rest_api(
        name="my_api2",
        description="this is my api",
        endpointConfiguration={"types": ["REGIONAL"]},
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)
    assert response["endpointConfiguration"] == {"types": ["REGIONAL"]}

    # 3. test creating rest api with EDGE endpointConfiguration
    response = client.create_rest_api(
        name="my_api3",
        description="this is my api",
        endpointConfiguration={"types": ["EDGE"]},
    )
    api_id = response["id"]

    response = client.get_rest_api(restApiId=api_id)
    assert response["endpointConfiguration"] == {"types": ["EDGE"]}


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
    valid_names = ["users", "{user_id}", "{proxy+}", "{pro:xy+}", "us:er_0-9"]
    # All invalid names should throw an exception
    for name in invalid_names:
        with pytest.raises(ClientError) as ex:
            client.create_resource(restApiId=api_id, parentId=root_id, pathPart=name)
        err = ex.value.response["Error"]
        assert err["Code"] == "BadRequestException"
        assert (
            err["Message"]
            == "Resource's path part only allow a-zA-Z0-9._- and curly braces at the beginning and the end and an optional plus sign before the closing brace."
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
    assert root_resource == {
        "path": "/",
        "id": root_id,
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    client.create_resource(restApiId=api_id, parentId=root_id, pathPart="users")

    resources = client.get_resources(restApiId=api_id)["items"]
    assert len(resources) == 2
    non_root_resource = [resource for resource in resources if resource["path"] != "/"][
        0
    ]

    client.delete_resource(restApiId=api_id, resourceId=non_root_resource["id"])

    assert len(client.get_resources(restApiId=api_id)["items"]) == 1


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
    assert child_resource == {
        "path": "/users/tags",
        "pathPart": "tags",
        "parentId": users_id,
        "id": tags_id,
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }


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
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="GET",
        authorizationType="none",
        requestParameters={"method.request.header.InvocationType": True},
    )

    response = client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    assert response == {
        "httpMethod": "GET",
        "authorizationType": "none",
        "apiKeyRequired": False,
        "methodResponses": {},
        "requestParameters": {"method.request.header.InvocationType": True},
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }


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
    assert response == {
        "httpMethod": "GET",
        "authorizationType": "none",
        "apiKeyRequired": True,
        "methodResponses": {},
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }


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
    assert response == {
        "ResponseMetadata": {"HTTPStatusCode": 201},
        "statusCode": "200",
    }

    response = client.get_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    assert response == {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "statusCode": "200",
    }

    response = client.delete_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    assert response == {"ResponseMetadata": {"HTTPStatusCode": 204}}


@mock_apigateway
def test_get_method_unknown_resource_id():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    with pytest.raises(ClientError) as ex:
        client.get_method(restApiId=api_id, resourceId="sth", httpMethod="GET")
    err = ex.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid resource identifier specified"


@mock_apigateway
def test_delete_method():
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

    client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")

    client.delete_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")

    with pytest.raises(ClientError) as ex:
        client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")
    err = ex.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid Method identifier specified"


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
        passthroughBehavior="WHEN_NO_TEMPLATES",
        uri="http://httpbin.org/robots.txt",
        integrationHttpMethod="POST",
        requestParameters={"integration.request.header.X-Custom": "'Custom'"},
        contentHandling="CONVERT_TO_TEXT",
        credentials=f"arn:aws:iam::{DEFAULT_ACCOUNT_ID}:role/apigateway-invoke-lambda-exec-role",
        tlsConfig={"insecureSkipVerification": True},
        connectionType="INTERNET",
    )

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    assert response == {
        "ResponseMetadata": {"HTTPStatusCode": 201},
        "httpMethod": "POST",
        "type": "HTTP",
        "uri": "http://httpbin.org/robots.txt",
        "passthroughBehavior": "WHEN_NO_TEMPLATES",
        "cacheKeyParameters": [],
        "requestParameters": {"integration.request.header.X-Custom": "'Custom'"},
        "contentHandling": "CONVERT_TO_TEXT",
        "credentials": f"arn:aws:iam::{DEFAULT_ACCOUNT_ID}:role/apigateway-invoke-lambda-exec-role",
        "tlsConfig": {"insecureSkipVerification": True},
        "connectionType": "INTERNET",
    }

    response = client.get_integration(
        restApiId=api_id, resourceId=root_id, httpMethod="GET"
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    assert response == {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "httpMethod": "POST",
        "type": "HTTP",
        "uri": "http://httpbin.org/robots.txt",
        "passthroughBehavior": "WHEN_NO_TEMPLATES",
        "cacheKeyParameters": [],
        "requestParameters": {"integration.request.header.X-Custom": "'Custom'"},
        "contentHandling": "CONVERT_TO_TEXT",
        "credentials": f"arn:aws:iam::{DEFAULT_ACCOUNT_ID}:role/apigateway-invoke-lambda-exec-role",
        "tlsConfig": {"insecureSkipVerification": True},
        "connectionType": "INTERNET",
    }

    response = client.get_resource(restApiId=api_id, resourceId=root_id)
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    assert response["resourceMethods"]["GET"]["httpMethod"] == "GET"
    assert response["resourceMethods"]["GET"]["authorizationType"] == "none"
    assert response["resourceMethods"]["GET"]["methodIntegration"] == {
        "httpMethod": "POST",
        "type": "HTTP",
        "uri": "http://httpbin.org/robots.txt",
        "cacheKeyParameters": [],
        "passthroughBehavior": "WHEN_NO_TEMPLATES",
        "requestParameters": {"integration.request.header.X-Custom": "'Custom'"},
        "contentHandling": "CONVERT_TO_TEXT",
        "credentials": f"arn:aws:iam::{DEFAULT_ACCOUNT_ID}:role/apigateway-invoke-lambda-exec-role",
        "tlsConfig": {"insecureSkipVerification": True},
        "connectionType": "INTERNET",
    }

    client.delete_integration(restApiId=api_id, resourceId=root_id, httpMethod="GET")

    response = client.get_resource(restApiId=api_id, resourceId=root_id)
    assert "methodIntegration" not in response["resourceMethods"]["GET"]

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
    client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="POST",
        type="HTTP",
        uri=test_uri,
        requestTemplates=templates,
        passthroughBehavior="WHEN_NO_MATCH",
        integrationHttpMethod="POST",
        timeoutInMillis=29000,
    )

    response = client.get_integration(
        restApiId=api_id, resourceId=root_id, httpMethod="POST"
    )
    assert response["uri"] == test_uri
    assert response["requestTemplates"] == templates
    assert response["passthroughBehavior"] == "WHEN_NO_MATCH"
    assert response["timeoutInMillis"] == 29000


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
        responseParameters={
            "method.response.header.Location": "integration.response.body.redirect.url",
            "method.response.header.x-user-id": "integration.response.header.x-userid",
        },
        responseTemplates={},
    )

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    assert response == {
        "statusCode": "200",
        "selectionPattern": "foobar",
        "ResponseMetadata": {"HTTPStatusCode": 201},
        "responseTemplates": {},  # Note: TF compatibility
        "responseParameters": {
            "method.response.header.Location": "integration.response.body.redirect.url",
            "method.response.header.x-user-id": "integration.response.header.x-userid",
        },
    }

    response = client.get_integration_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    assert response == {
        "statusCode": "200",
        "selectionPattern": "foobar",
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "responseTemplates": {},  # Note: TF compatibility
        "responseParameters": {
            "method.response.header.Location": "integration.response.body.redirect.url",
            "method.response.header.x-user-id": "integration.response.header.x-userid",
        },
    }

    response = client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    assert response["methodIntegration"]["integrationResponses"] == {
        "200": {
            "responseTemplates": {},  # Note: TF compatibility
            "selectionPattern": "foobar",
            "statusCode": "200",
            "responseParameters": {
                "method.response.header.Location": "integration.response.body.redirect.url",
                "method.response.header.x-user-id": "integration.response.header.x-userid",
            },
        }
    }

    client.delete_integration_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )

    response = client.get_method(restApiId=api_id, resourceId=root_id, httpMethod="GET")
    assert response["methodIntegration"]["integrationResponses"] == {}

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
    assert response == {
        "statusCode": "200",
        "selectionPattern": "foobar",
        "ResponseMetadata": {"HTTPStatusCode": 201},
        "responseTemplates": {},  # Note: TF compatibility
        "contentHandling": "CONVERT_TO_BINARY",
    }

    response = client.get_integration_response(
        restApiId=api_id, resourceId=root_id, httpMethod="PUT", statusCode="200"
    )
    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    assert response == {
        "statusCode": "200",
        "selectionPattern": "foobar",
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "responseTemplates": {},  # Note: TF compatibility
        "contentHandling": "CONVERT_TO_BINARY",
    }


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
    assert response == {
        "id": authorizer_id,
        "name": authorizer_name,
        "type": "COGNITO_USER_POOLS",
        "providerARNs": [user_pool_arn],
        "identitySource": "method.request.header.Authorization",
        "authorizerResultTtlInSeconds": 300,
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    client.update_authorizer(
        restApiId=api_id,
        authorizerId=authorizer_id,
        patchOperations=[{"op": "replace", "path": "/type", "value": "TOKEN"}],
    )

    authorizer = client.get_authorizer(restApiId=api_id, authorizerId=authorizer_id)

    assert authorizer["type"] == "TOKEN"

    client.update_authorizer(
        restApiId=api_id,
        authorizerId=authorizer_id,
        patchOperations=[{"op": "replace", "path": "/type", "value": "REQUEST"}],
    )

    authorizer = client.get_authorizer(restApiId=api_id, authorizerId=authorizer_id)
    assert authorizer["type"] == "REQUEST"

    # TODO: implement mult-update tests

    with pytest.raises(Exception) as exc:
        client.update_authorizer(
            restApiId=api_id,
            authorizerId=authorizer_id,
            patchOperations=[
                {"op": "add", "path": "/notasetting", "value": "eu-west-1"}
            ],
        )
    if settings.TEST_DECORATOR_MODE:
        assert 'Patch operation "add" not implemented' in str(exc.value)


@mock_apigateway
def test_non_existent_authorizer():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    with pytest.raises(ClientError) as exc:
        client.get_authorizer(restApiId=api_id, authorizerId="xxx")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid Authorizer identifier specified"

    with pytest.raises(ClientError) as exc:
        client.update_authorizer(
            restApiId=api_id,
            authorizerId="xxx",
            patchOperations=[{"op": "add", "path": "/type", "value": "sth"}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid Authorizer identifier specified"


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
    assert response == {
        "id": authorizer_id,
        "name": authorizer_name,
        "type": "COGNITO_USER_POOLS",
        "providerARNs": [user_pool_arn],
        "identitySource": "method.request.header.Authorization",
        "authorizerResultTtlInSeconds": 300,
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

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

    assert response["items"][0]["id"] in [authorizer_id, authorizer_id2]
    assert response["items"][1]["id"] in [authorizer_id, authorizer_id2]

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

    assert response == {
        "name": new_authorizer_name_with_vars,
        "id": authorizer_id3,
        "type": "COGNITO_USER_POOLS",
        "providerARNs": [user_pool_arn],
        "identitySource": "method.request.header.Authorization",
        "authorizerResultTtlInSeconds": 300,
        "ResponseMetadata": {"HTTPStatusCode": 201},
    }

    stage = client.get_authorizer(restApiId=api_id, authorizerId=authorizer_id3)
    assert stage["name"] == new_authorizer_name_with_vars
    assert stage["id"] == authorizer_id3
    assert stage["type"] == "COGNITO_USER_POOLS"
    assert stage["providerARNs"] == [user_pool_arn]
    assert stage["identitySource"] == "method.request.header.Authorization"
    assert stage["authorizerResultTtlInSeconds"] == 300


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
    assert response == {
        "id": authorizer_id,
        "name": authorizer_name,
        "type": "COGNITO_USER_POOLS",
        "providerARNs": [user_pool_arn],
        "identitySource": "method.request.header.Authorization",
        "authorizerResultTtlInSeconds": 300,
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

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
    assert sorted([authorizer["name"] for authorizer in authorizers]) == sorted(
        [authorizer_name2, authorizer_name]
    )
    # delete stage
    response = client.delete_authorizer(restApiId=api_id, authorizerId=authorizer_id2)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 202
    # verify other stage still exists
    authorizers = client.get_authorizers(restApiId=api_id)["items"]
    assert [authorizer["name"] for authorizer in authorizers] == [authorizer_name]


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

    client.put_integration_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="GET",
        statusCode="200",
        selectionPattern="foobar",
        responseParameters={
            "method.response.header.Location": "integration.response.body.redirect.url",
            "method.response.header.x-user-id": "integration.response.header.x-userid",
        },
        responseTemplates={"application/json": json.dumps({"data": "test"})},
    )

    response = client.get_integration_response(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    )

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    assert response == {
        "statusCode": "200",
        "selectionPattern": "foobar",
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "responseTemplates": {"application/json": json.dumps({"data": "test"})},
        "responseParameters": {
            "method.response.header.Location": "integration.response.body.redirect.url",
            "method.response.header.x-user-id": "integration.response.header.x-userid",
        },
    }


@mock_apigateway
def test_put_integration_response_but_integration_not_found():
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

    with pytest.raises(ClientError) as ex:
        client.put_integration_response(
            restApiId=api_id,
            resourceId=root_id,
            httpMethod="GET",
            statusCode="200",
            selectionPattern="foobar",
            responseTemplates={"application/json": json.dumps({"data": "test"})},
        )
    assert ex.value.response["Error"]["Code"] == "NotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


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

    for _type in types_requiring_integration_method:
        # Ensure that integrations of these types fail if no integrationHttpMethod is provided
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                httpMethod="GET",
                type=_type,
                uri="http://httpbin.org/robots.txt",
            )
        assert ex.value.response["Error"]["Code"] == "BadRequestException"
        assert (
            ex.value.response["Error"]["Message"]
            == "Enumeration value for HttpMethod must be non-empty"
        )
    for _type in types_not_requiring_integration_method:
        # Ensure that integrations of these types do not need the integrationHttpMethod
        client.put_integration(
            restApiId=api_id,
            resourceId=root_id,
            httpMethod="GET",
            type=_type,
            uri="http://httpbin.org/robots.txt",
        )
    for _type in http_types:
        # Ensure that it works fine when providing the integrationHttpMethod-argument
        client.put_integration(
            restApiId=api_id,
            resourceId=root_id,
            httpMethod="GET",
            type=_type,
            uri="http://httpbin.org/robots.txt",
            integrationHttpMethod="POST",
        )
    for _type in ["AWS"]:
        # Ensure that it works fine when providing the integrationHttpMethod + credentials
        client.put_integration(
            restApiId=api_id,
            resourceId=root_id,
            credentials=f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/testfunction-role-oe783psq",
            httpMethod="GET",
            type=_type,
            uri="arn:aws:apigateway:us-west-2:s3:path/b/k",
            integrationHttpMethod="POST",
        )
    for _type in aws_types:
        # Ensure that credentials are not required when URI points to a Lambda stream
        client.put_integration(
            restApiId=api_id,
            resourceId=root_id,
            httpMethod="GET",
            type=_type,
            uri="arn:aws:apigateway:eu-west-1:lambda:path/2015-03-31/functions/arn:aws:lambda:eu-west-1:012345678901:function:MyLambda/invocations",
            integrationHttpMethod="POST",
        )
    for _type in ["AWS_PROXY"]:
        # Ensure that aws_proxy does not support S3
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                credentials=f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/testfunction-role-oe783psq",
                httpMethod="GET",
                type=_type,
                uri="arn:aws:apigateway:us-west-2:s3:path/b/k",
                integrationHttpMethod="POST",
            )
        assert ex.value.response["Error"]["Code"] == "BadRequestException"
        assert (
            ex.value.response["Error"]["Message"]
            == "Integrations of type 'AWS_PROXY' currently only supports Lambda function and Firehose stream invocations."
        )
    for _type in aws_types:
        # Ensure that the Role ARN is for the current account
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                credentials="arn:aws:iam::000000000000:role/service-role/testrole",
                httpMethod="GET",
                type=_type,
                uri="arn:aws:apigateway:us-west-2:s3:path/b/k",
                integrationHttpMethod="POST",
            )
        assert ex.value.response["Error"]["Code"] == "AccessDeniedException"
        assert (
            ex.value.response["Error"]["Message"]
            == "Cross-account pass role is not allowed."
        )
    for _type in ["AWS"]:
        # Ensure that the Role ARN is specified for aws integrations
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                httpMethod="GET",
                type=_type,
                uri="arn:aws:apigateway:us-west-2:s3:path/b/k",
                integrationHttpMethod="POST",
            )
        assert ex.value.response["Error"]["Code"] == "BadRequestException"
        assert (
            ex.value.response["Error"]["Message"]
            == "Role ARN must be specified for AWS integrations"
        )
    for _type in http_types:
        # Ensure that the URI is valid HTTP
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                httpMethod="GET",
                type=_type,
                uri="non-valid-http",
                integrationHttpMethod="POST",
            )
        assert ex.value.response["Error"]["Code"] == "BadRequestException"
        assert (
            ex.value.response["Error"]["Message"]
            == "Invalid HTTP endpoint specified for URI"
        )
    for _type in aws_types:
        # Ensure that the URI is an ARN
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                httpMethod="GET",
                type=_type,
                uri="non-valid-arn",
                integrationHttpMethod="POST",
            )
        assert ex.value.response["Error"]["Code"] == "BadRequestException"
        assert (
            ex.value.response["Error"]["Message"]
            == "Invalid ARN specified in the request"
        )
    for _type in aws_types:
        # Ensure that the URI is a valid ARN
        with pytest.raises(ClientError) as ex:
            client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                httpMethod="GET",
                type=_type,
                uri="arn:aws:iam::0000000000:role/service-role/asdf",
                integrationHttpMethod="POST",
            )
        assert ex.value.response["Error"]["Code"] == "BadRequestException"
        assert (
            ex.value.response["Error"]["Message"]
            == "AWS ARN for integration must contain path or action"
        )


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
    assert response["domainName"] == domain_name
    assert response["certificateName"] == test_certificate_name
    # without domain name it should throw BadRequestException
    with pytest.raises(ClientError) as ex:
        client.create_domain_name(domainName="")

    assert ex.value.response["Error"]["Message"] == "No Domain Name specified"
    assert ex.value.response["Error"]["Code"] == "BadRequestException"


@mock_apigateway
def test_get_domain_names():
    client = boto3.client("apigateway", region_name="us-west-2")
    # without any domain names already present
    result = client.get_domain_names()
    assert result["items"] == []
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    response = client.create_domain_name(
        domainName=domain_name, certificateName=test_certificate_name
    )

    assert response["domainName"] == domain_name
    assert response["certificateName"] == test_certificate_name
    assert response["domainNameStatus"] == "AVAILABLE"
    # after adding a new domain name
    result = client.get_domain_names()
    assert result["items"][0]["domainName"] == domain_name
    assert result["items"][0]["certificateName"] == test_certificate_name
    assert result["items"][0]["domainNameStatus"] == "AVAILABLE"


@mock_apigateway
def test_get_domain_name():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    # adding a domain name
    client.create_domain_name(domainName=domain_name)
    # retrieving the data of added domain name.
    result = client.get_domain_name(domainName=domain_name)
    assert result["domainName"] == domain_name
    assert result["domainNameStatus"] == "AVAILABLE"


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
    assert response["name"] == model_name
    assert response["description"] == description

    # with an invalid rest_api_id it should throw NotFoundException
    with pytest.raises(ClientError) as ex:
        client.create_model(
            restApiId=dummy_rest_api_id,
            name=model_name,
            description=description,
            contentType=content_type,
        )
    assert ex.value.response["Error"]["Message"] == "Invalid Rest API Id specified"
    assert ex.value.response["Error"]["Code"] == "NotFoundException"

    with pytest.raises(ClientError) as ex:
        client.create_model(
            restApiId=rest_api_id,
            name="",
            description=description,
            contentType=content_type,
        )

    assert ex.value.response["Error"]["Message"] == "No Model Name specified"
    assert ex.value.response["Error"]["Code"] == "BadRequestException"


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
    assert result["items"] == []
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
    assert ex.value.response["Error"]["Message"] == "Invalid Rest API Id specified"
    assert ex.value.response["Error"]["Code"] == "NotFoundException"


@mock_apigateway
def test_get_model_with_invalid_name():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    rest_api_id = response["id"]
    # test with an invalid model name
    with pytest.raises(ClientError) as ex:
        client.get_model(restApiId=rest_api_id, modelName="fake")
    assert ex.value.response["Error"]["Message"] == "Invalid Model Name specified"
    assert ex.value.response["Error"]["Code"] == "NotFoundException"


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
    assert ex.operation_name == "CreateApiKey"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "BadRequestException"
    assert (
        ex.response["Error"]["Message"]
        == "API Key value should be at least 20 characters"
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
    assert "value" in response

    response = client.get_api_key(apiKey=api_key_id_one)
    assert "value" not in response

    response = client.get_api_key(apiKey=api_key_id_one, includeValue=True)
    assert "value" in response

    response = client.get_api_key(apiKey=api_key_id_one, includeValue=False)
    assert "value" not in response

    response = client.get_api_key(apiKey=api_key_id_one, includeValue=True)
    assert "value" in response


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
    assert len(response["items"]) == 2
    for api_key in response["items"]:
        assert "value" not in api_key

    response = client.get_api_keys(includeValues=True)
    assert len(response["items"]) == 2
    for api_key in response["items"]:
        assert "value" in api_key

    response = client.get_api_keys(includeValues=False)
    assert len(response["items"]) == 2
    for api_key in response["items"]:
        assert "value" not in api_key


@mock_apigateway
def test_create_api_key():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)

    apikey_value = "01234567890123456789"
    apikey_name = "TESTKEY1"
    payload = {"value": apikey_value, "name": apikey_name}

    response = client.create_api_key(**payload)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201
    assert response["name"] == apikey_name
    assert response["value"] == apikey_value
    assert response["enabled"] is False
    assert response["stageKeys"] == []

    response = client.get_api_keys()
    assert len(response["items"]) == 1


@mock_apigateway
def test_create_api_key_twice():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)

    apikey_value = "01234567890123456789"
    apikey_name = "TESTKEY1"
    payload = {"value": apikey_value, "name": apikey_name}

    client.create_api_key(**payload)
    with pytest.raises(ClientError) as ex:
        client.create_api_key(**payload)
    assert ex.value.response["Error"]["Code"] == "ConflictException"


@mock_apigateway
def test_api_keys():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)
    response = client.get_api_keys()
    assert len(response["items"]) == 0

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
    assert apikey["name"] == apikey_name
    assert apikey["value"] == apikey_value
    assert apikey["tags"]["tag1"] == "test_tag1"
    assert apikey["tags"]["tag2"] == "1"

    patch_operations = [
        {"op": "replace", "path": "/name", "value": "TESTKEY3_CHANGE"},
        {"op": "replace", "path": "/customerId", "value": "12345"},
        {"op": "replace", "path": "/description", "value": "APIKEY UPDATE TEST"},
        {"op": "replace", "path": "/enabled", "value": "false"},
    ]
    response = client.update_api_key(apiKey=apikey_id, patchOperations=patch_operations)
    assert response["name"] == "TESTKEY3_CHANGE"
    assert response["customerId"] == "12345"
    assert response["description"] == "APIKEY UPDATE TEST"
    assert response["enabled"] is False

    updated_api_key = client.get_api_key(apiKey=apikey_id)
    assert updated_api_key["name"] == "TESTKEY3_CHANGE"
    assert updated_api_key["customerId"] == "12345"
    assert updated_api_key["description"] == "APIKEY UPDATE TEST"
    assert updated_api_key["enabled"] is False

    response = client.get_api_keys()
    assert len(response["items"]) == 1

    payload = {"name": apikey_name}
    client.create_api_key(**payload)

    response = client.get_api_keys()
    assert len(response["items"]) == 2

    response = client.delete_api_key(apiKey=apikey_id)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 202

    response = client.get_api_keys()
    assert len(response["items"]) == 1


@mock_apigateway
def test_usage_plans():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)
    response = client.get_usage_plans()
    assert len(response["items"]) == 0

    # # Try to get info about a non existing usage
    with pytest.raises(ClientError) as ex:
        client.get_usage_plan(usagePlanId="not_existing")
    assert ex.value.response["Error"]["Code"] == "NotFoundException"
    assert ex.value.response["Error"]["Message"] == "Invalid Usage Plan ID specified"

    usage_plan_name = "TEST-PLAN"
    payload = {"name": usage_plan_name}
    response = client.create_usage_plan(**payload)
    usage_plan = client.get_usage_plan(usagePlanId=response["id"])
    assert usage_plan["name"] == usage_plan_name
    assert usage_plan["apiStages"] == []

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
        assert usage_plan[key] == value

    # Status code should be 200
    assert usage_plan["ResponseMetadata"]["HTTPStatusCode"] == 200

    # An Id should've been generated
    assert usage_plan["id"]

    response = client.get_usage_plans()
    assert len(response["items"]) == 2

    client.delete_usage_plan(usagePlanId=usage_plan_id)

    response = client.get_usage_plans()
    assert len(response["items"]) == 1


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
    assert response["quota"]["limit"] == 1000
    assert response["quota"]["period"] == "MONTH"
    assert response["name"] == "new-name"
    assert response["description"] == "new-description"
    assert response["productCode"] == "new-productionCode"


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
    assert len(response["items"]) == 0

    # Create usage plan key
    key_type = "API_KEY"
    payload = {"usagePlanId": usage_plan_id, "keyId": key_id, "keyType": key_type}
    response = client.create_usage_plan_key(**payload)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201
    usage_plan_key_id = response["id"]

    # Get current plan keys (expect 1)
    response = client.get_usage_plan_keys(usagePlanId=usage_plan_id)
    assert len(response["items"]) == 1

    # Get a single usage plan key and check it matches the created one
    usage_plan_key = client.get_usage_plan_key(
        usagePlanId=usage_plan_id, keyId=usage_plan_key_id
    )
    assert usage_plan_key["name"] == key_name
    assert usage_plan_key["id"] == key_id
    assert usage_plan_key["type"] == key_type
    assert usage_plan_key["value"] == key_value

    # Delete usage plan key
    client.delete_usage_plan_key(usagePlanId=usage_plan_id, keyId=key_id)

    # Get current plan keys (expect none)
    response = client.get_usage_plan_keys(usagePlanId=usage_plan_id)
    assert len(response["items"]) == 0

    # Try to get info about a non existing api key
    with pytest.raises(ClientError) as ex:
        client.get_usage_plan_key(usagePlanId=usage_plan_id, keyId="not_existing_key")
    err = ex.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid API Key identifier specified"

    # Try to get info about an existing api key that has not jet added to a valid usage plan
    with pytest.raises(ClientError) as ex:
        client.get_usage_plan_key(usagePlanId=usage_plan_id, keyId=key_id)
    err = ex.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid Usage Plan ID specified"

    # Try to get info about an existing api key that has not jet added to a valid usage plan
    with pytest.raises(ClientError) as ex:
        client.get_usage_plan_key(usagePlanId="not_existing_plan_id", keyId=key_id)
    err = ex.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid Usage Plan ID specified"


@mock_apigateway
def test_create_usage_plan_key_non_existent_api_key():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)
    usage_plan_id = "test"

    # Attempt to create a usage plan key for a API key that doesn't exists
    with pytest.raises(ClientError) as exc:
        client.create_usage_plan_key(
            usagePlanId=usage_plan_id, keyId="non-existent", keyType="API_KEY"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid API Key identifier specified"


@mock_apigateway
def test_get_usage_plans_using_key_id():
    region_name = "us-west-2"
    client = boto3.client("apigateway", region_name=region_name)

    # Create 2 Usage Plans
    # one will be attached to an API Key, the other will remain unattached
    attached_plan = client.create_usage_plan(name="Attached")
    client.create_usage_plan(name="Unattached")

    # Create an API key
    # to attach to the usage plan
    key_name = "test-api-key"
    response = client.create_api_key(name=key_name)
    key_id = response["id"]

    # Create a Usage Plan Key
    # Attached the Usage Plan and API Key
    key_type = "API_KEY"
    payload = {"usagePlanId": attached_plan["id"], "keyId": key_id, "keyType": key_type}
    client.create_usage_plan_key(**payload)

    # All usage plans should be returned when keyId is not included
    all_plans = client.get_usage_plans()
    assert len(all_plans["items"]) == 2

    # Only the usage plan attached to the given api key are included
    only_plans_with_key = client.get_usage_plans(keyId=key_id)
    assert len(only_plans_with_key["items"]) == 1
    assert only_plans_with_key["items"][0]["name"] == attached_plan["name"]
    assert only_plans_with_key["items"][0]["id"] == attached_plan["id"]


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
    err = ex.value.response["Error"]
    assert err["Message"] == "Invalid Response status code specified"
    assert err["Code"] == "NotFoundException"


@mock_apigateway
def test_get_api_key_unknown_apikey():
    client = boto3.client("apigateway", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.get_api_key(apiKey="unknown")
    err = ex.value.response["Error"]
    assert err["Message"] == "Invalid API Key identifier specified"
    assert err["Code"] == "NotFoundException"


@mock_apigateway
def test_get_domain_name_unknown_domainname():
    client = boto3.client("apigateway", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.get_domain_name(domainName="www.google.com")
    err = ex.value.response["Error"]
    assert err["Message"] == "Invalid domain name identifier specified"
    assert err["Code"] == "NotFoundException"


@mock_apigateway
def test_delete_domain_name_unknown_domainname():
    client = boto3.client("apigateway", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.delete_domain_name(domainName="www.google.com")
    err = ex.value.response["Error"]
    assert err["Message"] == "Invalid domain name identifier specified"
    assert err["Code"] == "NotFoundException"


@mock_apigateway
def test_create_base_path_mapping():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    client.create_domain_name(
        domainName=domain_name,
        certificateName="test.certificate",
        certificatePrivateKey="testPrivateKey",
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    stage_name = "dev"
    create_method_integration(client, api_id)
    client.create_deployment(
        restApiId=api_id, stageName=stage_name, description="1.0.1"
    )

    response = client.create_base_path_mapping(domainName=domain_name, restApiId=api_id)

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201
    assert response["basePath"] == "(none)"
    assert response["restApiId"] == api_id
    assert "stage" not in response

    response = client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id, stage=stage_name
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201
    assert response["basePath"] == "(none)"
    assert response["restApiId"] == api_id
    assert response["stage"] == stage_name

    response = client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id, stage=stage_name, basePath="v1"
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201
    assert response["basePath"] == "v1"
    assert response["restApiId"] == api_id
    assert response["stage"] == stage_name


@mock_apigateway
def test_create_base_path_mapping_with_unknown_api():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    client.create_domain_name(
        domainName=domain_name,
        certificateName="test.certificate",
        certificatePrivateKey="testPrivateKey",
    )

    with pytest.raises(ClientError) as ex:
        client.create_base_path_mapping(domainName=domain_name, restApiId="no")
    err = ex.value.response["Error"]
    assert err["Message"] == "Invalid REST API identifier specified"
    assert err["Code"] == "BadRequestException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_apigateway
def test_create_base_path_mapping_with_invalid_base_path():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    client.create_domain_name(
        domainName=domain_name,
        certificateName="test.certificate",
        certificatePrivateKey="testPrivateKey",
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    stage_name = "dev"
    create_method_integration(client, api_id)
    client.create_deployment(
        restApiId=api_id, stageName=stage_name, description="1.0.1"
    )

    with pytest.raises(ClientError) as ex:
        client.create_base_path_mapping(
            domainName=domain_name, restApiId=api_id, basePath="/v1"
        )
    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == "API Gateway V1 doesn't support the slash character (/) in base path mappings. To create a multi-level base path mapping, use API Gateway V2."
    )
    assert err["Code"] == "BadRequestException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_apigateway
def test_create_base_path_mapping_with_unknown_stage():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    client.create_domain_name(
        domainName=domain_name,
        certificateName="test.certificate",
        certificatePrivateKey="testPrivateKey",
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    stage_name = "dev"
    create_method_integration(client, api_id)
    client.create_deployment(
        restApiId=api_id, stageName=stage_name, description="1.0.1"
    )

    with pytest.raises(ClientError) as ex:
        client.create_base_path_mapping(
            domainName=domain_name, restApiId=api_id, stage="unknown-stage"
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "Invalid stage identifier specified"
    assert err["Code"] == "BadRequestException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_apigateway
def test_create_base_path_mapping_with_duplicate_base_path():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    client.create_domain_name(
        domainName=domain_name,
        certificateName="test.certificate",
        certificatePrivateKey="testPrivateKey",
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    base_path = "v1"
    client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id, basePath=base_path
    )
    with pytest.raises(ClientError) as ex:
        client.create_base_path_mapping(
            domainName=domain_name, restApiId=api_id, basePath=base_path
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "Base path already exists for this domain name"
    assert err["Code"] == "ConflictException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 409


@mock_apigateway
def test_get_base_path_mappings():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    client.create_domain_name(
        domainName=domain_name, certificateName=test_certificate_name
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    stage_name = "dev"
    create_method_integration(client, api_id)
    client.create_deployment(
        restApiId=api_id, stageName=stage_name, description="1.0.1"
    )

    client.create_base_path_mapping(domainName=domain_name, restApiId=api_id)
    client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id, basePath="v1"
    )
    client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id, basePath="v2", stage=stage_name
    )

    response = client.get_base_path_mappings(domainName=domain_name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    items = response["items"]

    assert items[0]["basePath"] == "(none)"
    assert items[0]["restApiId"] == api_id
    assert "stage" not in items[0]

    assert items[1]["basePath"] == "v1"
    assert items[1]["restApiId"] == api_id
    assert "stage" not in items[1]

    assert items[2]["basePath"] == "v2"
    assert items[2]["restApiId"] == api_id
    assert items[2]["stage"] == stage_name


@mock_apigateway
def test_get_base_path_mappings_with_unknown_domain():
    client = boto3.client("apigateway", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        client.get_base_path_mappings(domainName="unknown-domain")
    err = ex.value.response["Error"]
    assert err["Message"] == "Invalid domain name identifier specified"
    assert err["Code"] == "NotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


@mock_apigateway
def test_get_base_path_mapping():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    client.create_domain_name(
        domainName=domain_name, certificateName=test_certificate_name
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    stage_name = "dev"
    create_method_integration(client, api_id)
    client.create_deployment(
        restApiId=api_id, stageName=stage_name, description="1.0.1"
    )

    client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id, stage=stage_name
    )

    response = client.get_base_path_mapping(domainName=domain_name, basePath="(none)")
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["basePath"] == "(none)"
    assert response["restApiId"] == api_id
    assert response["stage"] == stage_name


@mock_apigateway
def test_get_base_path_mapping_with_unknown_domain():
    client = boto3.client("apigateway", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        client.get_base_path_mapping(domainName="unknown-domain", basePath="v1")

    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid domain name identifier specified"
    )
    assert ex.value.response["Error"]["Code"] == "NotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


@mock_apigateway
def test_get_base_path_mapping_with_unknown_base_path():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    client.create_domain_name(
        domainName=domain_name, certificateName=test_certificate_name
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id, basePath="v1"
    )

    with pytest.raises(ClientError) as ex:
        client.get_base_path_mapping(domainName=domain_name, basePath="unknown")

    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid base path mapping identifier specified"
    )
    assert ex.value.response["Error"]["Code"] == "NotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


@mock_apigateway
def test_delete_base_path_mapping():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    client.create_domain_name(
        domainName=domain_name, certificateName=test_certificate_name
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    base_path = "v1"
    client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id, basePath=base_path
    )

    client.get_base_path_mapping(domainName=domain_name, basePath=base_path)
    response = client.delete_base_path_mapping(
        domainName=domain_name, basePath=base_path
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 202

    with pytest.raises(ClientError) as ex:
        client.get_base_path_mapping(domainName=domain_name, basePath=base_path)

    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid base path mapping identifier specified"
    )
    assert ex.value.response["Error"]["Code"] == "NotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


@mock_apigateway
def test_delete_base_path_mapping_with_unknown_domain():
    client = boto3.client("apigateway", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        client.delete_base_path_mapping(domainName="unknown-domain", basePath="v1")

    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid domain name identifier specified"
    )
    assert ex.value.response["Error"]["Code"] == "NotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


@mock_apigateway
def test_delete_base_path_mapping_with_unknown_base_path():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    client.create_domain_name(
        domainName=domain_name, certificateName=test_certificate_name
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id, basePath="v1"
    )

    with pytest.raises(ClientError) as ex:
        client.delete_base_path_mapping(domainName=domain_name, basePath="unknown")

    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid base path mapping identifier specified"
    )
    assert ex.value.response["Error"]["Code"] == "NotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


@mock_apigateway
def test_update_path_mapping():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    client.create_domain_name(
        domainName=domain_name, certificateName=test_certificate_name
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]

    stage_name = "dev"

    client.create_base_path_mapping(domainName=domain_name, restApiId=api_id)

    response = client.create_rest_api(
        name="new_my_api", description="this is new my api"
    )
    new_api_id = response["id"]
    create_method_integration(client, new_api_id)
    client.create_deployment(
        restApiId=new_api_id, stageName=stage_name, description="1.0.1"
    )

    base_path = "v1"
    patch_operations = [
        {"op": "replace", "path": "/stage", "value": stage_name},
        {"op": "replace", "path": "/basePath", "value": base_path},
        {"op": "replace", "path": "/restapiId", "value": new_api_id},
    ]
    response = client.update_base_path_mapping(
        domainName=domain_name, basePath="(none)", patchOperations=patch_operations
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["basePath"] == base_path
    assert response["restApiId"] == new_api_id
    assert response["stage"] == stage_name


@mock_apigateway
def test_update_path_mapping_with_unknown_domain():
    client = boto3.client("apigateway", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        client.update_base_path_mapping(
            domainName="unknown-domain", basePath="(none)", patchOperations=[]
        )

    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid domain name identifier specified"
    )
    assert ex.value.response["Error"]["Code"] == "NotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


@mock_apigateway
def test_update_path_mapping_with_unknown_base_path():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    client.create_domain_name(
        domainName=domain_name, certificateName=test_certificate_name
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id, basePath="v1"
    )

    with pytest.raises(ClientError) as ex:
        client.update_base_path_mapping(
            domainName=domain_name, basePath="unknown", patchOperations=[]
        )

    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid base path mapping identifier specified"
    )
    assert ex.value.response["Error"]["Code"] == "NotFoundException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


@mock_apigateway
def test_update_path_mapping_to_same_base_path():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    client.create_domain_name(
        domainName=domain_name, certificateName=test_certificate_name
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id_1 = response["id"]
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id_2 = response["id"]

    client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id_1, basePath="v1"
    )
    client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id_2, basePath="v2"
    )

    response = client.get_base_path_mappings(domainName=domain_name)
    items = response["items"]
    assert len(items) == 2

    patch_operations = [
        {"op": "replace", "path": "/basePath", "value": "v2"},
    ]
    response = client.update_base_path_mapping(
        domainName=domain_name, basePath="v1", patchOperations=patch_operations
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["basePath"] == "v2"
    assert response["restApiId"] == api_id_1

    response = client.get_base_path_mappings(domainName=domain_name)
    items = response["items"]
    assert len(items) == 1
    assert items[0]["basePath"] == "v2"
    assert items[0]["restApiId"] == api_id_1
    assert "stage" not in items[0]


@mock_apigateway
def test_update_path_mapping_with_unknown_api():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    client.create_domain_name(
        domainName=domain_name, certificateName=test_certificate_name
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    base_path = "v1"
    client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id, basePath=base_path
    )

    with pytest.raises(ClientError) as ex:
        client.update_base_path_mapping(
            domainName=domain_name,
            basePath=base_path,
            patchOperations=[
                {"op": "replace", "path": "/restapiId", "value": "unknown"},
            ],
        )

    assert (
        ex.value.response["Error"]["Message"] == "Invalid REST API identifier specified"
    )
    assert ex.value.response["Error"]["Code"] == "BadRequestException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_apigateway
def test_update_path_mapping_with_unknown_stage():
    client = boto3.client("apigateway", region_name="us-west-2")
    domain_name = "testDomain"
    test_certificate_name = "test.certificate"
    client.create_domain_name(
        domainName=domain_name, certificateName=test_certificate_name
    )

    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    base_path = "v1"
    client.create_base_path_mapping(
        domainName=domain_name, restApiId=api_id, basePath=base_path
    )

    with pytest.raises(ClientError) as ex:
        client.update_base_path_mapping(
            domainName=domain_name,
            basePath=base_path,
            patchOperations=[{"op": "replace", "path": "/stage", "value": "unknown"}],
        )

    assert ex.value.response["Error"]["Message"] == "Invalid stage identifier specified"
    assert ex.value.response["Error"]["Code"] == "BadRequestException"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
