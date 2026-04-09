from datetime import datetime, timedelta

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core.utils import unix_time


@mock_aws
def test_create_api_key_simple():
    client = boto3.client("appsync", region_name="eu-west-1")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]
    resp = client.create_api_key(apiId=api_id)

    assert "apiKey" in resp
    api_key = resp["apiKey"]

    assert "id" in api_key
    assert "description" not in api_key
    assert "expires" in api_key
    assert "deletes" in api_key


@mock_aws
def test_create_api_key():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    two_days_ahead = datetime.now() + timedelta(days=2)
    two_days_ahead_in_secs = int(unix_time(two_days_ahead))

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]
    resp = client.create_api_key(
        apiId=api_id, description="my first api key", expires=two_days_ahead_in_secs
    )

    assert "apiKey" in resp
    api_key = resp["apiKey"]

    assert "id" in api_key
    assert api_key["description"] == "my first api key"
    assert api_key["expires"] == two_days_ahead_in_secs
    assert api_key["deletes"] == two_days_ahead_in_secs


@mock_aws
def test_delete_api_key():
    client = boto3.client("appsync", region_name="us-east-1")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]
    api_key_id = client.create_api_key(apiId=api_id)["apiKey"]["id"]

    client.delete_api_key(apiId=api_id, id=api_key_id)

    resp = client.list_api_keys(apiId=api_id)
    assert len(resp["apiKeys"]) == 0


@mock_aws
def test_list_api_keys_unknown_api():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    resp = client.list_api_keys(apiId="unknown")
    assert resp["apiKeys"] == []


@mock_aws
def test_list_api_keys_empty():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    resp = client.list_api_keys(apiId=api_id)
    assert resp["apiKeys"] == []


@mock_aws
def test_list_api_keys():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]
    client.create_api_key(apiId=api_id)
    client.create_api_key(apiId=api_id, description="my first api key")
    resp = client.list_api_keys(apiId=api_id)
    assert len(resp["apiKeys"]) == 2


@mock_aws
def test_update_api_key():
    client = boto3.client("appsync", region_name="eu-west-1")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    original = client.create_api_key(apiId=api_id, description="my first api key")[
        "apiKey"
    ]

    updated = client.update_api_key(
        apiId=api_id, id=original["id"], description="my second api key"
    )["apiKey"]

    assert updated["id"] == original["id"]
    assert updated["description"] == "my second api key"
    assert updated["expires"] == original["expires"]
    assert updated["deletes"] == original["deletes"]


@mock_aws
def test_create_api_key_invalid_expiration():
    client = boto3.client("appsync", region_name="us-east-1")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    twelve_hours_ahead = datetime.now() + timedelta(hours=12)
    twelve_hours_ahead_in_secs = int(unix_time(twelve_hours_ahead))

    with pytest.raises(ClientError) as exc:
        client.create_api_key(
            apiId=api_id,
            description="invalid api key",
            expires=twelve_hours_ahead_in_secs,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ApiKeyValidityOutOfBoundsException"
    assert "API key must be valid for a minimum of 1 days" in err["Message"]

    yesterday = datetime.now() - timedelta(days=1)
    yesterday_in_secs = int(unix_time(yesterday))

    with pytest.raises(ClientError) as exc:
        client.create_api_key(
            apiId=api_id, description="invalid api key", expires=yesterday_in_secs
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ApiKeyValidityOutOfBoundsException"


@mock_aws
def test_create_api_key_expire_time_in_past():
    client = boto3.client("appsync", region_name="us-east-1")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    yesterday = datetime.now() - timedelta(days=1)
    yesterday_in_secs = int(unix_time(yesterday))

    with pytest.raises(ClientError) as exc:
        client.create_api_key(
            apiId=api_id, description="invalid api key", expires=yesterday_in_secs
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ApiKeyValidityOutOfBoundsException"
    assert "API key must be valid for a minimum of 1 days" in err["Message"]
