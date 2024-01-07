import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_http_namespace_with_tags():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_http_namespace(
        Name="mynamespace", Tags=[{"Key": "key1", "Value": "val1"}]
    )

    ns_arn = client.list_namespaces()["Namespaces"][0]["Arn"]

    resp = client.list_tags_for_resource(ResourceARN=ns_arn)
    assert "Tags" in resp

    assert resp["Tags"] == [{"Key": "key1", "Value": "val1"}]


@mock_aws
def test_create_public_dns_namespace_with_tags():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_public_dns_namespace(
        Name="mynamespace", Tags=[{"Key": "key1", "Value": "val1"}]
    )

    ns_arn = client.list_namespaces()["Namespaces"][0]["Arn"]

    resp = client.list_tags_for_resource(ResourceARN=ns_arn)
    assert "Tags" in resp

    assert resp["Tags"] == [{"Key": "key1", "Value": "val1"}]


@mock_aws
def test_create_private_dns_namespace_with_tags():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_private_dns_namespace(
        Name="mynamespace", Vpc="vpc", Tags=[{"Key": "key1", "Value": "val1"}]
    )

    ns_arn = client.list_namespaces()["Namespaces"][0]["Arn"]

    resp = client.list_tags_for_resource(ResourceARN=ns_arn)
    assert "Tags" in resp

    assert resp["Tags"] == [{"Key": "key1", "Value": "val1"}]


@mock_aws
def test_create_service_with_tags():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_service(Name="myservice", Tags=[{"Key": "key1", "Value": "val1"}])

    ns_arn = client.list_services()["Services"][0]["Arn"]

    resp = client.list_tags_for_resource(ResourceARN=ns_arn)
    assert "Tags" in resp

    assert resp["Tags"] == [{"Key": "key1", "Value": "val1"}]


@mock_aws
def test_tag_resource():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")
    client.create_http_namespace(
        Name="mynamespace", Tags=[{"Key": "key1", "Value": "val1"}]
    )

    ns_arn = client.list_namespaces()["Namespaces"][0]["Arn"]
    client.tag_resource(ResourceARN=ns_arn, Tags=[{"Key": "key2", "Value": "val2"}])

    resp = client.list_tags_for_resource(ResourceARN=ns_arn)
    assert "Tags" in resp

    assert resp["Tags"] == [
        {"Key": "key1", "Value": "val1"},
        {"Key": "key2", "Value": "val2"},
    ]


@mock_aws
def test_untag_resource():
    client = boto3.client("servicediscovery", region_name="us-east-2")
    client.create_http_namespace(Name="mynamespace")

    ns_arn = client.list_namespaces()["Namespaces"][0]["Arn"]
    client.tag_resource(
        ResourceARN=ns_arn,
        Tags=[{"Key": "key1", "Value": "val1"}, {"Key": "key2", "Value": "val2"}],
    )

    client.untag_resource(ResourceARN=ns_arn, TagKeys=["key1"])

    resp = client.list_tags_for_resource(ResourceARN=ns_arn)
    assert "Tags" in resp

    assert resp["Tags"] == [{"Key": "key2", "Value": "val2"}]
