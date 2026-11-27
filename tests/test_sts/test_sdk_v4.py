"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

import json
from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_iam import IAMClient, IAMConfig
    from aws_sdk_sts import STSClient, STSConfig
except ImportError:  # Requires Python 3.12+
    pytest.skip(
        "aws-sdk-sts and aws-sdk-iam are not installed", allow_module_level=True
    )

from tests import DEFAULT_ACCOUNT_ID


@mock_aws
def test_assume_deployment_role():
    """Assume a role, and use the temporary credentials to make a new request."""
    role_name = f"deployer-{uuid4().hex[:8]}"
    session_name = "ci-pipeline"
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{DEFAULT_ACCOUNT_ID}:root"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    with IAMClient(config=IAMConfig.resolve(region="us-east-1")) as iam:
        role = iam.create_role(
            role_name=role_name,
            assume_role_policy_document=json.dumps(trust_policy),
        ).role

    with STSClient(config=STSConfig.resolve(region="us-east-1")) as client:
        identity = client.get_caller_identity()
        assert identity.account == DEFAULT_ACCOUNT_ID
        assert identity.arn == f"arn:aws:sts::{DEFAULT_ACCOUNT_ID}:user/moto"

        assumed = client.assume_role(
            role_arn=role.arn,
            role_session_name=session_name,
            duration_seconds=900,
            tags=[{"key": "team", "value": "platform"}],
        )
        assert assumed.assumed_role_user.arn == (
            f"arn:aws:sts::{DEFAULT_ACCOUNT_ID}:assumed-role/{role_name}/{session_name}"
        )
        assert (
            assumed.assumed_role_user.assumed_role_id
            == f"{role.role_id}:{session_name}"
        )
        credentials = assumed.credentials
        assert credentials.access_key_id.startswith("ASIA")
        assert credentials.secret_access_key
        assert credentials.session_token

    # Use the temporary credentials, the way a deployment script would
    role_config = STSConfig.resolve(
        region="us-east-1",
        aws_access_key_id=credentials.access_key_id,
        aws_secret_access_key=credentials.secret_access_key,
        aws_session_token=credentials.session_token,
    )
    with STSClient(config=role_config) as role_client:
        role_identity = role_client.get_caller_identity()
        assert role_identity.account == DEFAULT_ACCOUNT_ID
        assert role_identity.arn == assumed.assumed_role_user.arn
        assert role_identity.user_id == f"{role.role_id}:{session_name}"
