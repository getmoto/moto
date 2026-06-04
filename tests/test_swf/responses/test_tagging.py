import boto3

from moto import mock_aws


def _register_and_describe_domain(client, name="test-domain", tags=None):
    kwargs = {
        "name": name,
        "workflowExecutionRetentionPeriodInDays": "30",
    }
    if tags:
        kwargs["tags"] = tags
    client.register_domain(**kwargs)
    return client.describe_domain(name=name)


@mock_aws
def test_register_domain_with_tags():
    client = boto3.client("swf", region_name="us-east-1")
    arn = _register_and_describe_domain(
        client,
        tags=[{"key": "env", "value": "prod"}, {"key": "team", "value": "platform"}],
    )["domainInfo"]["arn"]

    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]

    assert {"key": "env", "value": "prod"} in tags
    assert {"key": "team", "value": "platform"} in tags


@mock_aws
def test_list_tags_for_resource_empty():
    client = boto3.client("swf", region_name="us-east-1")
    arn = _register_and_describe_domain(client)["domainInfo"]["arn"]

    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert tags == []


@mock_aws
def test_tag_resource():
    client = boto3.client("swf", region_name="us-east-1")
    arn = _register_and_describe_domain(client)["domainInfo"]["arn"]

    client.tag_resource(
        resourceArn=arn,
        tags=[{"key": "k1", "value": "v1"}, {"key": "k2", "value": "v2"}],
    )

    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert {"key": "k1", "value": "v1"} in tags
    assert {"key": "k2", "value": "v2"} in tags


@mock_aws
def test_tag_resource_updates_existing_key():
    client = boto3.client("swf", region_name="us-east-1")
    arn = _register_and_describe_domain(client, tags=[{"key": "k1", "value": "old"}])[
        "domainInfo"
    ]["arn"]

    client.tag_resource(
        resourceArn=arn,
        tags=[{"key": "k1", "value": "new"}],
    )

    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert {"key": "k1", "value": "new"} in tags
    assert {"key": "k1", "value": "old"} not in tags


@mock_aws
def test_untag_resource():
    client = boto3.client("swf", region_name="us-east-1")
    arn = _register_and_describe_domain(
        client,
        tags=[{"key": "k1", "value": "v1"}, {"key": "k2", "value": "v2"}],
    )["domainInfo"]["arn"]

    client.untag_resource(resourceArn=arn, tagKeys=["k1"])

    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert {"key": "k1", "value": "v1"} not in tags
    assert {"key": "k2", "value": "v2"} in tags


@mock_aws
def test_untag_resource_nonexistent_key():
    client = boto3.client("swf", region_name="us-east-1")
    arn = _register_and_describe_domain(client, tags=[{"key": "k1", "value": "v1"}])[
        "domainInfo"
    ]["arn"]

    # Should not raise
    client.untag_resource(resourceArn=arn, tagKeys=["nonexistent"])

    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert {"key": "k1", "value": "v1"} in tags
