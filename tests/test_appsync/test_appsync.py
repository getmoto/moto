import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_graphql_api():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    resp = client.create_graphql_api(name="api1", authenticationType="API_KEY")

    assert "graphqlApi" in resp

    api = resp["graphqlApi"]
    assert api["name"] == "api1"
    assert "apiId" in api
    assert api["authenticationType"] == "API_KEY"
    assert (
        api["arn"] == f"arn:aws:appsync:ap-southeast-1:{ACCOUNT_ID}:apis/{api['apiId']}"
    )
    assert api["uris"] == {"GRAPHQL": "http://graphql.uri"}
    assert api["xrayEnabled"] is False
    assert "additionalAuthenticationProviders" not in api
    assert "logConfig" not in api


@mock_aws
def test_create_graphql_api_advanced():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    resp = client.create_graphql_api(
        name="api1",
        authenticationType="API_KEY",
        additionalAuthenticationProviders=[{"authenticationType": "API_KEY"}],
        logConfig={
            "fieldLogLevel": "ERROR",
            "cloudWatchLogsRoleArn": "arn:aws:cloudwatch:role",
        },
        xrayEnabled=True,
    )

    assert "graphqlApi" in resp

    api = resp["graphqlApi"]
    assert api["name"] == "api1"
    assert "apiId" in api
    assert api["authenticationType"] == "API_KEY"
    assert (
        api["arn"] == f"arn:aws:appsync:ap-southeast-1:{ACCOUNT_ID}:apis/{api['apiId']}"
    )
    assert api["uris"] == {"GRAPHQL": "http://graphql.uri"}
    assert api["additionalAuthenticationProviders"] == [
        {"authenticationType": "API_KEY"}
    ]
    assert api["logConfig"] == {
        "cloudWatchLogsRoleArn": "arn:aws:cloudwatch:role",
        "fieldLogLevel": "ERROR",
    }
    assert api["xrayEnabled"] is True


@mock_aws
def test_get_graphql_api():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    resp = client.get_graphql_api(apiId=api_id)
    assert "graphqlApi" in resp

    api = resp["graphqlApi"]
    assert api["name"] == "api1"
    assert "apiId" in api
    assert api["authenticationType"] == "API_KEY"


@mock_aws
def test_update_graphql_api():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.update_graphql_api(
        apiId=api_id,
        name="api2",
        authenticationType="AWS_IAM",
        logConfig={
            "cloudWatchLogsRoleArn": "arn:aws:cloudwatch:role",
            "fieldLogLevel": "ERROR",
        },
        userPoolConfig={
            "awsRegion": "us-east-1",
            "defaultAction": "DENY",
            "userPoolId": "us-east-1_391729ed4a2d430a9d2abadecfc1ab86",
        },
        xrayEnabled=True,
    )

    graphql_api = client.get_graphql_api(apiId=api_id)["graphqlApi"]

    assert graphql_api["name"] == "api2"
    assert graphql_api["authenticationType"] == "AWS_IAM"
    assert (
        graphql_api["arn"]
        == f"arn:aws:appsync:ap-southeast-1:{ACCOUNT_ID}:apis/{graphql_api['apiId']}"
    )
    assert graphql_api["logConfig"] == {
        "cloudWatchLogsRoleArn": "arn:aws:cloudwatch:role",
        "fieldLogLevel": "ERROR",
    }
    assert graphql_api["userPoolConfig"] == {
        "awsRegion": "us-east-1",
        "defaultAction": "DENY",
        "userPoolId": "us-east-1_391729ed4a2d430a9d2abadecfc1ab86",
    }
    assert graphql_api["xrayEnabled"] is True


@mock_aws
def test_get_graphql_api_unknown():
    client = boto3.client("appsync", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_graphql_api(apiId="unknown")
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "GraphQL API unknown not found."


@mock_aws
def test_delete_graphql_api():
    client = boto3.client("appsync", region_name="eu-west-1")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    resp = client.list_graphql_apis()
    assert len(resp["graphqlApis"]) == 1

    client.delete_graphql_api(apiId=api_id)

    resp = client.list_graphql_apis()
    assert len(resp["graphqlApis"]) == 0


@mock_aws
def test_list_graphql_apis():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    resp = client.list_graphql_apis()
    assert resp["graphqlApis"] == []

    for _ in range(3):
        client.create_graphql_api(name="api1", authenticationType="API_KEY")

    resp = client.list_graphql_apis()
    assert len(resp["graphqlApis"]) == 3
