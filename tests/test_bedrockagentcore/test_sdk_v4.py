"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_bedrock_agentcore import BedrockAgentCoreClient, BedrockAgentCoreConfig
    from aws_sdk_bedrock_agentcore.models import (
        PayloadTypeConversational,
        ResourceNotFoundException,
    )
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-bedrock-agentcore is not installed", allow_module_level=True)


@mock_aws
def test_agent_conversation_memory():
    """Store the turns of a chat session in AgentCore Memory, read the history back, and forget a turn."""
    config = BedrockAgentCoreConfig.resolve(region="us-east-1")
    memory_id = f"ChatMemory-{str(uuid4())[:10]}"
    session = {"memory_id": memory_id, "actor_id": "customer-42", "session_id": "s-1"}
    conversation = [
        ("USER", "My order hasn't arrived yet."),
        ("ASSISTANT", "Sorry to hear that! What is your order number?"),
        ("USER", "It's order 1234."),
    ]

    with BedrockAgentCoreClient(config=config) as client:
        event_ids = []
        for role, text in conversation:
            event = client.create_event(
                **session,
                event_timestamp=datetime.now(timezone.utc),
                payload=[{"conversational": {"content": {"text": text}, "role": role}}],
                metadata={"channel": {"string_value": "web-chat"}},
            ).event
            assert event.memory_id == memory_id
            assert event.branch.name == "main"
            event_ids.append(event.event_id)

        history = client.list_events(**session, include_payloads=True).events
        assert [e.event_id for e in history] == event_ids
        turns = []
        for event in history:
            payload = event.payload[0]
            assert isinstance(payload, PayloadTypeConversational)
            turns.append((payload.value.role, payload.value.content.value))
        assert turns == conversation

        first = client.get_event(**session, event_id=event_ids[0]).event
        assert first.payload[0].value.content.value == "My order hasn't arrived yet."
        assert first.metadata["channel"].value == "web-chat"

        deleted = client.delete_event(**session, event_id=event_ids[0])
        assert deleted.event_id == event_ids[0]
        with pytest.raises(ResourceNotFoundException):
            client.get_event(**session, event_id=event_ids[0])
        remaining = client.list_events(**session).events
        assert [e.event_id for e in remaining] == event_ids[1:]
