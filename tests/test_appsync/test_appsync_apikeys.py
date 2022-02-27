import boto3

from datetime import timedelta, datetime
from moto import mock_appsync
from moto.core.utils import unix_time


@mock_appsync
def test_create_api_key_simple():
    client = boto3.client("appsync", region_name="eu-west-1")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]
    resp = client.create_api_key(apiId=api_id)

    resp.should.have.key("apiKey")
    api_key = resp["apiKey"]

    api_key.should.have.key("id")
    api_key.shouldnt.have.key("description")
    api_key.should.have.key("expires")
    api_key.should.have.key("deletes")


@mock_appsync
def test_create_api_key():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_in_secs = int(unix_time(tomorrow))

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]
    resp = client.create_api_key(
        apiId=api_id, description="my first api key", expires=tomorrow_in_secs
    )

    resp.should.have.key("apiKey")
    api_key = resp["apiKey"]

    api_key.should.have.key("id")
    api_key.should.have.key("description").equals("my first api key")
    api_key.should.have.key("expires").equals(tomorrow_in_secs)
    api_key.should.have.key("deletes").equals(tomorrow_in_secs)


@mock_appsync
def test_delete_api_key():
    client = boto3.client("appsync", region_name="us-east-1")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]
    api_key_id = client.create_api_key(apiId=api_id)["apiKey"]["id"]

    client.delete_api_key(apiId=api_id, id=api_key_id)

    resp = client.list_api_keys(apiId=api_id)
    resp.should.have.key("apiKeys").length_of(0)


@mock_appsync
def test_list_api_keys_unknown_api():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    resp = client.list_api_keys(apiId="unknown")
    resp.should.have.key("apiKeys").equals([])


@mock_appsync
def test_list_api_keys_empty():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    resp = client.list_api_keys(apiId=api_id)
    resp.should.have.key("apiKeys").equals([])


@mock_appsync
def test_list_api_keys():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]
    client.create_api_key(apiId=api_id)
    client.create_api_key(apiId=api_id, description="my first api key")
    resp = client.list_api_keys(apiId=api_id)
    resp.should.have.key("apiKeys").length_of(2)


@mock_appsync
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

    updated.should.have.key("id").equals(original["id"])
    updated.should.have.key("description").equals("my second api key")
    updated.should.have.key("expires").equals(original["expires"])
    updated.should.have.key("deletes").equals(original["deletes"])
