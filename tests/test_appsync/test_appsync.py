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


@mock_aws
def test_get_api_cache():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.create_api_cache(
        apiId=api_id,
        ttl=300,
        apiCachingBehavior="FULL_REQUEST_CACHING",
        type="T2_SMALL",
        transitEncryptionEnabled=False,
        atRestEncryptionEnabled=False,
        healthMetricsConfig="DISABLED",
    )

    cache = client.get_api_cache(apiId=api_id)["apiCache"]

    assert cache["ttl"] == 300
    assert cache["apiCachingBehavior"] == "FULL_REQUEST_CACHING"
    assert cache["transitEncryptionEnabled"] is False
    assert cache["atRestEncryptionEnabled"] is False
    assert cache["type"] == "T2_SMALL"
    assert cache["status"] == "AVAILABLE"
    assert cache["healthMetricsConfig"] == "DISABLED"


@mock_aws
def test_get_api_cache_error():
    client = boto3.client("appsync", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_api_cache(apiId="unknown")
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "GraphQL API unknown not found."

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    with pytest.raises(ClientError) as exc:
        client.get_api_cache(apiId=api_id)
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert err["Message"] == (
        "Unable to get the cache as it doesn't exist, please create the cache first."
    )


@mock_aws
def test_delete_api_cache():
    client = boto3.client("appsync", region_name="eu-west-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.create_api_cache(
        apiId=api_id,
        ttl=300,
        apiCachingBehavior="FULL_REQUEST_CACHING",
        type="T2_SMALL",
    )

    client.delete_api_cache(apiId=api_id)

    with pytest.raises(ClientError) as exc:
        client.get_api_cache(apiId=api_id)
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert err["Message"] == (
        "Unable to get the cache as it doesn't exist, please create the cache first."
    )


@mock_aws
def test_delete_api_cache_error():
    client = boto3.client("appsync", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.delete_api_cache(apiId="unknown")
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "GraphQL API unknown not found."

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    with pytest.raises(ClientError) as exc:
        client.delete_api_cache(apiId=api_id)
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert err["Message"] == (
        "Unable to delete the cache as it doesn't exist, please create the cache first."
    )


@mock_aws
def test_create_api_cache():
    client = boto3.client("appsync", region_name="eu-west-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    cache = client.create_api_cache(
        apiId=api_id,
        ttl=300,
        apiCachingBehavior="FULL_REQUEST_CACHING",
        type="T2_SMALL",
    )["apiCache"]

    assert cache["ttl"] == 300
    assert cache["apiCachingBehavior"] == "FULL_REQUEST_CACHING"
    assert cache["transitEncryptionEnabled"] is False
    assert cache["atRestEncryptionEnabled"] is False
    assert cache["type"] == "T2_SMALL"
    assert cache["status"] == "AVAILABLE"
    assert cache["healthMetricsConfig"] == "DISABLED"


@mock_aws
def test_create_api_cache_advanced():
    client = boto3.client("appsync", region_name="eu-west-1")
    api_id = client.create_graphql_api(name="api2", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]
    cache = client.create_api_cache(
        apiId=api_id,
        ttl=500,
        apiCachingBehavior="PER_RESOLVER_CACHING",
        type="R4_4XLARGE",
        transitEncryptionEnabled=True,
        atRestEncryptionEnabled=True,
        healthMetricsConfig="ENABLED",
    )["apiCache"]
    assert cache["ttl"] == 500
    assert cache["apiCachingBehavior"] == "PER_RESOLVER_CACHING"
    assert cache["transitEncryptionEnabled"] is True
    assert cache["atRestEncryptionEnabled"] is True
    assert cache["type"] == "R4_4XLARGE"
    assert cache["status"] == "AVAILABLE"
    assert cache["healthMetricsConfig"] == "ENABLED"


@mock_aws
def test_create_api_cache_error():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.create_api_cache(
            apiId="unknown",
            ttl=100,
            apiCachingBehavior="FULL_REQUEST_CACHING",
            type="SMALL",
        )
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "GraphQL API unknown not found."

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.create_api_cache(
        apiId=api_id,
        ttl=300,
        apiCachingBehavior="FULL_REQUEST_CACHING",
        type="T2_SMALL",
    )
    with pytest.raises(ClientError) as exc:
        client.create_api_cache(
            apiId=api_id,
            ttl=100,
            apiCachingBehavior="FULL_REQUEST_CACHING",
            type="SMALL",
        )
    err = exc.value.response["Error"]

    assert err["Code"] == "BadRequestException"
    assert err["Message"] == "The API has already enabled caching."


@mock_aws
def test_update_api_cache():
    client = boto3.client("appsync", region_name="eu-west-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.create_api_cache(
        apiId=api_id,
        ttl=300,
        apiCachingBehavior="FULL_REQUEST_CACHING",
        type="T2_SMALL",
    )["apiCache"]

    cache = client.update_api_cache(
        apiId=api_id,
        ttl=500,
        apiCachingBehavior="PER_RESOLVER_CACHING",
        type="R4_4XLARGE",
    )["apiCache"]
    assert cache["ttl"] == 500
    assert cache["apiCachingBehavior"] == "PER_RESOLVER_CACHING"
    assert cache["transitEncryptionEnabled"] is False
    assert cache["atRestEncryptionEnabled"] is False
    assert cache["type"] == "R4_4XLARGE"
    assert cache["status"] == "AVAILABLE"
    assert cache["healthMetricsConfig"] == "DISABLED"

    cache = client.update_api_cache(
        apiId=api_id,
        ttl=300,
        apiCachingBehavior="FULL_REQUEST_CACHING",
        type="SMALL",
        healthMetricsConfig="ENABLED",
    )["apiCache"]

    assert cache["healthMetricsConfig"] == "ENABLED"


@mock_aws
def test_update_api_cache_error():
    client = boto3.client("appsync", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.update_api_cache(
            apiId="unknown",
            ttl=100,
            apiCachingBehavior="FULL_REQUEST_CACHING",
            type="SMALL",
        )
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "GraphQL API unknown not found."

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    with pytest.raises(ClientError) as exc:
        client.update_api_cache(
            apiId=api_id,
            ttl=100,
            apiCachingBehavior="FULL_REQUEST_CACHING",
            type="SMALL",
        )
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert (
        err["Message"]
        == "Unable to update the cache as it doesn't exist, please create the cache first."
    )


@mock_aws
def test_flush_api_cache():
    client = boto3.client("appsync", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.flush_api_cache(apiId="unknown")
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "GraphQL API unknown not found."

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    with pytest.raises(ClientError) as exc:
        client.flush_api_cache(apiId=api_id)
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert (
        err["Message"]
        == "Unable to flush the cache as it doesn't exist, please create the cache first."
    )

    client.create_api_cache(
        apiId=api_id,
        ttl=300,
        apiCachingBehavior="FULL_REQUEST_CACHING",
        type="T2_SMALL",
    )["apiCache"]
    client.flush_api_cache(apiId=api_id)
