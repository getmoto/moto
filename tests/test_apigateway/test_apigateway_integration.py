import boto3
import requests

from moto import mock_apigateway, mock_dynamodb2


@mock_apigateway
def test_http_integration():
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
@mock_dynamodb2
def test_aws_integration_dynamodb():
    client = boto3.client("apigateway", region_name="us-west-2")
    response = client.create_rest_api(name="my_api", description="this is my api")
    api_id = response["id"]
    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][
        0
    ]["id"]

    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="PUT", authorizationType="NONE"
    )

    client.put_method_response(
        restApiId=api_id, resourceId=root_id, httpMethod="PUT", statusCode="200",
    )

    # Create DynamoDB table
    dynamodb = boto3.client("dynamodb", region_name="us-west-2")
    dynamodb.create_table(
        TableName="test_1",
        KeySchema=[{"AttributeName": "name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "name", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # Ensure that it works fine when providing the integrationHttpMethod-argument
    result = client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="PUT",
        type="AWS",
        uri="arn:aws:apigateway:us-west-2:dynamodb:action/PutItem",
        integrationHttpMethod="PUT",
    )

    client.put_integration_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod="PUT",
        statusCode="200",
        selectionPattern="",
        responseTemplates={"application/json": "{}"})

    client.create_deployment(restApiId=api_id, stageName="staging")

    res = requests.put(
        "https://{}.execute-api.us-west-2.amazonaws.com/staging".format(api_id),
        json={"TableName": "test_1", "Item": {"name": {"S": "the-key"}}},
    )
    res.status_code.should.equal(200)
    res.content.should.equal(b"{}")

# TODO: create different stage, verify both stages work
# TODO: add different resource (with path), verify it works
# TODO: verify base_path can be set
# TODO: remove integration, verify it can no longer be reached
