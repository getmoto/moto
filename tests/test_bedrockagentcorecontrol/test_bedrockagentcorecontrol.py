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
    assert get_resp["description"] == "Test endpoint"
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


@mock_aws
def test_create_agent_runtime_with_optional_fields():
    client = _create_client()
    protocol_config = {"serverProtocol": "HTTP_2"}
    env_vars = {"VAR1": "value1", "VAR2": "value2"}
    auth_config = {
        "customJWTAuthorizer": {
            "discoveryUrl": "https://example.com/.well-known/jwks.json"
        }
    }
    header_config = {"requestHeaderAllowlist": ["Authorization", "X-Custom-Header"]}

    create_resp = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
        protocolConfiguration=protocol_config,
        environmentVariables=env_vars,
        authorizerConfiguration=auth_config,
        requestHeaderConfiguration=header_config,
    )
    runtime_id = create_resp["agentRuntimeId"]

    get_resp = client.get_agent_runtime(agentRuntimeId=runtime_id)
    assert get_resp["protocolConfiguration"] == protocol_config
    assert get_resp["environmentVariables"] == env_vars
    assert get_resp["authorizerConfiguration"] == auth_config
    assert get_resp["requestHeaderConfiguration"] == header_config


@mock_aws
def test_update_agent_runtime_with_optional_fields():
    client = _create_client()
    create_resp = client.create_agent_runtime(
        agentRuntimeName="my_runtime",
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
    )
    runtime_id = create_resp["agentRuntimeId"]

    protocol_config = {"serverProtocol": "HTTP_2"}
    env_vars = {"ENV1": "val1"}
    auth_config = {
        "customJWTAuthorizer": {
            "discoveryUrl": "https://example.com/.well-known/jwks.json"
        }
    }
    header_config = {"requestHeaderAllowlist": ["X-API-Key"]}
    lifecycle_config = {"idleRuntimeSessionTimeout": 1800}

    client.update_agent_runtime(
        agentRuntimeId=runtime_id,
        agentRuntimeArtifact=RUNTIME_ARTIFACT,
        roleArn=ROLE_ARN,
        networkConfiguration=NETWORK_CONFIG,
        description="Updated with all fields",
        protocolConfiguration=protocol_config,
        environmentVariables=env_vars,
        authorizerConfiguration=auth_config,
        requestHeaderConfiguration=header_config,
        lifecycleConfiguration=lifecycle_config,
    )

    get_resp = client.get_agent_runtime(agentRuntimeId=runtime_id)
    assert get_resp["description"] == "Updated with all fields"
    assert get_resp["protocolConfiguration"] == protocol_config
    assert get_resp["environmentVariables"] == env_vars
    assert get_resp["authorizerConfiguration"] == auth_config
    assert get_resp["requestHeaderConfiguration"] == header_config
    assert get_resp["lifecycleConfiguration"] == lifecycle_config


GATEWAY_ROLE_ARN = "arn:aws:iam::123456789012:role/GatewayRole"
TARGET_CONFIG = {"mcp": {"mcpServer": {"endpoint": "https://example.com/mcp"}}}
CREDENTIAL_PROVIDER_CONFIGS = [
    {
        "credentialProviderType": "GATEWAY_IAM_ROLE",
    }
]


@mock_aws
def test_create_gateway():
    client = _create_client()
    resp = client.create_gateway(
        name="my-gateway",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
        description="Test gateway",
    )
    assert resp["gatewayId"] is not None
    assert resp["name"] == "my-gateway"
    assert resp["protocolType"] == "MCP"
    assert resp["authorizerType"] == "NONE"
    assert resp["status"] == "CREATING"
    assert "gatewayArn" in resp
    assert "gatewayUrl" in resp
    assert "workloadIdentityDetails" in resp


@mock_aws
def test_get_gateway():
    client = _create_client()
    create_resp = client.create_gateway(
        name="my-gateway",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
        description="Test gateway",
    )
    gateway_id = create_resp["gatewayId"]

    get_resp = client.get_gateway(gatewayIdentifier=gateway_id)
    assert get_resp["gatewayId"] == gateway_id
    assert get_resp["name"] == "my-gateway"
    assert get_resp["description"] == "Test gateway"
    assert get_resp["roleArn"] == GATEWAY_ROLE_ARN
    assert get_resp["status"] == "READY"


@mock_aws
def test_get_gateway_not_found():
    client = _create_client()
    with pytest.raises(ClientError) as exc:
        client.get_gateway(gatewayIdentifier="nonexistent0")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_update_gateway():
    client = _create_client()
    create_resp = client.create_gateway(
        name="my-gateway",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
    )
    gateway_id = create_resp["gatewayId"]

    update_resp = client.update_gateway(
        gatewayIdentifier=gateway_id,
        name="updated-gateway",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
        description="Updated",
    )
    assert update_resp["status"] == "UPDATING"
    assert update_resp["name"] == "updated-gateway"

    get_resp = client.get_gateway(gatewayIdentifier=gateway_id)
    assert get_resp["name"] == "updated-gateway"
    assert get_resp["description"] == "Updated"


@mock_aws
def test_delete_gateway():
    client = _create_client()
    create_resp = client.create_gateway(
        name="my-gateway",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
    )
    gateway_id = create_resp["gatewayId"]

    del_resp = client.delete_gateway(gatewayIdentifier=gateway_id)
    assert del_resp["status"] == "DELETING"
    assert del_resp["gatewayId"] == gateway_id

    with pytest.raises(ClientError) as exc:
        client.get_gateway(gatewayIdentifier=gateway_id)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_gateways():
    client = _create_client()

    resp = client.list_gateways()
    assert resp["items"] == []

    client.create_gateway(
        name="gw-one",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
    )
    client.create_gateway(
        name="gw-two",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
    )

    resp = client.list_gateways()
    assert len(resp["items"]) == 2
    names = {g["name"] for g in resp["items"]}
    assert names == {"gw-one", "gw-two"}


@mock_aws
def test_create_gateway_target():
    client = _create_client()
    gw = client.create_gateway(
        name="my-gateway",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
    )
    gateway_id = gw["gatewayId"]

    resp = client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="my-target",
        targetConfiguration=TARGET_CONFIG,
        credentialProviderConfigurations=CREDENTIAL_PROVIDER_CONFIGS,
        description="Test target",
    )
    assert resp["targetId"] is not None
    assert resp["name"] == "my-target"
    assert resp["status"] == "CREATING"
    assert resp["targetConfiguration"] == TARGET_CONFIG
    assert "gatewayArn" in resp


@mock_aws
def test_get_gateway_target():
    client = _create_client()
    gw = client.create_gateway(
        name="my-gateway",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
    )
    gateway_id = gw["gatewayId"]

    create_resp = client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="my-target",
        targetConfiguration=TARGET_CONFIG,
        credentialProviderConfigurations=CREDENTIAL_PROVIDER_CONFIGS,
        description="Test target",
    )
    target_id = create_resp["targetId"]

    get_resp = client.get_gateway_target(
        gatewayIdentifier=gateway_id,
        targetId=target_id,
    )
    assert get_resp["targetId"] == target_id
    assert get_resp["name"] == "my-target"
    assert get_resp["status"] == "READY"
    assert get_resp["description"] == "Test target"


@mock_aws
def test_get_gateway_target_not_found():
    client = _create_client()
    gw = client.create_gateway(
        name="my-gateway",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
    )
    gateway_id = gw["gatewayId"]

    with pytest.raises(ClientError) as exc:
        client.get_gateway_target(
            gatewayIdentifier=gateway_id,
            targetId="nonexist00",
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_update_gateway_target():
    client = _create_client()
    gw = client.create_gateway(
        name="my-gateway",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
    )
    gateway_id = gw["gatewayId"]

    create_resp = client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="my-target",
        targetConfiguration=TARGET_CONFIG,
        credentialProviderConfigurations=CREDENTIAL_PROVIDER_CONFIGS,
    )
    target_id = create_resp["targetId"]

    new_config = {"mcp": {"mcpServer": {"endpoint": "https://example.com/mcp-v2"}}}
    update_resp = client.update_gateway_target(
        gatewayIdentifier=gateway_id,
        targetId=target_id,
        name="updated-target",
        targetConfiguration=new_config,
        description="Updated target",
    )
    assert update_resp["status"] == "UPDATING"

    get_resp = client.get_gateway_target(
        gatewayIdentifier=gateway_id,
        targetId=target_id,
    )
    assert get_resp["name"] == "updated-target"
    assert get_resp["targetConfiguration"] == new_config
    assert get_resp["description"] == "Updated target"


@mock_aws
def test_delete_gateway_target():
    client = _create_client()
    gw = client.create_gateway(
        name="my-gateway",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
    )
    gateway_id = gw["gatewayId"]

    create_resp = client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="my-target",
        targetConfiguration=TARGET_CONFIG,
        credentialProviderConfigurations=CREDENTIAL_PROVIDER_CONFIGS,
    )
    target_id = create_resp["targetId"]

    del_resp = client.delete_gateway_target(
        gatewayIdentifier=gateway_id,
        targetId=target_id,
    )
    assert del_resp["status"] == "DELETING"
    assert del_resp["targetId"] == target_id

    with pytest.raises(ClientError) as exc:
        client.get_gateway_target(
            gatewayIdentifier=gateway_id,
            targetId=target_id,
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_gateway_targets():
    client = _create_client()
    gw = client.create_gateway(
        name="my-gateway",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
    )
    gateway_id = gw["gatewayId"]

    resp = client.list_gateway_targets(gatewayIdentifier=gateway_id)
    assert resp["items"] == []

    client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="target-one",
        targetConfiguration=TARGET_CONFIG,
        credentialProviderConfigurations=CREDENTIAL_PROVIDER_CONFIGS,
    )
    client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="target-two",
        targetConfiguration=TARGET_CONFIG,
        credentialProviderConfigurations=CREDENTIAL_PROVIDER_CONFIGS,
    )

    resp = client.list_gateway_targets(gatewayIdentifier=gateway_id)
    assert len(resp["items"]) == 2
    names = {t["name"] for t in resp["items"]}
    assert names == {"target-one", "target-two"}


@mock_aws
def test_delete_gateway_removes_targets():
    client = _create_client()
    gw = client.create_gateway(
        name="my-gateway",
        roleArn=GATEWAY_ROLE_ARN,
        protocolType="MCP",
        authorizerType="NONE",
    )
    gateway_id = gw["gatewayId"]

    client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="target-one",
        targetConfiguration=TARGET_CONFIG,
        credentialProviderConfigurations=CREDENTIAL_PROVIDER_CONFIGS,
    )
    client.delete_gateway(gatewayIdentifier=gateway_id)

    with pytest.raises(ClientError) as exc:
        client.get_gateway(gatewayIdentifier=gateway_id)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
