"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

import json
from urllib.parse import unquote
from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_iam import IAMClient, IAMConfig
    from aws_sdk_iam.models import DeleteConflictException, NoSuchEntityException
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-iam is not installed", allow_module_level=True)

from tests import DEFAULT_ACCOUNT_ID


@pytest.mark.skip(
    reason="Moto's DeletePolicy deletes a managed policy that is still attached to a role, "
    "instead of raising DeleteConflict like AWS does"
)
@mock_aws
def test_ec2_application_role():
    """Create a role for an application running on EC2, with managed and inline policies."""
    suffix = uuid4().hex[:8]
    role_name = f"web-app-{suffix}"
    policy_name = f"read-assets-{suffix}"
    profile_name = f"web-app-profile-{suffix}"
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    read_assets = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject"],
                "Resource": "arn:aws:s3:::assets/*",
            }
        ],
    }
    write_logs = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": "logs:PutLogEvents", "Resource": "*"}
        ],
    }

    with IAMClient(config=IAMConfig.resolve(region="us-east-1")) as client:
        role = client.create_role(
            role_name=role_name,
            path="/apps/",
            assume_role_policy_document=json.dumps(trust_policy),
            description="Role for the web application",
            tags=[{"key": "team", "value": "web"}],
        ).role
        assert role.arn == f"arn:aws:iam::{DEFAULT_ACCOUNT_ID}:role/apps/{role_name}"
        assert role.role_id.startswith("AROA")

        policy = client.create_policy(
            policy_name=policy_name, policy_document=json.dumps(read_assets)
        ).policy
        assert policy.arn == f"arn:aws:iam::{DEFAULT_ACCOUNT_ID}:policy/{policy_name}"
        assert policy.default_version_id == "v1"

        client.attach_role_policy(role_name=role_name, policy_arn=policy.arn)
        client.put_role_policy(
            role_name=role_name,
            policy_name="write-logs",
            policy_document=json.dumps(write_logs),
        )

        attached = client.list_attached_role_policies(role_name=role_name)
        assert [(p.policy_name, p.policy_arn) for p in attached.attached_policies] == [
            (policy_name, policy.arn)
        ]
        inline = client.get_role_policy(role_name=role_name, policy_name="write-logs")
        assert json.loads(unquote(inline.policy_document)) == write_logs

        client.create_instance_profile(instance_profile_name=profile_name)
        client.add_role_to_instance_profile(
            instance_profile_name=profile_name, role_name=role_name
        )
        profile = client.get_instance_profile(
            instance_profile_name=profile_name
        ).instance_profile
        assert [r.role_name for r in profile.roles] == [role_name]

        # A managed policy can't be deleted while it is still attached
        with pytest.raises(DeleteConflictException):
            client.delete_policy(policy_arn=policy.arn)

        # Tear everything down again
        client.remove_role_from_instance_profile(
            instance_profile_name=profile_name, role_name=role_name
        )
        client.delete_instance_profile(instance_profile_name=profile_name)
        client.detach_role_policy(role_name=role_name, policy_arn=policy.arn)
        client.delete_role_policy(role_name=role_name, policy_name="write-logs")
        client.delete_policy(policy_arn=policy.arn)
        client.delete_role(role_name=role_name)

        with pytest.raises(NoSuchEntityException):
            client.get_role(role_name=role_name)
