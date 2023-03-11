import boto3
import json
import pytest

from botocore.exceptions import ClientError
from moto import mock_secretsmanager


@mock_secretsmanager
def test_get_initial_policy():
    client = boto3.client("secretsmanager", region_name="us-west-2")
    client.create_secret(Name="test-secret")

    resp = client.get_resource_policy(SecretId="test-secret")
    assert resp.get("Name") == "test-secret"
    assert "ARN" in resp
    assert "ResourcePolicy" not in resp


@mock_secretsmanager
def test_put_resource_policy():
    client = boto3.client("secretsmanager", region_name="us-west-2")
    client.create_secret(Name="test-secret")

    policy = {
        "Statement": [
            {
                "Action": "secretsmanager:GetSecretValue",
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::123456789012:role/tf-acc-test-655046176950657276"
                },
                "Resource": "*",
                "Sid": "EnableAllPermissions",
            }
        ],
        "Version": "2012-10-17",
    }
    resp = client.put_resource_policy(
        SecretId="test-secret", ResourcePolicy=json.dumps(policy)
    )
    assert "ARN" in resp
    assert "Name" in resp

    resp = client.get_resource_policy(SecretId="test-secret")
    assert "ResourcePolicy" in resp
    assert json.loads(resp["ResourcePolicy"]) == policy


@mock_secretsmanager
def test_delete_resource_policy():
    client = boto3.client("secretsmanager", region_name="us-west-2")
    client.create_secret(Name="test-secret")

    client.put_resource_policy(SecretId="test-secret", ResourcePolicy="some policy")

    client.delete_resource_policy(SecretId="test-secret")

    resp = client.get_resource_policy(SecretId="test-secret")
    assert "ResourcePolicy" not in resp


@mock_secretsmanager
def test_policies_for_unknown_secrets():
    client = boto3.client("secretsmanager", region_name="us-west-2")

    with pytest.raises(ClientError) as exc:
        client.put_resource_policy(SecretId="unknown secret", ResourcePolicy="p")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"

    with pytest.raises(ClientError) as exc:
        client.get_resource_policy(SecretId="unknown secret")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"

    with pytest.raises(ClientError) as exc:
        client.delete_resource_policy(SecretId="unknown secret")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
