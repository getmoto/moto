import json
from unittest import SkipTest

import boto3
import requests

from moto import mock_aws, settings
from moto.core.models import responses_mock


@mock_aws
def test_http_integration():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Cannot test mock of execute-api.apigateway in ServerMode")
    responses_mock.add(
        responses_mock.GET, "http://httpbin.org/robots.txt", body="a fake response"
    )
    registered = responses_mock.registered()
    assert isinstance(registered, list) and len(registered) > 1
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
        requestParameters={"integration.request.header.X-Custom": "'Custom'"},
    )

    stage_name = "staging"
    client.create_deployment(restApiId=api_id, stageName=stage_name)

    deploy_url = (
        f"https://{api_id}.execute-api.{region_name}.amazonaws.com/{stage_name}"
    )

    assert requests.get(deploy_url).content == b"a fake response"


@mock_aws
def test_aws_integration_dynamodb():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Cannot test mock of execute-api.apigateway in ServerMode")

    client = boto3.client("apigateway", region_name="us-west-2")
    dynamodb = boto3.client("dynamodb", region_name="us-west-2")
    table_name = "test_1"
    integration_action = "arn:aws:apigateway:us-west-2:dynamodb:action/PutItem"
    stage_name = "staging"

    create_table(dynamodb, table_name)
    api_id, _ = create_integration_test_api(client, integration_action)

    client.create_deployment(restApiId=api_id, stageName=stage_name)

    res = requests.put(
        f"https://{api_id}.execute-api.us-west-2.amazonaws.com/{stage_name}",
        json={"TableName": table_name, "Item": {"name": {"S": "the-key"}}},
    )
    assert res.status_code == 200
    assert res.content == b"{}"


@mock_aws
def test_aws_integration_dynamodb_multiple_stages():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Cannot test mock of execute-api.apigateway in ServerMode")

    client = boto3.client("apigateway", region_name="us-west-2")
    dynamodb = boto3.client("dynamodb", region_name="us-west-2")
    table_name = "test_1"
    integration_action = "arn:aws:apigateway:us-west-2:dynamodb:action/PutItem"

    create_table(dynamodb, table_name)
    api_id, _ = create_integration_test_api(client, integration_action)

    client.create_deployment(restApiId=api_id, stageName="dev")
    client.create_deployment(restApiId=api_id, stageName="staging")

    res = requests.put(
        f"https://{api_id}.execute-api.us-west-2.amazonaws.com/dev",
        json={"TableName": table_name, "Item": {"name": {"S": "the-key"}}},
    )
    assert res.status_code == 200

    res = requests.put(
        f"https://{api_id}.execute-api.us-west-2.amazonaws.com/staging",
        json={"TableName": table_name, "Item": {"name": {"S": "the-key"}}},
    )
    assert res.status_code == 200

    # We haven't pushed to prod yet
    res = requests.put(
        f"https://{api_id}.execute-api.us-west-2.amazonaws.com/prod",
        json={"TableName": table_name, "Item": {"name": {"S": "the-key"}}},
    )
    assert res.status_code == 400


@mock_aws
def test_aws_integration_dynamodb_multiple_resources():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Cannot test mock of execute-api.apigateway in ServerMode")

    client = boto3.client("apigateway", region_name="us-west-2")
    dynamodb = boto3.client("dynamodb", region_name="us-west-2")
    table_name = "test_1"
    create_table(dynamodb, table_name)

    # Create API integration to PutItem
    integration_action = "arn:aws:apigateway:us-west-2:dynamodb:action/PutItem"
    api_id, root_id = create_integration_test_api(client, integration_action)

    # Create API integration to GetItem
    res = client.create_resource(restApiId=api_id, parentId=root_id, pathPart="item")
    parent_id = res["id"]
    integration_action = "arn:aws:apigateway:us-west-2:dynamodb:action/GetItem"
    api_id, root_id = create_integration_test_api(
        client,
        integration_action,
        api_id=api_id,
        parent_id=parent_id,
        http_method="GET",
    )

    client.create_deployment(restApiId=api_id, stageName="dev")

    # Put item at the root resource
    res = requests.put(
        f"https://{api_id}.execute-api.us-west-2.amazonaws.com/dev",
        json={
            "TableName": table_name,
            "Item": {"name": {"S": "the-key"}, "attr2": {"S": "sth"}},
        },
    )
    assert res.status_code == 200

    # Get item from child resource
    res = requests.get(
        f"https://{api_id}.execute-api.us-west-2.amazonaws.com/dev/item",
        json={"TableName": table_name, "Key": {"name": {"S": "the-key"}}},
    )
    assert res.status_code == 200
    assert json.loads(res.content) == {
        "Item": {"name": {"S": "the-key"}, "attr2": {"S": "sth"}}
    }


@mock_aws
def test_aws_integration_sagemaker():
    region = "us-west-2"
    client = boto3.client("apigateway", region_name=region)
    sagemaker_endpoint = "non-existing"
    integration_action = f"arn:aws:apigateway:{region}:runtime.sagemaker:path//endpoints/{sagemaker_endpoint}/invocations"

    api_id, resource_id = create_integration_test_api(client, integration_action)

    # We can't invoke Sagemaker
    # Just verify that the integration action was successful
    response = client.get_integration(
        restApiId=api_id, resourceId=resource_id, httpMethod="PUT"
    )
    assert response["uri"] == integration_action


def create_table(dynamodb, table_name):
    # Create DynamoDB table
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "name", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )


def create_integration_test_api(
    client, integration_action, api_id=None, parent_id=None, http_method="PUT"
):
    if not api_id:
        # We do not have a root yet - create the API first
        response = client.create_rest_api(name="my_api", description="this is my api")
        api_id = response["id"]
    if not parent_id:
        resources = client.get_resources(restApiId=api_id)
        parent_id = [
            resource for resource in resources["items"] if resource["path"] == "/"
        ][0]["id"]

    client.put_method(
        restApiId=api_id,
        resourceId=parent_id,
        httpMethod=http_method,
        authorizationType="NONE",
    )
    client.put_method_response(
        restApiId=api_id, resourceId=parent_id, httpMethod=http_method, statusCode="200"
    )
    client.put_integration(
        restApiId=api_id,
        resourceId=parent_id,
        httpMethod=http_method,
        type="AWS",
        uri=integration_action,
        integrationHttpMethod=http_method,
    )
    client.put_integration_response(
        restApiId=api_id,
        resourceId=parent_id,
        httpMethod=http_method,
        statusCode="200",
        selectionPattern="",
        responseTemplates={"application/json": "{}"},
    )
    return api_id, parent_id
