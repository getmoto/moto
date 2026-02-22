"""Unit tests for bedrock-agentcore-control-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

TEST_REGION = "us-east-1"

RUNTIME_ARTIFACT = {
    "containerConfiguration": {
        "containerUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-agent:latest"
    }
}
NETWORK_CONFIG = {"networkMode": "PUBLIC"}
ROLE_ARN = "arn:aws:iam::123456789012:role/AgentRuntimeRole"


def _create_client():
    return boto3.client("bedrock-agentcore-control", region_name=TEST_REGION)


@mock_aws
def test_create_agent_runtime():
    client = _create_client()
    resp = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
        description="Test runtime",
    )
    assert resp["agentRuntimeId"] is not None
    assert (
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:agent/"
        in resp["agentRuntimeArn"]
    )
    assert resp["agentRuntimeVersion"] == "1"
    assert resp["status"] == "CREATING"
    assert "workloadIdentityDetails" in resp


@mock_aws
def test_create_agent_runtime_with_tags():
    client = _create_client()
    tags = {"env": "test", "project": "agentcore"}
    resp = client.create_agent_runtime(
        agentRuntimeName="tagged_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
        tags=tags,
    )
    arn = resp["agentRuntimeArn"]
    tag_resp = client.list_tags_for_resource(resourceArn=arn)
    assert tag_resp["tags"] == tags


@mock_aws
def test_get_agent_runtime():
    client = _create_client()
    create_resp = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
        description="Test runtime",
    )
    runtime_id = create_resp["agentRuntimeId"]

    get_resp = client.get_agent_runtime(agentRuntimeId=runtime_id)
    assert get_resp["agentRuntimeId"] == runtime_id
    assert get_resp["agentRuntimeName"] == "my_runtime"
    assert get_resp["roleArn"] == ROLE_ARN
    assert get_resp["networkConfiguration"] == NETWORK_CONFIG
    assert get_resp["agentRuntimeArtifact"] == RUNTIME_ARTIFACT
    assert get_resp["description"] == "Test runtime"
    # ManagedState should advance CREATING -> READY
    assert get_resp["status"] == "READY"


@mock_aws
def test_get_agent_runtime_not_found():
    client = _create_client()
    with pytest.raises(ClientError) as exc:
        client.get_agent_runtime(agentRuntimeId="nonexistent_id-abc1234567")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_update_agent_runtime():
    client = _create_client()
    create_resp = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    runtime_id = create_resp["agentRuntimeId"]

    new_artifact = {
        "containerConfiguration": {
            "containerUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-agent:v2"
        }
    }
    update_resp = client.update_agent_runtime(
        agentRuntimeId=runtime_id,
        agentRuntimeArtifact=new_artifact,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
        description="Updated runtime",
    )
    assert update_resp["agentRuntimeVersion"] == "2"
    assert update_resp["status"] == "UPDATING"

    get_resp = client.get_agent_runtime(agentRuntimeId=runtime_id)
    assert get_resp["agentRuntimeArtifact"] == new_artifact
    assert get_resp["description"] == "Updated runtime"


@mock_aws
def test_delete_agent_runtime():
    client = _create_client()
    create_resp = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    runtime_id = create_resp["agentRuntimeId"]

    del_resp = client.delete_agent_runtime(agentRuntimeId=runtime_id)
    assert del_resp["status"] == "DELETING"
    assert del_resp["agentRuntimeId"] == runtime_id

    with pytest.raises(ClientError) as exc:
        client.get_agent_runtime(agentRuntimeId=runtime_id)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_agent_runtimes():
    client = _create_client()

    # Start with empty list
    resp = client.list_agent_runtimes()
    assert resp["agentRuntimes"] == []

    # Create two runtimes
    client.create_agent_runtime(
        agentRuntimeName="runtime_one",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    client.create_agent_runtime(
        agentRuntimeName="runtime_two",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )

    resp = client.list_agent_runtimes()
    assert len(resp["agentRuntimes"]) == 2
    names = {r["agentRuntimeName"] for r in resp["agentRuntimes"]}
    assert names == {"runtime_one", "runtime_two"}


@mock_aws
def test_list_agent_runtime_versions():
    client = _create_client()
    create_resp = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    runtime_id = create_resp["agentRuntimeId"]

    # Update to create version 2
    client.update_agent_runtime(
        agentRuntimeId=runtime_id,
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
        description="v2",
    )

    resp = client.list_agent_runtime_versions(agentRuntimeId=runtime_id)
    versions = resp["agentRuntimes"]
    assert len(versions) == 2
    # Most recent version first
    assert versions[0]["agentRuntimeVersion"] == "2"
    assert versions[1]["agentRuntimeVersion"] == "1"


@mock_aws
def test_create_agent_runtime_endpoint():
    client = _create_client()
    runtime = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    runtime_id = runtime["agentRuntimeId"]

    resp = client.create_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        name="my_endpoint",
        description="Test endpoint",
    )
    assert resp["endpointName"] == "my_endpoint"
    assert resp["agentRuntimeId"] == runtime_id
    assert resp["status"] == "CREATING"
    assert "agentRuntimeEndpointArn" in resp
    assert resp["targetVersion"] == "1"


@mock_aws
def test_create_agent_runtime_endpoint_conflict():
    client = _create_client()
    runtime = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    runtime_id = runtime["agentRuntimeId"]

    client.create_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        name="my_endpoint",
    )
    with pytest.raises(ClientError) as exc:
        client.create_agent_runtime_endpoint(
            agentRuntimeId=runtime_id,
            name="my_endpoint",
        )
    assert exc.value.response["Error"]["Code"] == "ConflictException"


@mock_aws
def test_get_agent_runtime_endpoint():
    client = _create_client()
    runtime = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    runtime_id = runtime["agentRuntimeId"]

    client.create_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        name="my_endpoint",
        description="Test endpoint",
    )

    get_resp = client.get_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        endpointName="my_endpoint",
    )
    assert get_resp["name"] == "my_endpoint"
    assert get_resp["status"] == "READY"  # ManagedState advances
    assert "id" in get_resp
    assert "agentRuntimeEndpointArn" in get_resp


@mock_aws
def test_get_agent_runtime_endpoint_not_found():
    client = _create_client()
    runtime = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    runtime_id = runtime["agentRuntimeId"]

    with pytest.raises(ClientError) as exc:
        client.get_agent_runtime_endpoint(
            agentRuntimeId=runtime_id,
            endpointName="nonexistent",
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_update_agent_runtime_endpoint():
    client = _create_client()
    runtime = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    runtime_id = runtime["agentRuntimeId"]

    client.create_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        name="my_endpoint",
    )

    update_resp = client.update_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        endpointName="my_endpoint",
        description="Updated endpoint",
    )
    assert update_resp["status"] == "UPDATING"


@mock_aws
def test_delete_agent_runtime_endpoint():
    client = _create_client()
    runtime = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    runtime_id = runtime["agentRuntimeId"]

    client.create_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        name="my_endpoint",
    )

    del_resp = client.delete_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        endpointName="my_endpoint",
    )
    assert del_resp["status"] == "DELETING"

    with pytest.raises(ClientError) as exc:
        client.get_agent_runtime_endpoint(
            agentRuntimeId=runtime_id,
            endpointName="my_endpoint",
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_agent_runtime_endpoints():
    client = _create_client()
    runtime = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    runtime_id = runtime["agentRuntimeId"]

    resp = client.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
    assert resp["runtimeEndpoints"] == []

    client.create_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        name="endpoint_one",
    )
    client.create_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        name="endpoint_two",
    )

    resp = client.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
    assert len(resp["runtimeEndpoints"]) == 2
    names = {ep["name"] for ep in resp["runtimeEndpoints"]}
    assert names == {"endpoint_one", "endpoint_two"}


@mock_aws
def test_tag_resource():
    client = _create_client()
    runtime = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    arn = runtime["agentRuntimeArn"]

    client.tag_resource(resourceArn=arn, tags={"key1": "val1", "key2": "val2"})
    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert tags == {"key1": "val1", "key2": "val2"}


@mock_aws
def test_untag_resource():
    client = _create_client()
    runtime = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
        tags={"key1": "val1", "key2": "val2"},
    )
    arn = runtime["agentRuntimeArn"]

    client.untag_resource(resourceArn=arn, tagKeys=["key1"])
    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert tags == {"key2": "val2"}


@mock_aws
def test_delete_agent_runtime_removes_endpoints():
    client = _create_client()
    runtime = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    runtime_id = runtime["agentRuntimeId"]

    client.create_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        name="ep1",
    )
    client.delete_agent_runtime(agentRuntimeId=runtime_id)

    # After deletion, both the runtime and its endpoints should be gone
    with pytest.raises(ClientError) as exc:
        client.get_agent_runtime(agentRuntimeId=runtime_id)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
