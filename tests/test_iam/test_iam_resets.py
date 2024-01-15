import json
import os
from unittest import SkipTest, mock

import boto3

from moto import mock_aws, settings


# Test IAM User Inline Policy
def test_policies_are_not_kept_after_mock_ends():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Policies not loaded in ServerMode")
    with mock_aws(config={"iam": {"load_aws_managed_policies": True}}):
        iam_client = boto3.client("iam", "us-east-1")
        role_name = "test"
        assume_role_policy_document = {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "sts:AssumeRole",
            },
        }
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
        )
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/ReadOnlyAccess",
        )

        iam_policies = iam_client.list_policies(Scope="AWS", OnlyAttached=True)[
            "Policies"
        ]
        assert len(iam_policies) == 1
        assert iam_policies[0]["Arn"] == "arn:aws:iam::aws:policy/ReadOnlyAccess"
        assert iam_client.list_roles()["Roles"][0]["RoleName"] == "test"

    with mock_aws(config={"iam": {"load_aws_managed_policies": True}}):
        resp = iam_client.list_policies(Scope="AWS", OnlyAttached=True)
        assert len(resp["Policies"]) == 0


def test_policies_are_loaded_when_using_env_variable():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("EnvVar not loaded in ServerMode")
    with mock.patch.dict(os.environ, {"MOTO_IAM_LOAD_MANAGED_POLICIES": "true"}):
        with mock_aws():
            iam_client = boto3.client("iam", "us-east-1")

            iam_policies = iam_client.list_policies(Scope="AWS")["Policies"]
            assert len(iam_policies) > 10
