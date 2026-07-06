import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

REGION = "us-east-1"


def _client():
    return boto3.client("devops-agent", region_name=REGION)


@mock_aws
def test_crud_round_trip():
    client = _client()

    resp = client.create_agent_space(name="my-space", description="A test space")
    space = resp["agentSpace"]
    assert "agentSpaceId" in space
    assert space["name"] == "my-space"
    assert space["description"] == "A test space"
    assert "createdAt" in space
    assert "updatedAt" in space
    space_id = space["agentSpaceId"]

    resp = client.get_agent_space(agentSpaceId=space_id)
    space = resp["agentSpace"]
    assert space["agentSpaceId"] == space_id
    assert space["name"] == "my-space"

    resp = client.list_agent_spaces()
    assert len(resp["agentSpaces"]) == 1
    assert resp["agentSpaces"][0]["agentSpaceId"] == space_id

    resp = client.update_agent_space(agentSpaceId=space_id, name="renamed-space")
    space = resp["agentSpace"]
    assert space["name"] == "renamed-space"

    resp = client.get_agent_space(agentSpaceId=space_id)
    assert resp["agentSpace"]["name"] == "renamed-space"

    client.delete_agent_space(agentSpaceId=space_id)

    resp = client.list_agent_spaces()
    assert len(resp["agentSpaces"]) == 0


@mock_aws
def test_tagging():
    client = _client()

    resp = client.create_agent_space(
        name="tagged-space",
        tags={"env": "test", "team": "platform"},
    )
    space_id = resp["agentSpace"]["agentSpaceId"]
    assert resp.get("tags") == {"env": "test", "team": "platform"}

    resp = client.get_agent_space(agentSpaceId=space_id)
    assert resp["tags"] == {"env": "test", "team": "platform"}

    # Build the ARN for tag operations
    sts = boto3.client("sts", region_name=REGION)
    account_id = sts.get_caller_identity()["Account"]
    arn = f"arn:aws:aidevops:{REGION}:{account_id}:agentspace/{space_id}"

    resp = client.list_tags_for_resource(resourceArn=arn)
    assert resp["tags"] == {"env": "test", "team": "platform"}

    client.tag_resource(resourceArn=arn, tags={"version": "1"})
    resp = client.list_tags_for_resource(resourceArn=arn)
    assert resp["tags"] == {"env": "test", "team": "platform", "version": "1"}

    client.untag_resource(resourceArn=arn, tagKeys=["team"])
    resp = client.list_tags_for_resource(resourceArn=arn)
    assert resp["tags"] == {"env": "test", "version": "1"}


@mock_aws
def test_not_found():
    client = _client()

    with pytest.raises(ClientError) as exc:
        client.get_agent_space(agentSpaceId="as-nonexistent")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"

    with pytest.raises(ClientError) as exc:
        client.update_agent_space(agentSpaceId="as-nonexistent", name="x")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"

    with pytest.raises(ClientError) as exc:
        client.delete_agent_space(agentSpaceId="as-nonexistent")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
