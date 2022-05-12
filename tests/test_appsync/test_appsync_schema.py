import boto3
import sure  # noqa # pylint: disable=unused-import

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
