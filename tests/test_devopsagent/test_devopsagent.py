import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

REGION = "us-east-1"


def _client():
    return boto3.client("devops-agent", region_name=REGION)


def _create_agent_space(client, name="my-space", **kwargs):
    return client.create_agent_space(name=name, **kwargs)["agentSpace"]


def _arn_for(space_id):
    sts = boto3.client("sts", region_name=REGION)
    account_id = sts.get_caller_identity()["Account"]
    return f"arn:aws:aidevops:{REGION}:{account_id}:agentspace/{space_id}"


@mock_aws
def test_create_agent_space():
    client = _client()

    resp = client.create_agent_space(name="my-space", description="A test space")
    space = resp["agentSpace"]
    assert "agentSpaceId" in space
    assert space["name"] == "my-space"
    assert space["description"] == "A test space"
    assert "createdAt" in space
    assert "updatedAt" in space


@mock_aws
def test_get_agent_space():
    client = _client()
    space_id = _create_agent_space(client)["agentSpaceId"]

    resp = client.get_agent_space(agentSpaceId=space_id)
    space = resp["agentSpace"]
    assert space["agentSpaceId"] == space_id
    assert space["name"] == "my-space"


@mock_aws
def test_get_agent_space_not_found():
    client = _client()

    with pytest.raises(ClientError) as exc:
        client.get_agent_space(agentSpaceId="as-nonexistent")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_agent_spaces():
    client = _client()
    space_id = _create_agent_space(client)["agentSpaceId"]

    resp = client.list_agent_spaces()
    assert len(resp["agentSpaces"]) == 1
    assert resp["agentSpaces"][0]["agentSpaceId"] == space_id


@mock_aws
def test_update_agent_space():
    client = _client()
    space_id = _create_agent_space(client)["agentSpaceId"]

    resp = client.update_agent_space(agentSpaceId=space_id, name="renamed-space")
    assert resp["agentSpace"]["name"] == "renamed-space"

    resp = client.get_agent_space(agentSpaceId=space_id)
    assert resp["agentSpace"]["name"] == "renamed-space"


@mock_aws
def test_update_agent_space_not_found():
    client = _client()

    with pytest.raises(ClientError) as exc:
        client.update_agent_space(agentSpaceId="as-nonexistent", name="x")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_delete_agent_space():
    client = _client()
    space_id = _create_agent_space(client)["agentSpaceId"]

    client.delete_agent_space(agentSpaceId=space_id)

    resp = client.list_agent_spaces()
    assert len(resp["agentSpaces"]) == 0


@mock_aws
def test_delete_agent_space_not_found():
    client = _client()

    with pytest.raises(ClientError) as exc:
        client.delete_agent_space(agentSpaceId="as-nonexistent")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_create_agent_space_with_tags():
    client = _client()

    resp = client.create_agent_space(
        name="tagged-space",
        tags={"env": "test", "team": "platform"},
    )
    space_id = resp["agentSpace"]["agentSpaceId"]
    assert resp.get("tags") == {"env": "test", "team": "platform"}

    resp = client.get_agent_space(agentSpaceId=space_id)
    assert resp["tags"] == {"env": "test", "team": "platform"}


@mock_aws
def test_list_tags_for_resource():
    client = _client()
    space_id = _create_agent_space(
        client, name="tagged-space", tags={"env": "test", "team": "platform"}
    )["agentSpaceId"]

    resp = client.list_tags_for_resource(resourceArn=_arn_for(space_id))
    assert resp["tags"] == {"env": "test", "team": "platform"}


@mock_aws
def test_tag_resource():
    client = _client()
    space_id = _create_agent_space(
        client, name="tagged-space", tags={"env": "test", "team": "platform"}
    )["agentSpaceId"]
    arn = _arn_for(space_id)

    client.tag_resource(resourceArn=arn, tags={"version": "1"})
    resp = client.list_tags_for_resource(resourceArn=arn)
    assert resp["tags"] == {"env": "test", "team": "platform", "version": "1"}


@mock_aws
def test_untag_resource():
    client = _client()
    space_id = _create_agent_space(
        client, name="tagged-space", tags={"env": "test", "team": "platform"}
    )["agentSpaceId"]
    arn = _arn_for(space_id)

    client.untag_resource(resourceArn=arn, tagKeys=["team"])
    resp = client.list_tags_for_resource(resourceArn=arn)
    assert resp["tags"] == {"env": "test"}
