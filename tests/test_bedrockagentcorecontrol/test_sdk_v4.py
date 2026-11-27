"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_bedrock_agentcore_control import (
        BedrockAgentCoreControlClient,
        BedrockAgentCoreControlConfig,
    )
    from aws_sdk_bedrock_agentcore_control.models import ResourceNotFoundException
except ImportError:  # Requires Python 3.12+
    pytest.skip(
        "aws-sdk-bedrock-agentcore-control is not installed", allow_module_level=True
    )


@mock_aws
def test_deploy_and_roll_out_agent_runtime():
    """Deploy a containerized agent, expose it via an endpoint, and roll out a new version."""
    config = BedrockAgentCoreControlConfig.resolve(region="us-east-1")
    runtime_name = f"support_agent_{uuid4().hex[:8]}"
    image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/support-agent"
    runtime_settings = {
        "role_arn": "arn:aws:iam::123456789012:role/AgentRuntimeRole",
        "network_configuration": {"network_mode": "PUBLIC"},
    }

    with BedrockAgentCoreControlClient(config=config) as client:
        created = client.create_agent_runtime(
            agent_runtime_name=runtime_name,
            agent_runtime_artifact={
                "container_configuration": {"container_uri": f"{image}:v1"}
            },
            description="Customer support agent",
            environment_variables={"LOG_LEVEL": "INFO"},
            tags={"team": "support"},
            **runtime_settings,
        )
        runtime_id = created.agent_runtime_id
        assert created.agent_runtime_version == "1"

        runtime = client.get_agent_runtime(agent_runtime_id=runtime_id)
        assert runtime.agent_runtime_name == runtime_name
        assert runtime.status == "READY"
        assert runtime.agent_runtime_artifact.value.container_uri == f"{image}:v1"
        assert runtime.environment_variables == {"LOG_LEVEL": "INFO"}

        endpoint = client.create_agent_runtime_endpoint(
            agent_runtime_id=runtime_id,
            name="production",
            agent_runtime_version="1",
        )
        assert endpoint.target_version == "1"

        # Roll out a new container image, and point the production endpoint at it
        updated = client.update_agent_runtime(
            agent_runtime_id=runtime_id,
            agent_runtime_artifact={
                "container_configuration": {"container_uri": f"{image}:v2"}
            },
            **runtime_settings,
        )
        assert updated.agent_runtime_version == "2"
        versions = client.list_agent_runtime_versions(agent_runtime_id=runtime_id)
        assert [v.agent_runtime_version for v in versions.agent_runtimes] == ["2", "1"]

        client.update_agent_runtime_endpoint(
            agent_runtime_id=runtime_id,
            endpoint_name="production",
            agent_runtime_version="2",
        )
        endpoint = client.get_agent_runtime_endpoint(
            agent_runtime_id=runtime_id, endpoint_name="production"
        )
        assert endpoint.target_version == "2"
        endpoints = client.list_agent_runtime_endpoints(agent_runtime_id=runtime_id)
        assert [e.name for e in endpoints.runtime_endpoints] == ["production"]

        tags = client.list_tags_for_resource(resource_arn=created.agent_runtime_arn)
        assert tags.tags == {"team": "support"}

        client.delete_agent_runtime_endpoint(
            agent_runtime_id=runtime_id, endpoint_name="production"
        )
        deleted = client.delete_agent_runtime(agent_runtime_id=runtime_id)
        assert deleted.status == "DELETING"
        with pytest.raises(ResourceNotFoundException):
            client.get_agent_runtime(agent_runtime_id=runtime_id)
