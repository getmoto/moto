import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_amp
from uuid import uuid4

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_amp
def test_create_workspace():
    client = boto3.client("amp", region_name="ap-southeast-1")
    resp = client.create_workspace(alias="test", clientToken="mytoken")

    assert "arn" in resp
    assert resp["status"] == {"statusCode": "ACTIVE"}
    assert "workspaceId" in resp


@mock_amp
def test_describe_workspace():
    client = boto3.client("amp", region_name="eu-west-1")
    workspace_id = client.create_workspace(alias="test", clientToken="mytoken")[
        "workspaceId"
    ]

    resp = client.describe_workspace(workspaceId=workspace_id)
    assert "workspace" in resp

    workspace = resp["workspace"]
    assert "alias" in workspace
    assert "arn" in workspace
    assert "createdAt" in workspace
    assert "prometheusEndpoint" in workspace
    assert workspace["status"] == {"statusCode": "ACTIVE"}
    assert workspace["workspaceId"] == workspace_id


@mock_amp
def test_list_workspaces():
    my_alias = str(uuid4())[0:6]
    client = boto3.client("amp", region_name="ap-southeast-1")
    client.create_workspace(alias="test")
    client.create_workspace(alias=my_alias)

    spaces = client.list_workspaces(maxResults=1000)["workspaces"]
    assert len(spaces) >= 2
    assert "test" in [sp.get("alias") for sp in spaces]
    assert my_alias in [sp.get("alias") for sp in spaces]

    resp = client.list_workspaces(alias=my_alias)
    assert len(resp["workspaces"]) == 1
    assert resp["workspaces"][0]["alias"] == my_alias


@mock_amp
def test_list_workspaces__paginated():
    client = boto3.client("amp", region_name="ap-southeast-1")
    for _ in range(125):
        client.create_workspace()

    # default pagesize is 100
    page1 = client.list_workspaces()
    assert len(page1["workspaces"]) == 100
    assert "nextToken" in page1

    # We can ask for a smaller pagesize
    page2 = client.list_workspaces(maxResults=15, nextToken=page1["nextToken"])
    assert len(page2["workspaces"]) == 15
    assert "nextToken" in page2

    # We could request all of them in one go
    all_workspaces = client.list_workspaces(maxResults=1000)["workspaces"]
    length = len(all_workspaces)
    # We don't know exactly how much workspaces there are, because we are running multiple tests at the same time
    assert length >= 125


@mock_amp
def test_list_tags_for_resource():
    client = boto3.client("amp", region_name="ap-southeast-1")
    arn = client.create_workspace(
        alias="test", clientToken="mytoken", tags={"t1": "v1", "t2": "v2"}
    )["arn"]

    assert get_tags(arn, client) == {"t1": "v1", "t2": "v2"}


@mock_amp
def test_update_workspace_alias():
    client = boto3.client("amp", region_name="ap-southeast-1")

    workspace_id = client.create_workspace(alias="initial")["workspaceId"]

    w = client.describe_workspace(workspaceId=workspace_id)["workspace"]
    assert w["alias"] == "initial"

    client.update_workspace_alias(alias="updated", workspaceId=workspace_id)

    w = client.describe_workspace(workspaceId=workspace_id)["workspace"]
    assert w["alias"] == "updated"


@mock_amp
def test_delete_workspace():
    client = boto3.client("amp", region_name="us-east-2")

    workspace_id = client.create_workspace(alias="test", clientToken="mytoken")[
        "workspaceId"
    ]

    client.delete_workspace(workspaceId=workspace_id)

    with pytest.raises(ClientError) as exc:
        client.describe_workspace(workspaceId=workspace_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Workspace not found"


@mock_amp
def test_tag_resource():
    client = boto3.client("amp", region_name="us-east-2")

    workspace = client.create_workspace(alias="test", tags={"t": "v"})
    arn = workspace["arn"]
    workspace_id = workspace["workspaceId"]

    client.tag_resource(resourceArn=arn, tags={"t1": "v1", "t2": "v2"})

    expected = {"t": "v", "t1": "v1", "t2": "v2"}
    assert get_tags(arn, client) == expected
    assert (
        client.describe_workspace(workspaceId=workspace_id)["workspace"]["tags"]
        == expected
    )

    client.untag_resource(resourceArn=arn, tagKeys=["t1"])
    assert get_tags(arn, client) == {"t": "v", "t2": "v2"}

    client.untag_resource(resourceArn=arn, tagKeys=["t", "t2"])
    assert get_tags(arn, client) == {}


def get_tags(arn, client):
    return client.list_tags_for_resource(resourceArn=arn)["tags"]
