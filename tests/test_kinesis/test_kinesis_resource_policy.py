import json

import boto3

from moto import mock_aws


def get_policy_doc(action, stream_arn):
    sts = boto3.client("sts", "us-east-1")
    account_id = sts.get_caller_identity()["Account"]

    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Principal": {"AWS": account_id},
                "Effect": "Allow",
                "Action": [action],
                "Resource": f"{stream_arn}",
            }
        ],
    }
    return json.dumps(policy_doc)


@mock_aws
def test_put_resource_policy():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)
    resp = client.describe_stream(StreamName="my-stream")
    desc = resp["StreamDescription"]
    stream_arn = desc["StreamARN"]
    
    action = "kinesis:*"
    json_policy_doc = get_policy_doc(action, stream_arn)
    client.put_resource_policy(ResourceARN=stream_arn, Policy=json_policy_doc)
    response = client.get_resource_policy(ResourceARN=stream_arn)

    assert response["Policy"] == json_policy_doc


@mock_aws
def test_delete_resource_policy():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)
    resp = client.describe_stream(StreamName="my-stream")
    desc = resp["StreamDescription"]
    stream_arn = desc["StreamARN"]
    action = "kinesis:*"
    json_policy_doc = get_policy_doc(action, stream_arn)
    client.put_resource_policy(ResourceARN=stream_arn, Policy=json_policy_doc)
    response = client.get_resource_policy(ResourceARN=stream_arn)
    assert response["Policy"] == json_policy_doc

    client.delete_resource_policy(ResourceARN=stream_arn)
    response = client.get_resource_policy(ResourceARN=stream_arn)
    assert response["Policy"] == "{}"