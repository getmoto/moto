import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_get_initial_policy():
    client = boto3.client("secretsmanager", region_name="us-west-2")
    client.create_secret(Name="test-secret")

    resp = client.get_resource_policy(SecretId="test-secret")
    assert resp.get("Name") == "test-secret"
    assert "ARN" in resp
    assert "ResourcePolicy" not in resp


@mock_aws
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


@mock_aws
def test_delete_resource_policy():
    client = boto3.client("secretsmanager", region_name="us-west-2")
    client.create_secret(Name="test-secret")

    client.put_resource_policy(SecretId="test-secret", ResourcePolicy="some policy")

    client.delete_resource_policy(SecretId="test-secret")

    resp = client.get_resource_policy(SecretId="test-secret")
    assert "ResourcePolicy" not in resp


@mock_aws
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


@mock_aws
def test_validate_resource_policy():
    client = boto3.client("secretsmanager", region_name="us-west-2")

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                "Action": "secretsmanager:GetSecretValue",
                "Resource": "*",
            }
        ],
    }
    resp = client.validate_resource_policy(ResourcePolicy=json.dumps(policy))
    assert resp["PolicyValidationPassed"] is True
    assert resp["ValidationErrors"] == []


@mock_aws
def test_validate_resource_policy_for_secret():
    client = boto3.client("secretsmanager", region_name="us-west-2")
    arn = client.create_secret(Name="test-secret")["ARN"]

    policy = {
        "Statement": {
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
            "Action": ["secretsmanager:GetSecretValue"],
            "Resource": "*",
        },
    }
    for secret_id in ["test-secret", arn]:
        resp = client.validate_resource_policy(
            SecretId=secret_id, ResourcePolicy=json.dumps(policy)
        )
        assert resp["PolicyValidationPassed"] is True
        assert resp["ValidationErrors"] == []

    # Validating a policy does not attach it to the secret
    resp = client.get_resource_policy(SecretId="test-secret")
    assert "ResourcePolicy" not in resp


@mock_aws
def test_validate_resource_policy_for_unknown_secret():
    client = boto3.client("secretsmanager", region_name="us-west-2")

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": "secretsmanager:*", "Resource": "*"}
        ],
    }
    with pytest.raises(ClientError) as exc:
        client.validate_resource_policy(
            SecretId="unknown secret", ResourcePolicy=json.dumps(policy)
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@pytest.mark.parametrize(
    "policy",
    [
        "some policy",
        json.dumps({"Version": "2012-10-17"}),
        json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [{"Action": "secretsmanager:*", "Resource": "*"}],
            }
        ),
        json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {"Effect": "Allow", "Action": "secretsmanager:*", "Unknown": "*"}
                ],
            }
        ),
    ],
    ids=["invalid-json", "no-statement", "no-effect", "unknown-element"],
)
@mock_aws
def test_validate_resource_policy_with_malformed_policy(policy):
    client = boto3.client("secretsmanager", region_name="us-west-2")

    with pytest.raises(ClientError) as exc:
        client.validate_resource_policy(ResourcePolicy=policy)
    err = exc.value.response["Error"]
    assert err["Code"] == "MalformedPolicyDocumentException"
    assert err["Message"] == "The resource policy has syntax errors."
