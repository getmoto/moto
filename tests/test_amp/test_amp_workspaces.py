import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_amp

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_amp
def test_create_workspace():
    client = boto3.client("amp", region_name="ap-southeast-1")
    resp = client.create_workspace(alias="test", clientToken="mytoken")

    resp.should.have.key("arn")
    resp.should.have.key("status").equals({"statusCode": "ACTIVE"})
    resp.should.have.key("workspaceId")


@mock_amp
def test_describe_workspace():
    client = boto3.client("amp", region_name="eu-west-1")
    workspace_id = client.create_workspace(alias="test", clientToken="mytoken")[
        "workspaceId"
    ]

    resp = client.describe_workspace(workspaceId=workspace_id)
    resp.should.have.key("workspace")

    workspace = resp["workspace"]
    workspace.should.have.key("alias")
    workspace.should.have.key("arn")
    workspace.should.have.key("createdAt")
    workspace.should.have.key("prometheusEndpoint")
    workspace.should.have.key("status").equals({"statusCode": "ACTIVE"})
    workspace.should.have.key("workspaceId").equals(workspace_id)


@mock_amp
def test_list_workspaces():
    client = boto3.client("amp", region_name="ap-southeast-1")
    client.create_workspace(alias="test")
    client.create_workspace(alias="another")
    client.create_workspace()

    resp = client.list_workspaces()
    resp.should.have.key("workspaces").length_of(3)
    resp.shouldnt.have.key("nextToken")

    resp = client.list_workspaces(alias="another")
    resp.should.have.key("workspaces").length_of(1)
    resp["workspaces"][0].should.have.key("alias").equals("another")


@mock_amp
def test_list_workspaces__paginated():
    client = boto3.client("amp", region_name="ap-southeast-1")
    for _ in range(125):
        client.create_workspace()

    # default pagesize is 100
    page1 = client.list_workspaces()
    page1.should.have.key("workspaces").length_of(100)
    page1.should.have.key("nextToken")

    # We can ask for a smaller pagesize
    page2 = client.list_workspaces(maxResults=15, nextToken=page1["nextToken"])
    page2.should.have.key("workspaces").length_of(15)
    page2.should.have.key("nextToken")

    page3 = client.list_workspaces(maxResults=15, nextToken=page2["nextToken"])
    page3.should.have.key("workspaces").length_of(10)
    page3.shouldnt.have.key("nextToken")

    # We could request all of them in one go
    full_page = client.list_workspaces(maxResults=150)
    full_page.should.have.key("workspaces").length_of(125)
    full_page.shouldnt.have.key("nextToken")


@mock_amp
def test_list_tags_for_resource():
    client = boto3.client("amp", region_name="ap-southeast-1")
    arn = client.create_workspace(
        alias="test", clientToken="mytoken", tags={"t1": "v1", "t2": "v2"}
    )["arn"]

    resp = client.list_tags_for_resource(resourceArn=arn)
    resp.should.have.key("tags").equals({"t1": "v1", "t2": "v2"})


@mock_amp
def test_update_workspace_alias():
    client = boto3.client("amp", region_name="ap-southeast-1")

    workspace_id = client.create_workspace(alias="initial")["workspaceId"]

    w = client.describe_workspace(workspaceId=workspace_id)["workspace"]
    w.should.have.key("alias").equals("initial")

    client.update_workspace_alias(alias="updated", workspaceId=workspace_id)

    w = client.describe_workspace(workspaceId=workspace_id)["workspace"]
    w.should.have.key("alias").equals("updated")


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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("Workspace not found")


@mock_amp
def test_tag_resource():
    client = boto3.client("amp", region_name="us-east-2")

    workspace = client.create_workspace(alias="test", tags={"t": "v"})
    arn = workspace["arn"]
    workspace_id = workspace["workspaceId"]

    client.tag_resource(resourceArn=arn, tags={"t1": "v1", "t2": "v2"})

    client.list_tags_for_resource(resourceArn=arn)["tags"].should.equal(
        {"t": "v", "t1": "v1", "t2": "v2"}
    )
    client.describe_workspace(workspaceId=workspace_id)["workspace"][
        "tags"
    ].should.equal({"t": "v", "t1": "v1", "t2": "v2"})

    client.untag_resource(resourceArn=arn, tagKeys=["t1"])
    client.list_tags_for_resource(resourceArn=arn)["tags"].should.equal(
        {"t": "v", "t2": "v2"}
    )

    client.untag_resource(resourceArn=arn, tagKeys=["t", "t2"])
    client.list_tags_for_resource(resourceArn=arn)["tags"].should.equal({})
