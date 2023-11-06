import boto3

from moto import mock_aws


@mock_aws
def test_tag_resource():
    client = boto3.client("inspector2", region_name="ap-southeast-1")
    arn = client.create_filter(
        name="my_first_filter",
        action="NONE",
        filterCriteria={"findingArn": [{"comparison": "EQUALS", "value": "cvdn"}]},
    )["arn"]

    assert client.list_tags_for_resource(resourceArn=arn)["tags"] == {}

    client.tag_resource(resourceArn=arn, tags={"k1": "v1"})
    assert client.list_tags_for_resource(resourceArn=arn)["tags"] == {"k1": "v1"}

    client.tag_resource(resourceArn=arn, tags={"k2": "v2"})
    assert client.list_tags_for_resource(resourceArn=arn)["tags"] == {
        "k1": "v1",
        "k2": "v2",
    }

    client.untag_resource(resourceArn=arn, tagKeys=["k1"])
    assert client.list_tags_for_resource(resourceArn=arn)["tags"] == {"k2": "v2"}


@mock_aws
def test_tag_filter():
    client = boto3.client("inspector2", region_name="ap-southeast-1")
    arn = client.create_filter(
        name="my_first_filter",
        action="NONE",
        filterCriteria={"findingArn": [{"comparison": "EQUALS", "value": "cvdn"}]},
        tags={"k1": "v1"},
    )["arn"]

    assert client.list_tags_for_resource(resourceArn=arn)["tags"] == {"k1": "v1"}

    client.tag_resource(resourceArn=arn, tags={"k2": "v2"})
    assert client.list_tags_for_resource(resourceArn=arn)["tags"] == {
        "k1": "v1",
        "k2": "v2",
    }

    filters = client.list_filters()["filters"]
    assert filters[0]["tags"] == {"k1": "v1", "k2": "v2"}
