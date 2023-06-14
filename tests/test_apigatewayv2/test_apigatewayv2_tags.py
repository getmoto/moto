import boto3

from moto import mock_apigatewayv2


@mock_apigatewayv2
def test_create_api_with_tags():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    resp = client.create_api(
        Name="test-api", ProtocolType="HTTP", Tags={"key1": "value1", "key2": "value2"}
    )

    assert resp["Tags"] == {"key1": "value1", "key2": "value2"}


@mock_apigatewayv2
def test_tag_resource():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resource_arn = f"arn:aws:apigateway:eu-west-1::/apis/{api_id}"
    client.tag_resource(
        ResourceArn=resource_arn, Tags={"key1": "value1", "key2": "value2"}
    )

    resp = client.get_api(ApiId=api_id)

    assert resp["Tags"] == {"key1": "value1", "key2": "value2"}


@mock_apigatewayv2
def test_get_tags():
    client = boto3.client("apigatewayv2", region_name="eu-west-2")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    resource_arn = f"arn:aws:apigateway:eu-west-2::/apis/{api_id}"

    client.tag_resource(
        ResourceArn=resource_arn, Tags={"key1": "value1", "key2": "value2"}
    )

    resp = client.get_tags(ResourceArn=resource_arn)

    assert resp["Tags"] == {"key1": "value1", "key2": "value2"}


@mock_apigatewayv2
def test_untag_resource():
    client = boto3.client("apigatewayv2", region_name="eu-west-2")
    api_id = client.create_api(
        Name="test-api", ProtocolType="HTTP", Tags={"key1": "value1"}
    )["ApiId"]
    resource_arn = f"arn:aws:apigateway:eu-west-2::/apis/{api_id}"

    client.tag_resource(
        ResourceArn=resource_arn, Tags={"key2": "value2", "key3": "value3"}
    )

    client.untag_resource(ResourceArn=resource_arn, TagKeys=["key2"])

    resp = client.get_tags(ResourceArn=resource_arn)

    assert resp["Tags"] == {"key1": "value1", "key3": "value3"}
