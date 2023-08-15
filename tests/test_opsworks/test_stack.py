import boto3
import pytest

from moto import mock_opsworks


@mock_opsworks
def test_create_stack_response():
    client = boto3.client("opsworks", region_name="us-east-1")
    response = client.create_stack(
        Name="test_stack_1",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn",
    )
    assert "StackId" in response


@mock_opsworks
def test_describe_stacks():
    client = boto3.client("opsworks", region_name="us-east-1")
    for i in range(1, 4):
        client.create_stack(
            Name=f"test_stack_{i}",
            Region="us-east-1",
            ServiceRoleArn="service_arn",
            DefaultInstanceProfileArn="profile_arn",
        )

    response = client.describe_stacks()
    assert len(response["Stacks"]) == 3
    for stack in response["Stacks"]:
        assert stack["ServiceRoleArn"] == "service_arn"
        assert stack["DefaultInstanceProfileArn"] == "profile_arn"

    _id = response["Stacks"][0]["StackId"]
    response = client.describe_stacks(StackIds=[_id])
    assert len(response["Stacks"]) == 1
    assert _id in response["Stacks"][0]["Arn"]

    # ClientError/ResourceNotFoundException
    with pytest.raises(Exception) as exc:
        client.describe_stacks(StackIds=["foo"])
    assert r"foo" in exc.value.response["Error"]["Message"]
