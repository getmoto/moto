import boto3

from moto import mock_batch


@mock_batch
def test_create_with_tags():
    client = boto3.client("batch", "us-east-2")
    arn = client.create_scheduling_policy(name="test", tags={"key": "val"})["arn"]

    resp = client.describe_scheduling_policies(arns=[arn])

    policy = resp["schedulingPolicies"][0]
    policy["tags"].should.equal({"key": "val"})
