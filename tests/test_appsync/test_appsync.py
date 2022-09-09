import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_appsync
from moto.core import ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_appsync
def test_create_graphql_api():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    resp = client.create_graphql_api(name="api1", authenticationType="API_KEY")

    resp.should.have.key("graphqlApi")

    api = resp["graphqlApi"]
    api.should.have.key("name").equals("api1")
    api.should.have.key("apiId")
    api.should.have.key("authenticationType").equals("API_KEY")
    api.should.have.key("arn").equals(
        f"arn:aws:appsync:ap-southeast-1:{ACCOUNT_ID}:apis/{api['apiId']}"
    )
    api.should.have.key("uris").equals({"GRAPHQL": "http://graphql.uri"})
    api.should.have.key("xrayEnabled").equals(False)
    api.shouldnt.have.key("additionalAuthenticationProviders")
    api.shouldnt.have.key("logConfig")


@mock_appsync
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

    resp.should.have.key("graphqlApi")

    api = resp["graphqlApi"]
    api.should.have.key("name").equals("api1")
    api.should.have.key("apiId")
    api.should.have.key("authenticationType").equals("API_KEY")
    api.should.have.key("arn").equals(
        f"arn:aws:appsync:ap-southeast-1:{ACCOUNT_ID}:apis/{api['apiId']}"
    )
    api.should.have.key("uris").equals({"GRAPHQL": "http://graphql.uri"})
    api.should.have.key("additionalAuthenticationProviders").equals(
        [{"authenticationType": "API_KEY"}]
    )
    api.should.have.key("logConfig").equals(
        {"cloudWatchLogsRoleArn": "arn:aws:cloudwatch:role", "fieldLogLevel": "ERROR"}
    )
    api.should.have.key("xrayEnabled").equals(True)


@mock_appsync
def test_get_graphql_api():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    resp = client.get_graphql_api(apiId=api_id)
    resp.should.have.key("graphqlApi")

    api = resp["graphqlApi"]
    api.should.have.key("name").equals("api1")
    api.should.have.key("apiId")
    api.should.have.key("authenticationType").equals("API_KEY")


@mock_appsync
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

    graphql_api.should.have.key("name").equals("api2")
    graphql_api.should.have.key("authenticationType").equals("AWS_IAM")
    graphql_api.should.have.key("arn").equals(
        f"arn:aws:appsync:ap-southeast-1:{ACCOUNT_ID}:apis/{graphql_api['apiId']}"
    )
    graphql_api.should.have.key("logConfig").equals(
        {"cloudWatchLogsRoleArn": "arn:aws:cloudwatch:role", "fieldLogLevel": "ERROR"}
    )
    graphql_api.should.have.key("userPoolConfig").equals(
        {
            "awsRegion": "us-east-1",
            "defaultAction": "DENY",
            "userPoolId": "us-east-1_391729ed4a2d430a9d2abadecfc1ab86",
        }
    )
    graphql_api.should.have.key("xrayEnabled").equals(True)


@mock_appsync
def test_get_graphql_api_unknown():
    client = boto3.client("appsync", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_graphql_api(apiId="unknown")
    err = exc.value.response["Error"]

    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("GraphQL API unknown not found.")


@mock_appsync
def test_delete_graphql_api():
    client = boto3.client("appsync", region_name="eu-west-1")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    resp = client.list_graphql_apis()
    resp.should.have.key("graphqlApis").length_of(1)

    client.delete_graphql_api(apiId=api_id)

    resp = client.list_graphql_apis()
    resp.should.have.key("graphqlApis").length_of(0)


@mock_appsync
def test_list_graphql_apis():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    resp = client.list_graphql_apis()
    resp.should.have.key("graphqlApis").equals([])

    for _ in range(3):
        client.create_graphql_api(name="api1", authenticationType="API_KEY")

    resp = client.list_graphql_apis()
    resp.should.have.key("graphqlApis").length_of(3)
