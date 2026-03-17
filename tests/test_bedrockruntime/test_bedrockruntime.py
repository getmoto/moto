import json

import boto3

from moto import mock_aws


@mock_aws
def test_invoke_model():
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    inference_parameters = {}
    resp = client.invoke_model(
        modelId="test-model-id",
        body=json.dumps(inference_parameters),
        performanceConfigLatency="optimized",
        serviceTier="flex",
    )
    assert resp["performanceConfigLatency"] == "optimized"
    assert resp["serviceTier"] == "flex"
