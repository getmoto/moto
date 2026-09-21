import boto3

from moto import mock_aws
from tests.test_cleanrooms.test_cleanrooms import (
    REGION,
    create_collaboration,
    create_configured_table,
)


@mock_aws
def test_resourcegroupstaggingapi_get_cleanrooms_resources():
    client = boto3.client("cleanrooms", region_name=REGION)
    tagging = boto3.client("resourcegroupstaggingapi", region_name=REGION)
    collaboration = create_collaboration(client, tags={"env": "test"})
    configured_table = create_configured_table(client, tags={"team": "data"})
    membership = client.create_membership(
        collaborationIdentifier=collaboration["id"],
        queryLogStatus="ENABLED",
        tags={"env": "test"},
    )["membership"]
    untagged = create_collaboration(client, name="untagged-collaboration")

    resources = tagging.get_resources()["ResourceTagMappingList"]
    assert {r["ResourceARN"] for r in resources} == {
        collaboration["arn"],
        configured_table["arn"],
        membership["arn"],
    }
    assert untagged["arn"] not in {r["ResourceARN"] for r in resources}

    # Filter by type
    assert [
        r["ResourceARN"]
        for r in tagging.get_resources(
            ResourceTypeFilters=["cleanrooms:collaboration"]
        )["ResourceTagMappingList"]
    ] == [collaboration["arn"]]
    assert [
        r["ResourceARN"]
        for r in tagging.get_resources(
            ResourceTypeFilters=["cleanrooms:configuredtable"]
        )["ResourceTagMappingList"]
    ] == [configured_table["arn"]]

    # Filter by Tag
    assert {
        r["ResourceARN"]
        for r in tagging.get_resources(TagFilters=[{"Key": "env", "Values": ["test"]}])[
            "ResourceTagMappingList"
        ]
    } == {collaboration["arn"], membership["arn"]}


@mock_aws
def test_resourcegroupstaggingapi_tag_and_untag_cleanrooms_resources():
    client = boto3.client("cleanrooms", region_name=REGION)
    tagging = boto3.client("resourcegroupstaggingapi", region_name=REGION)
    collaboration = create_collaboration(client, tags={"env": "test"})
    configured_table = create_configured_table(client)
    membership = client.create_membership(
        collaborationIdentifier=collaboration["id"],
        queryLogStatus="ENABLED",
    )["membership"]
    arns = [collaboration["arn"], configured_table["arn"], membership["arn"]]

    # Only the collaboration is tagged initially
    assert [
        r["ResourceARN"] for r in tagging.get_resources()["ResourceTagMappingList"]
    ] == [collaboration["arn"]]

    # Tag all resources through the Resource Groups Tagging API
    resp = tagging.tag_resources(
        ResourceARNList=arns, Tags={"team": "data", "owner": "alice"}
    )
    assert resp["FailedResourcesMap"] == {}

    assert client.list_tags_for_resource(resourceArn=collaboration["arn"])["tags"] == {
        "env": "test",
        "team": "data",
        "owner": "alice",
    }
    for arn in arns[1:]:
        assert client.list_tags_for_resource(resourceArn=arn)["tags"] == {
            "team": "data",
            "owner": "alice",
        }
    assert {
        r["ResourceARN"]
        for r in tagging.get_resources(
            TagFilters=[{"Key": "team", "Values": ["data"]}]
        )["ResourceTagMappingList"]
    } == set(arns)

    # Untag through the Resource Groups Tagging API
    resp = tagging.untag_resources(ResourceARNList=arns, TagKeys=["team", "owner"])
    assert resp["FailedResourcesMap"] == {}

    assert client.list_tags_for_resource(resourceArn=collaboration["arn"])["tags"] == {
        "env": "test"
    }
    for arn in arns[1:]:
        assert client.list_tags_for_resource(resourceArn=arn)["tags"] == {}
    assert (
        tagging.get_resources(TagFilters=[{"Key": "team"}])["ResourceTagMappingList"]
        == []
    )
    assert [
        r["ResourceARN"] for r in tagging.get_resources()["ResourceTagMappingList"]
    ] == [collaboration["arn"]]
