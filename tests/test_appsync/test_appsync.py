import json
from datetime import datetime, timedelta
from unittest import SkipTest

import boto3
import pytest
import requests
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.core.utils import unix_time

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
    assert api["visibility"] == "GLOBAL"


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
        visibility="PRIVATE",
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
    assert api["visibility"] == "PRIVATE"


@mock_aws
def test_get_graphql_api():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    api_id = client.create_graphql_api(
        name="api1",
        authenticationType="API_KEY",
        tags={"key1": "value1", "key2": "value2"},
    )["graphqlApi"]["apiId"]

    resp = client.get_graphql_api(apiId=api_id)
    assert "graphqlApi" in resp

    api = resp["graphqlApi"]
    assert api["name"] == "api1"
    assert "apiId" in api
    assert api["authenticationType"] == "API_KEY"
    assert api["visibility"] == "GLOBAL"
    assert "tags" in api
    assert api["tags"] == {"key1": "value1", "key2": "value2"}


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
        client.create_graphql_api(
            name="api1", authenticationType="API_KEY", tags={"my_key": "value1"}
        )

    resp = client.list_graphql_apis()
    assert len(resp["graphqlApis"]) == 3
    assert "tags" in resp["graphqlApis"][0]
    assert resp["graphqlApis"][0]["tags"] == {"my_key": "value1"}


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


@mock_aws
def test_create_api():
    client = boto3.client("appsync", region_name="eu-west-1")
    resp = client.create_api(
        name="api1",
        eventConfig={
            "authProviders": [
                {"authType": "API_KEY"},
            ],
            "connectionAuthModes": [
                {"authType": "API_KEY"},
            ],
            "defaultPublishAuthModes": [
                {"authType": "API_KEY"},
            ],
            "defaultSubscribeAuthModes": [
                {"authType": "API_KEY"},
            ],
        },
    )

    assert "api" in resp
    api = resp["api"]
    assert api["name"] == "api1"
    assert "apiId" in api
    assert (
        api["apiArn"] == f"arn:aws:appsync:eu-west-1:{ACCOUNT_ID}:apis/{api['apiId']}"
    )
    assert "dns" in api
    assert "REALTIME" in api["dns"]
    assert "HTTP" in api["dns"]
    assert api["dns"]["REALTIME"].endswith(
        ".appsync-realtime-api.eu-west-1.amazonaws.com"
    )
    assert api["dns"]["HTTP"].endswith(".appsync-api.eu-west-1.amazonaws.com")
    assert "created" in api
    assert api["eventConfig"]["authProviders"][0]["authType"] == "API_KEY"
    assert api["tags"] == {}


@mock_aws
def test_create_api_with_all_params():
    client = boto3.client("appsync", region_name="us-east-2")

    event_config = {
        "authProviders": [
            {
                "authType": "AWS_IAM",
            },
        ],
        "connectionAuthModes": [{"authType": "AWS_IAM"}],
        "defaultPublishAuthModes": [{"authType": "AWS_IAM"}],
        "defaultSubscribeAuthModes": [{"authType": "API_KEY"}],
        "logConfig": {
            "logLevel": "ALL",
            "cloudWatchLogsRoleArn": "arn:aws:iam::123456789012:role/MyRole",
        },
    }

    resp = client.create_api(
        name="MyEventsAPI",
        ownerContact="owner@example.com",
        tags={"key1": "value1", "key2": "value2"},
        eventConfig=event_config,
    )

    api = resp["api"]

    assert api["name"] == "MyEventsAPI"
    assert api["ownerContact"] == "owner@example.com"
    assert api["tags"] == {"key1": "value1", "key2": "value2"}
    assert api["eventConfig"] == event_config
    assert api["eventConfig"]["authProviders"][0]["authType"] == "AWS_IAM"
    assert api["eventConfig"]["defaultPublishAuthModes"][0]["authType"] == "AWS_IAM"
    assert api["eventConfig"]["defaultSubscribeAuthModes"][0]["authType"] == "API_KEY"
    assert api["eventConfig"]["logConfig"]["logLevel"] == "ALL"


@mock_aws
def test_delete_api():
    client = boto3.client("appsync", region_name="ap-southeast-1")

    resp = client.create_api(
        name="api1",
        eventConfig={
            "authProviders": [
                {"authType": "API_KEY"},
            ],
            "connectionAuthModes": [
                {"authType": "API_KEY"},
            ],
            "defaultPublishAuthModes": [
                {"authType": "API_KEY"},
            ],
            "defaultSubscribeAuthModes": [
                {"authType": "API_KEY"},
            ],
        },
    )
    api_id = resp["api"]["apiId"]

    resp = client.list_apis()
    assert len(resp["apis"]) == 1

    client.delete_api(apiId=api_id)

    resp = client.list_apis()
    assert len(resp["apis"]) == 0


@mock_aws
def test_create_channel_namespace():
    client = boto3.client("appsync", region_name="us-east-2")
    resp = client.create_api(
        name="api1",
        eventConfig={
            "authProviders": [
                {"authType": "API_KEY"},
            ],
            "connectionAuthModes": [
                {"authType": "API_KEY"},
            ],
            "defaultPublishAuthModes": [
                {"authType": "API_KEY"},
            ],
            "defaultSubscribeAuthModes": [
                {"authType": "API_KEY"},
            ],
        },
    )
    api_id = resp["api"]["apiId"]

    channel_response = client.create_channel_namespace(
        apiId=api_id,
        name="testChannel",
        subscribeAuthModes=[{"authType": "API_KEY"}],
        publishAuthModes=[{"authType": "API_KEY"}],
        tags={"key1": "value1", "key2": "value2"},
        handlerConfigs={},
    )

    assert "channelNamespace" in channel_response

    channel = channel_response["channelNamespace"]
    assert channel["apiId"] == api_id
    assert channel["name"] == "testChannel"
    assert channel["subscribeAuthModes"] == [{"authType": "API_KEY"}]
    assert channel["publishAuthModes"] == [{"authType": "API_KEY"}]
    assert channel["tags"] == {"key1": "value1", "key2": "value2"}
    assert "channelNamespaceArn" in channel
    assert channel["channelNamespaceArn"].endswith(
        f":apis/{api_id}/channelNamespace/testChannel"
    )
    assert "created" in channel
    assert "lastModified" in channel
    assert "handlerConfigs" in channel


@mock_aws
def test_delete_channel_namespace():
    client = boto3.client("appsync", region_name="us-east-2")
    resp = client.create_api(
        name="api1",
        eventConfig={
            "authProviders": [
                {"authType": "API_KEY"},
            ],
            "connectionAuthModes": [
                {"authType": "API_KEY"},
            ],
            "defaultPublishAuthModes": [
                {"authType": "API_KEY"},
            ],
            "defaultSubscribeAuthModes": [
                {"authType": "API_KEY"},
            ],
        },
    )
    api_id = resp["api"]["apiId"]

    resp = client.create_channel_namespace(
        apiId=api_id,
        name="testChannel",
        subscribeAuthModes=[{"authType": "API_KEY"}],
        publishAuthModes=[{"authType": "API_KEY"}],
    )

    assert len(client.list_channel_namespaces(apiId=api_id)["channelNamespaces"]) == 1

    client.delete_channel_namespace(apiId=api_id, name="testChannel")

    assert len(client.list_channel_namespaces(apiId=api_id)["channelNamespaces"]) == 0


@mock_aws
def test_get_api():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    api_id = client.create_api(
        name="api1",
        eventConfig={
            "authProviders": [{"authType": "API_KEY"}],
            "connectionAuthModes": [{"authType": "API_KEY"}],
            "defaultPublishAuthModes": [{"authType": "API_KEY"}],
            "defaultSubscribeAuthModes": [{"authType": "API_KEY"}],
        },
    )["api"]["apiId"]

    resp = client.get_api(apiId=api_id)
    assert "api" in resp
    api = resp["api"]
    assert api["name"] == "api1"
    assert api["apiId"] == api_id


@mock_aws
def test_events_api_direct_http_request_e2e():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only test this flow in DecoratorMode")
    client = boto3.client("appsync", region_name="us-east-1")
    api_resp = client.create_api(
        name="events-api",
        eventConfig={
            "authProviders": [
                {"authType": "API_KEY"},
            ],
            "connectionAuthModes": [
                {"authType": "API_KEY"},
            ],
            "defaultPublishAuthModes": [
                {"authType": "API_KEY"},
            ],
            "defaultSubscribeAuthModes": [
                {"authType": "API_KEY"},
            ],
        },
    )
    api_id = api_resp["api"]["apiId"]
    api_http_url = api_resp["api"]["dns"]["HTTP"]

    channel_name = "test-channel"
    client.create_channel_namespace(
        apiId=api_id,
        name=channel_name,
        subscribeAuthModes=[{"authType": "API_KEY"}],
        publishAuthModes=[{"authType": "API_KEY"}],
    )

    three_days_ahead = datetime.now() + timedelta(days=3)
    three_days_ahead_in_secs = int(unix_time(three_days_ahead))
    key_resp = client.create_api_key(
        apiId=api_id, description="test api key", expires=three_days_ahead_in_secs
    )
    api_key = key_resp["apiKey"]["id"]

    foo_content = "test-foo-123"
    bar_content = "test-bar-456"
    event_payload = {
        "channel": channel_name,
        "events": [json.dumps({"foo": foo_content, "bar": bar_content}, default=str)],
    }

    endpoint_url = f"https://{api_http_url}/event"

    response = requests.post(
        endpoint_url,
        headers={"Content-Type": "application/json", "x-api-key": api_key},
        json=event_payload,
        timeout=10,
    )
    assert response.status_code == 200
    assert response.json()["failed"] == []
    assert len(response.json()["successful"]) == 1

    get_api_resp = client.get_api(apiId=api_id)
    assert get_api_resp["api"]["apiId"] == api_id
    assert get_api_resp["api"]["dns"]["HTTP"] == api_http_url

    list_channels_resp = client.list_channel_namespaces(apiId=api_id)
    assert len(list_channels_resp["channelNamespaces"]) == 1
    assert list_channels_resp["channelNamespaces"][0]["name"] == channel_name

    list_keys_resp = client.list_api_keys(apiId=api_id)
    assert len(list_keys_resp["apiKeys"]) == 1
    assert list_keys_resp["apiKeys"][0]["id"] == api_key


@mock_aws
def test_create_channel_namespace_invalid_name():
    client = boto3.client("appsync", region_name="us-east-2")
    resp = client.create_api(
        name="api1",
        eventConfig={
            "authProviders": [
                {"authType": "API_KEY"},
            ],
            "connectionAuthModes": [
                {"authType": "API_KEY"},
            ],
            "defaultPublishAuthModes": [
                {"authType": "API_KEY"},
            ],
            "defaultSubscribeAuthModes": [
                {"authType": "API_KEY"},
            ],
        },
    )
    api_id = resp["api"]["apiId"]

    with pytest.raises(ClientError) as exc:
        client.create_channel_namespace(
            apiId=api_id,
            name="test-channel/",
            subscribeAuthModes=[{"authType": "API_KEY"}],
            publishAuthModes=[{"authType": "API_KEY"}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "1 validation error detected" in err["Message"]
    assert "Value at 'name' failed to satisfy constraint" in err["Message"]
    assert "Member must satisfy regular expression pattern" in err["Message"]

    with pytest.raises(ClientError) as exc:
        client.create_channel_namespace(
            apiId=api_id,
            name="-test-channel",
            subscribeAuthModes=[{"authType": "API_KEY"}],
            publishAuthModes=[{"authType": "API_KEY"}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"

    with pytest.raises(ClientError) as exc:
        client.create_channel_namespace(
            apiId=api_id,
            name="test-channel-",
            subscribeAuthModes=[{"authType": "API_KEY"}],
            publishAuthModes=[{"authType": "API_KEY"}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"


@mock_aws
def test_create_api_invalid_name():
    client = boto3.client("appsync", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.create_api(
            name="invalid/api",
            eventConfig={
                "authProviders": [{"authType": "API_KEY"}],
                "connectionAuthModes": [{"authType": "API_KEY"}],
                "defaultPublishAuthModes": [{"authType": "API_KEY"}],
                "defaultSubscribeAuthModes": [{"authType": "API_KEY"}],
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"

    with pytest.raises(ClientError) as exc:
        client.create_api(
            name="invalid@api",
            eventConfig={
                "authProviders": [{"authType": "API_KEY"}],
                "connectionAuthModes": [{"authType": "API_KEY"}],
                "defaultPublishAuthModes": [{"authType": "API_KEY"}],
                "defaultSubscribeAuthModes": [{"authType": "API_KEY"}],
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
