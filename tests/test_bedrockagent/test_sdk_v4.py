"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_bedrock_agent import BedrockAgentClient, BedrockAgentConfig
    from aws_sdk_bedrock_agent.models import ResourceNotFoundException
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-bedrock-agent is not installed", allow_module_level=True)


@pytest.mark.skip(
    reason="Moto returns createdAt/updatedAt/preparedAt as epoch numbers (unix_time()), "
    "but the service model uses timestampFormat date-time. botocore accepts both, "
    "the SDK v4 JSON deserializer only accepts an ISO-8601 string and fails on CreateKnowledgeBase"
)
@mock_aws
def test_support_agent_with_knowledge_base():
    """Create a knowledge base and an agent that answers questions using it, then tear both down."""
    config = BedrockAgentConfig.resolve(region="us-east-1")
    suffix = str(uuid4())[:8]
    role_arn = "arn:aws:iam::123456789012:role/AmazonBedrockExecutionRoleForAgents"

    with BedrockAgentClient(config=config) as client:
        knowledge_base = client.create_knowledge_base(
            name=f"product-docs-{suffix}",
            description="Product manuals",
            role_arn=role_arn,
            knowledge_base_configuration={
                "type": "VECTOR",
                "vector_knowledge_base_configuration": {
                    "embedding_model_arn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
                },
            },
            storage_configuration={
                "type": "OPENSEARCH_SERVERLESS",
                "opensearch_serverless_configuration": {
                    "collection_arn": "arn:aws:aoss:us-east-1:123456789012:collection/docs",
                    "vector_index_name": "product-docs",
                    "field_mapping": {
                        "vector_field": "embedding",
                        "text_field": "text",
                        "metadata_field": "metadata",
                    },
                },
            },
            tags={"team": "support"},
        ).knowledge_base
        kb_id = knowledge_base.knowledge_base_id
        assert knowledge_base.name == f"product-docs-{suffix}"
        assert knowledge_base.status == "Active"

        agent = client.create_agent(
            agent_name=f"support-agent-{suffix}",
            foundation_model="anthropic.claude-3-haiku-20240307-v1:0",
            instruction="You are a support agent. Answer questions using the product manuals.",
            idle_session_ttl_in_seconds=600,
            agent_resource_role_arn=role_arn,
        ).agent
        agent_id = agent.agent_id

        agent = client.get_agent(agent_id=agent_id).agent
        assert agent.agent_name == f"support-agent-{suffix}"
        assert agent.foundation_model == "anthropic.claude-3-haiku-20240307-v1:0"
        assert agent.idle_session_ttl_in_seconds == 600

        agents = client.list_agents().agent_summaries
        assert agent_id in [a.agent_id for a in agents]
        kbs = client.list_knowledge_bases().knowledge_base_summaries
        assert kb_id in [kb.knowledge_base_id for kb in kbs]

        client.tag_resource(resource_arn=agent.agent_arn, tags={"env": "prod"})
        tags = client.list_tags_for_resource(resource_arn=agent.agent_arn).tags
        assert tags == {"env": "prod"}
        kb_arn = knowledge_base.knowledge_base_arn
        client.untag_resource(resource_arn=kb_arn, tag_keys=["team"])
        assert not client.list_tags_for_resource(resource_arn=kb_arn).tags

        deleted = client.delete_agent(agent_id=agent_id)
        assert deleted.agent_status == "DELETING"
        with pytest.raises(ResourceNotFoundException):
            client.get_agent(agent_id=agent_id)

        deleted_kb = client.delete_knowledge_base(knowledge_base_id=kb_id)
        assert deleted_kb.status == "DELETING"
