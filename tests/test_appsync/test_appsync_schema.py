import boto3
import sure  # noqa # pylint: disable=unused-import
import json
from botocore.exceptions import ClientError
import pytest
from moto import mock_appsync

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


@mock_appsync
def test_start_schema_creation():
    client = boto3.client("appsync", region_name="us-east-2")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    resp = client.start_schema_creation(apiId=api_id, definition=b"sth")

    resp.should.have.key("status").equals("PROCESSING")


@mock_appsync
def test_get_schema_creation_status():
    client = boto3.client("appsync", region_name="eu-west-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(apiId=api_id, definition=schema.encode("utf-8"))
    resp = client.get_schema_creation_status(apiId=api_id)

    resp.should.have.key("status").equals("SUCCESS")
    resp.shouldnt.have.key("details")


@mock_appsync
def test_get_schema_creation_status_invalid():
    client = boto3.client("appsync", region_name="eu-west-1")
    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(apiId=api_id, definition=b"sth")
    resp = client.get_schema_creation_status(apiId=api_id)

    resp.should.have.key("status").equals("FAILED")
    resp.should.have.key("details").match("Syntax Error")


@mock_appsync
def test_get_type_from_schema():
    client = boto3.client("appsync", region_name="us-east-2")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(apiId=api_id, definition=schema.encode("utf-8"))
    resp = client.get_type(apiId=api_id, typeName="Post", format="SDL")

    resp.should.have.key("type")
    graphql_type = resp["type"]
    graphql_type.should.have.key("name").equals("Post")
    graphql_type.should.have.key("description").equals("My custom post type")
    graphql_type.should.have.key("arn").equals("arn:aws:appsync:graphql_type/Post")
    graphql_type.should.have.key("definition").equals("NotYetImplemented")
    graphql_type.should.have.key("format").equals("SDL")

    query_type = client.get_type(apiId=api_id, typeName="Query", format="SDL")["type"]
    query_type.should.have.key("name").equals("Query")
    query_type.shouldnt.have.key("description")


@mock_appsync
def test_get_introspection_schema_raise_gql_schema_error_if_no_schema():
    client = boto3.client("appsync", region_name="us-east-2")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    with pytest.raises(ClientError) as exc:
        client.get_introspection_schema(apiId=api_id, format="SDL")
    err = exc.value.response["Error"]
    err["Code"].should.equal("GraphQLSchemaException")
    # AWS API appears to return InvalidSyntaxError if no schema exists
    err["Message"].should.equal("InvalidSyntaxError")


@mock_appsync
def test_get_introspection_schema_sdl():
    client = boto3.client("appsync", region_name="us-east-2")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(apiId=api_id, definition=schema.encode("utf-8"))

    resp = client.get_introspection_schema(apiId=api_id, format="SDL")
    schema_sdl = resp["schema"].read().decode("utf-8")
    schema_sdl.should.contain("putPost(")
    schema_sdl.should.contain("singlePost(id: ID!): Post")


@mock_appsync
def test_get_introspection_schema_json():

    client = boto3.client("appsync", region_name="us-east-2")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(apiId=api_id, definition=schema.encode("utf-8"))

    resp = client.get_introspection_schema(apiId=api_id, format="JSON")
    schema_json = json.loads(resp["schema"].read().decode("utf-8"))
    schema_json.should.have.key("__schema")
    schema_json["__schema"].should.have.key("queryType")
    schema_json["__schema"].should.have.key("mutationType")
    schema_json["__schema"].should.have.key("subscriptionType")
    schema_json["__schema"].should.have.key("types")
    schema_json["__schema"].should.have.key("directives")


@mock_appsync
def test_get_introspection_schema_bad_format():
    client = boto3.client("appsync", region_name="us-east-2")

    api_id = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]["apiId"]

    client.start_schema_creation(apiId=api_id, definition=schema.encode("utf-8"))

    with pytest.raises(ClientError) as exc:
        client.get_introspection_schema(apiId=api_id, format="NotAFormat")
    err = exc.value.response["Error"]

    err["Code"].should.equal("BadRequestException")
    err["Message"].should.equal("Invalid format NotAFormat given")


@mock_appsync
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

    schema_sdl.should.contain("@aws_subscribe")


@mock_appsync
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

    schema_sdl.shouldnt.contain("@aws_subscribe")
