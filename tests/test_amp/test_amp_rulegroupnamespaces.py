"""Unit tests for amp-supported APIs."""
import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_amp

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_amp
def test_create_rule_groups_namespace():
    client = boto3.client("amp", region_name="ap-southeast-1")
    workspace_id = client.create_workspace()["workspaceId"]
    resp = client.create_rule_groups_namespace(
        data=b"asdf", name="my first rule group", workspaceId=workspace_id
    )

    assert "arn" in resp
    assert resp["name"] == "my first rule group"
    assert "status" in resp


@mock_amp
def test_delete_rule_groups_namespace():
    client = boto3.client("amp", region_name="us-east-2")
    workspace_id = client.create_workspace()["workspaceId"]
    client.create_rule_groups_namespace(
        data=b"asdf", name="myname", workspaceId=workspace_id
    )

    client.delete_rule_groups_namespace(name="myname", workspaceId=workspace_id)

    with pytest.raises(ClientError) as exc:
        client.describe_rule_groups_namespace(name="myname", workspaceId=workspace_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "RuleGroupNamespace not found"


@mock_amp
def test_describe_rule_groups_namespace():
    client = boto3.client("amp", region_name="us-east-2")

    workspace_id = client.create_workspace()["workspaceId"]
    client.create_rule_groups_namespace(
        data=b"asdf", name="myname", workspaceId=workspace_id
    )

    resp = client.describe_rule_groups_namespace(
        name="myname", workspaceId=workspace_id
    )
    assert "ruleGroupsNamespace" in resp
    ns = resp["ruleGroupsNamespace"]

    assert "arn" in ns
    assert "createdAt" in ns
    assert ns["data"] == b"asdf"
    assert "modifiedAt" in ns
    assert ns["name"] == "myname"
    assert "status" in ns


@mock_amp
def test_put_rule_groups_namespace():
    client = boto3.client("amp", region_name="eu-west-1")

    workspace_id = client.create_workspace()["workspaceId"]
    client.create_rule_groups_namespace(
        data=b"asdf", name="myname", workspaceId=workspace_id
    )

    client.put_rule_groups_namespace(
        name="myname", workspaceId=workspace_id, data=b"updated"
    )

    resp = client.describe_rule_groups_namespace(
        name="myname", workspaceId=workspace_id
    )
    assert "ruleGroupsNamespace" in resp
    ns = resp["ruleGroupsNamespace"]

    assert "arn" in ns
    assert "createdAt" in ns
    assert ns["data"] == b"updated"


@mock_amp
def test_list_rule_groups_namespaces():
    client = boto3.client("amp", region_name="ap-southeast-1")
    w_id = client.create_workspace()["workspaceId"]
    for idx in range(15):
        client.create_rule_groups_namespace(
            data=b"a", name=f"ns{idx}", workspaceId=w_id
        )

    resp = client.list_rule_groups_namespaces(workspaceId=w_id)
    assert len(resp["ruleGroupsNamespaces"]) == 15
    assert "nextToken" not in resp

    resp = client.list_rule_groups_namespaces(workspaceId=w_id, name="ns1")
    assert len(resp["ruleGroupsNamespaces"]) == 6
    names = [ns["name"] for ns in resp["ruleGroupsNamespaces"]]
    assert set(names) == {"ns10", "ns13", "ns1", "ns12", "ns11", "ns14"}

    resp = client.list_rule_groups_namespaces(workspaceId=w_id, name="ns10")
    assert len(resp["ruleGroupsNamespaces"]) == 1
    names = [ns["name"] for ns in resp["ruleGroupsNamespaces"]]
    assert set(names) == {"ns10"}


@mock_amp
def test_list_rule_groups_namespaces__paginated():
    client = boto3.client("amp", region_name="ap-southeast-1")
    w_id = client.create_workspace()["workspaceId"]
    for idx in range(125):
        client.create_rule_groups_namespace(
            data=b"a", name=f"ns{idx}", workspaceId=w_id
        )

    # default pagesize is 100
    page1 = client.list_rule_groups_namespaces(workspaceId=w_id)
    assert len(page1["ruleGroupsNamespaces"]) == 100
    assert "nextToken" in page1

    # We can ask for a smaller pagesize
    page2 = client.list_rule_groups_namespaces(
        workspaceId=w_id, maxResults=15, nextToken=page1["nextToken"]
    )
    assert len(page2["ruleGroupsNamespaces"]) == 15
    assert "nextToken" in page2

    page3 = client.list_rule_groups_namespaces(
        workspaceId=w_id, maxResults=15, nextToken=page2["nextToken"]
    )
    assert len(page3["ruleGroupsNamespaces"]) == 10
    assert "nextToken" not in page3

    # We could request all of them in one go
    full_page = client.list_rule_groups_namespaces(workspaceId=w_id, maxResults=150)
    assert len(full_page["ruleGroupsNamespaces"]) == 125
    assert "nextToken" not in full_page


@mock_amp
def test_tag_resource():
    client = boto3.client("amp", region_name="us-east-2")

    w_id = client.create_workspace()["workspaceId"]
    ns = client.create_rule_groups_namespace(
        data=b"a", name="ns", workspaceId=w_id, tags={"t": "v"}
    )

    arn = ns["arn"]

    client.tag_resource(resourceArn=arn, tags={"t1": "v1", "t2": "v2"})

    assert get_tags(arn, client) == {"t": "v", "t1": "v1", "t2": "v2"}
    ns = client.describe_rule_groups_namespace(workspaceId=w_id, name="ns")[
        "ruleGroupsNamespace"
    ]
    assert ns["tags"] == {"t": "v", "t1": "v1", "t2": "v2"}

    client.untag_resource(resourceArn=arn, tagKeys=["t1"])
    assert get_tags(arn, client) == {"t": "v", "t2": "v2"}

    client.untag_resource(resourceArn=arn, tagKeys=["t", "t2"])
    assert get_tags(arn, client) == {}


def get_tags(arn, client):
    return client.list_tags_for_resource(resourceArn=arn)["tags"]
