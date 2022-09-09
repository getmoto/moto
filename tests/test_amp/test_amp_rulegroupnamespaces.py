"""Unit tests for amp-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

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

    resp.should.have.key("arn")
    resp.should.have.key("name").equals("my first rule group")
    resp.should.have.key("status")


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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("RuleGroupNamespace not found")


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
    resp.should.have.key("ruleGroupsNamespace")
    ns = resp["ruleGroupsNamespace"]

    ns.should.have.key("arn")
    ns.should.have.key("createdAt")
    ns.should.have.key("data").equals(b"asdf")
    ns.should.have.key("modifiedAt")
    ns.should.have.key("name").equals("myname")
    ns.should.have.key("status")


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
    resp.should.have.key("ruleGroupsNamespace")
    ns = resp["ruleGroupsNamespace"]

    ns.should.have.key("arn")
    ns.should.have.key("createdAt")
    ns.should.have.key("data").equals(b"updated")


@mock_amp
def test_list_rule_groups_namespaces():
    client = boto3.client("amp", region_name="ap-southeast-1")
    w_id = client.create_workspace()["workspaceId"]
    for idx in range(15):
        client.create_rule_groups_namespace(
            data=b"a", name=f"ns{idx}", workspaceId=w_id
        )

    resp = client.list_rule_groups_namespaces(workspaceId=w_id)
    resp.should.have.key("ruleGroupsNamespaces").length_of(15)
    resp.shouldnt.have.key("nextToken")

    resp = client.list_rule_groups_namespaces(workspaceId=w_id, name="ns1")
    resp.should.have.key("ruleGroupsNamespaces").length_of(6)
    names = [ns["name"] for ns in resp["ruleGroupsNamespaces"]]
    set(names).should.equal({"ns10", "ns13", "ns1", "ns12", "ns11", "ns14"})

    resp = client.list_rule_groups_namespaces(workspaceId=w_id, name="ns10")
    resp.should.have.key("ruleGroupsNamespaces").length_of(1)
    names = [ns["name"] for ns in resp["ruleGroupsNamespaces"]]
    set(names).should.equal({"ns10"})


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
    page1.should.have.key("ruleGroupsNamespaces").length_of(100)
    page1.should.have.key("nextToken")

    # We can ask for a smaller pagesize
    page2 = client.list_rule_groups_namespaces(
        workspaceId=w_id, maxResults=15, nextToken=page1["nextToken"]
    )
    page2.should.have.key("ruleGroupsNamespaces").length_of(15)
    page2.should.have.key("nextToken")

    page3 = client.list_rule_groups_namespaces(
        workspaceId=w_id, maxResults=15, nextToken=page2["nextToken"]
    )
    page3.should.have.key("ruleGroupsNamespaces").length_of(10)
    page3.shouldnt.have.key("nextToken")

    # We could request all of them in one go
    full_page = client.list_rule_groups_namespaces(workspaceId=w_id, maxResults=150)
    full_page.should.have.key("ruleGroupsNamespaces").length_of(125)
    full_page.shouldnt.have.key("nextToken")


@mock_amp
def test_tag_resource():
    client = boto3.client("amp", region_name="us-east-2")

    w_id = client.create_workspace()["workspaceId"]
    ns = client.create_rule_groups_namespace(
        data=b"a", name="ns", workspaceId=w_id, tags={"t": "v"}
    )

    arn = ns["arn"]

    client.tag_resource(resourceArn=arn, tags={"t1": "v1", "t2": "v2"})

    client.list_tags_for_resource(resourceArn=arn)["tags"].should.equal(
        {"t": "v", "t1": "v1", "t2": "v2"}
    )
    client.describe_rule_groups_namespace(workspaceId=w_id, name="ns")[
        "ruleGroupsNamespace"
    ]["tags"].should.equal({"t": "v", "t1": "v1", "t2": "v2"})

    client.untag_resource(resourceArn=arn, tagKeys=["t1"])
    client.list_tags_for_resource(resourceArn=arn)["tags"].should.equal(
        {"t": "v", "t2": "v2"}
    )

    client.untag_resource(resourceArn=arn, tagKeys=["t", "t2"])
    client.list_tags_for_resource(resourceArn=arn)["tags"].should.equal({})
