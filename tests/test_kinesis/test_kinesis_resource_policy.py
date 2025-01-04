import json

import boto3
import pytest
from botocore.exceptions import ClientError

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


@mock_aws
def test_get_resource_policy_from_unknown_resource():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)
    resp = client.describe_stream(StreamName="my-stream")
    desc = resp["StreamDescription"]
    stream_arn = desc["StreamARN"] + "unknown"
    sts = boto3.client("sts", "us-east-1")
    account_id = sts.get_caller_identity()["Account"]
    with pytest.raises(ClientError) as exc:
        client.get_resource_policy(ResourceARN=stream_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"] == f"Stream {stream_arn} under account {account_id} not found."
    )


@mock_aws
def test_delete_resource_policy_from_unknown_resource():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)
    resp = client.describe_stream(StreamName="my-stream")
    desc = resp["StreamDescription"]
    stream_arn = desc["StreamARN"] + "unknown"
    sts = boto3.client("sts", "us-east-1")
    account_id = sts.get_caller_identity()["Account"]
    with pytest.raises(ClientError) as exc:
        client.delete_resource_policy(ResourceARN=stream_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"] == f"Stream {stream_arn} under account {account_id} not found."
    )


@mock_aws
def test_delete_resource_policy_from_resource_without_policy():
    client = boto3.client("kinesis", region_name="us-west-2")
    client.create_stream(StreamName="my-stream", ShardCount=2)
    resp = client.describe_stream(StreamName="my-stream")
    desc = resp["StreamDescription"]
    stream_arn = desc["StreamARN"]
    with pytest.raises(ClientError) as exc:
        client.delete_resource_policy(ResourceARN=stream_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"No resource policy found for resource ARN {stream_arn}."
