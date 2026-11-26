"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

import json

import pytest

from moto import mock_aws

try:
    from aws_sdk_bedrock_runtime import BedrockRuntimeClient, BedrockRuntimeConfig
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-bedrock-runtime is not installed", allow_module_level=True)


@mock_aws
def test_summarize_support_tickets():
    """Ask a foundation model to summarize support tickets, using different performance tiers."""
    config = BedrockRuntimeConfig.resolve(region="us-east-1")
    tickets = [
        "My order #1234 arrived damaged, I want a refund.",
        "How do I reset my password? The reset email never arrives.",
    ]

    with BedrockRuntimeClient(config=config) as client:
        summaries = []
        for ticket in tickets:
            request = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 200,
                "messages": [
                    {"role": "user", "content": f"Summarize in one line: {ticket}"}
                ],
            }
            response = client.invoke_model(
                model_id="anthropic.claude-3-haiku-20240307-v1:0",
                content_type="application/json",
                accept="application/json",
                body=json.dumps(request).encode(),
            )
            assert response.content_type == "application/json"
            assert response.performance_config_latency == "standard"
            assert response.service_tier == "default"
            # Moto does not run a model, and always returns an empty inference result
            summaries.append(json.loads(response.body))
        assert summaries == [{}, {}]

        # Latency-sensitive requests use the optimized, flex-tier configuration
        response = client.invoke_model(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            content_type="application/json",
            body=json.dumps(request).encode(),
            performance_config_latency="optimized",
            service_tier="flex",
        )
        assert response.performance_config_latency == "optimized"
        assert response.service_tier == "flex"
