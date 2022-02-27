import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_appsync


@mock_appsync
def test_create_graphql_api_with_tags():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    api = client.create_graphql_api(
        name="api1", authenticationType="API_KEY", tags={"key": "val", "key2": "val2"}
    )["graphqlApi"]

    api.should.have.key("tags").equals({"key": "val", "key2": "val2"})

    api = client.get_graphql_api(apiId=api["apiId"])["graphqlApi"]

    api.should.have.key("tags").equals({"key": "val", "key2": "val2"})


@mock_appsync
def test_tag_resource():
    client = boto3.client("appsync", region_name="us-east-2")
    api = client.create_graphql_api(name="api1", authenticationType="API_KEY")[
        "graphqlApi"
    ]

    client.tag_resource(resourceArn=(api["arn"]), tags={"key1": "val1"})

    api = client.get_graphql_api(apiId=api["apiId"])["graphqlApi"]
    api.should.have.key("tags").equals({"key1": "val1"})


@mock_appsync
def test_tag_resource_with_existing_tags():
    client = boto3.client("appsync", region_name="us-east-2")
    api = client.create_graphql_api(
        name="api1", authenticationType="API_KEY", tags={"key": "val", "key2": "val2"}
    )["graphqlApi"]

    client.untag_resource(resourceArn=api["arn"], tagKeys=["key"])

    client.tag_resource(
        resourceArn=(api["arn"]), tags={"key2": "new value", "key3": "val3"}
    )

    api = client.get_graphql_api(apiId=api["apiId"])["graphqlApi"]
    api.should.have.key("tags").equals({"key2": "new value", "key3": "val3"})


@mock_appsync
def test_untag_resource():
    client = boto3.client("appsync", region_name="eu-west-1")
    api = client.create_graphql_api(
        name="api1", authenticationType="API_KEY", tags={"key": "val", "key2": "val2"}
    )["graphqlApi"]

    client.untag_resource(resourceArn=api["arn"], tagKeys=["key"])

    api = client.get_graphql_api(apiId=api["apiId"])["graphqlApi"]
    api.should.have.key("tags").equals({"key2": "val2"})


@mock_appsync
def test_untag_resource_all():
    client = boto3.client("appsync", region_name="eu-west-1")
    api = client.create_graphql_api(
        name="api1", authenticationType="API_KEY", tags={"key": "val", "key2": "val2"}
    )["graphqlApi"]

    client.untag_resource(resourceArn=api["arn"], tagKeys=["key", "key2"])

    api = client.get_graphql_api(apiId=api["apiId"])["graphqlApi"]
    api.should.have.key("tags").equals({})


@mock_appsync
def test_list_tags_for_resource():
    client = boto3.client("appsync", region_name="ap-southeast-1")
    api = client.create_graphql_api(
        name="api1", authenticationType="API_KEY", tags={"key": "val", "key2": "val2"}
    )["graphqlApi"]

    resp = client.list_tags_for_resource(resourceArn=api["arn"])

    resp.should.have.key("tags").equals({"key": "val", "key2": "val2"})
