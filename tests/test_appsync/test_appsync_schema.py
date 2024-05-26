import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

schema = """type Mutation {
    putPost(id: ID!, title: String!): Post
}

"My custom post type"
type Post {
    id: ID!
    title: String!
}

type Query {
    singlePost(id: ID!): Post
}

schema {
    query: Query
    mutation: Mutation

}"""

schema_with_directives = """type Mutation {
    putPost(id: ID!, title: String!): Post
}

"My custom post type"
type Post {
    id: ID!
    title: String!
    createdAt: AWSDateTime!
}

type Query {
    singlePost(id: ID!): Post
}

schema {
    query: Query
    mutation: Mutation
    subscription: Subscription
}

type Subscription {
    onPostCreated(id: ID!): Post @aws_subscribe(mutations: ["putPost"])
}

"""


@mock_aws
def test_start_schema_creation():
    client = boto3.client("appsync", region_name="us-east-2")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    resp = client.start_schema_creation(apiId=api_id, definition=b"sth")

    assert resp["status"] == "PROCESSING"


@mock_aws
def test_get_schema_creation_status():
    client = boto3.client("appsync", region_name="eu-west-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(apiId=api_id, definition=schema.encode("utf-8"))
    resp = client.get_schema_creation_status(apiId=api_id)

    assert resp["status"] == "SUCCESS"
    assert "details" not in resp


@mock_aws
def test_get_schema_creation_status_invalid():
    client = boto3.client("appsync", region_name="eu-west-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(apiId=api_id, definition=b"sth")
    resp = client.get_schema_creation_status(apiId=api_id)

    assert resp["status"] == "FAILED"
    assert "Syntax Error" in resp["details"]


@mock_aws
@pytest.mark.parametrize(
    "region,partition", [("us-east-2", "aws"), ("cn-north-1", "aws-cn")]
)
def test_get_type_from_schema(region, partition):
    client = boto3.client("appsync", region_name=region)

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(apiId=api_id, definition=schema.encode("utf-8"))
    resp = client.get_type(apiId=api_id, typeName="Post", format="SDL")

    assert "type" in resp
    graphql_type = resp["type"]
    assert graphql_type["name"] == "Post"
    assert graphql_type["description"] == "My custom post type"
    assert graphql_type["arn"] == f"arn:{partition}:appsync:graphql_type/Post"
    assert graphql_type["definition"] == "NotYetImplemented"
    assert graphql_type["format"] == "SDL"

    query_type = client.get_type(apiId=api_id, typeName="Query", format="SDL")["type"]
    assert query_type["name"] == "Query"
    assert "description" not in query_type


@mock_aws
def test_get_introspection_schema_raise_gql_schema_error_if_no_schema():
    client = boto3.client("appsync", region_name="us-east-2")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    with pytest.raises(ClientError) as exc:
        client.get_introspection_schema(apiId=api_id, format="SDL")
    err = exc.value.response["Error"]
    assert err["Code"] == "GraphQLSchemaException"
    # AWS API appears to return InvalidSyntaxError if no schema exists
    assert err["Message"] == "InvalidSyntaxError"


@mock_aws
def test_get_introspection_schema_sdl():
    client = boto3.client("appsync", region_name="us-east-2")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(apiId=api_id, definition=schema.encode("utf-8"))

    resp = client.get_introspection_schema(apiId=api_id, format="SDL")
    schema_sdl = resp["schema"].read().decode("utf-8")
    assert "putPost(" in schema_sdl
    assert "singlePost(id: ID!): Post" in schema_sdl


@mock_aws
def test_get_introspection_schema_json():
    client = boto3.client("appsync", region_name="us-east-2")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(apiId=api_id, definition=schema.encode("utf-8"))

    resp = client.get_introspection_schema(apiId=api_id, format="JSON")
    schema_json = json.loads(resp["schema"].read().decode("utf-8"))
    assert "__schema" in schema_json
    assert "queryType" in schema_json["__schema"]
    assert "mutationType" in schema_json["__schema"]
    assert "subscriptionType" in schema_json["__schema"]
    assert "types" in schema_json["__schema"]
    assert "directives" in schema_json["__schema"]


@mock_aws
def test_get_introspection_schema_bad_format():
    client = boto3.client("appsync", region_name="us-east-2")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(apiId=api_id, definition=schema.encode("utf-8"))

    with pytest.raises(ClientError) as exc:
        client.get_introspection_schema(apiId=api_id, format="NotAFormat")
    err = exc.value.response["Error"]

    assert err["Code"] == "BadRequestException"
    assert err["Message"] == "Invalid format NotAFormat given"


@mock_aws
def test_get_introspection_schema_include_directives_true():
    client = boto3.client("appsync", region_name="us-east-2")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(
        apiId=api_id, definition=schema_with_directives.encode("utf-8")
    )

    resp = client.get_introspection_schema(
        apiId=api_id, format="SDL", includeDirectives=True
    )

    schema_sdl = resp["schema"].read().decode("utf-8")

    assert "@aws_subscribe" in schema_sdl


@mock_aws
def test_get_introspection_schema_include_directives_false():
    client = boto3.client("appsync", region_name="us-east-2")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(
        apiId=api_id, definition=schema_with_directives.encode("utf-8")
    )

    resp = client.get_introspection_schema(
        apiId=api_id, format="SDL", includeDirectives=False
    )

    schema_sdl = resp["schema"].read().decode("utf-8")

    assert "@aws_subscribe" not in schema_sdl
