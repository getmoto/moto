import boto3
import json
import pytest
from botocore.exceptions import ClientError
from unittest import mock

from moto import mock_kms
from moto.kms.exceptions import AccessDeniedException
from moto.kms.models import Key
from moto.kms.policy_validator import validate_policy
from cryptography.hazmat.primitives.asymmetric import rsa


@mock_kms
class TestKMSPolicyEnforcement:
    def setup_method(self, *args) -> None:  # pylint: disable=unused-argument
        self.client = boto3.client("kms", "us-east-1")

        # The key-value is irrelevant, so let's mock the expensive cryptographic key-generation
        # Patching does not work in ServerMode, but at least decorator tests times are improved
        with mock.patch.object(rsa, "generate_private_key", return_value=""):
            new_key = self.client.create_key(Description="t", Origin="AWS_KMS")
        self.key_id = new_key["KeyMetadata"]["KeyId"]

    @pytest.mark.parametrize(
        "actions",
        [["kms:*"], ["kms:unknown", "kms:*"], ["kms:DescribeKey"], ["kms:Describe*"]],
    )
    def test_policy__deny_based_on_actions(self, actions):
        policy = {
            "Version": "2012-10-17",
            "Id": "",
            "Statement": [
                {
                    "Sid": "test",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": actions,
                    "Resource": "*",
                }
            ],
        }
        self.client.put_key_policy(
            Policy=json.dumps(policy), PolicyName="default", KeyId=self.key_id
        )
        with pytest.raises(ClientError) as exc:
            self.client.describe_key(KeyId=self.key_id)
        err = exc.value.response["Error"]
        assert err["Code"] == "AccessDeniedException"

    @pytest.mark.parametrize("actions", [["kms:unknown"], ["kms:describestuff"]])
    def test_policy__allow_based_on_actions(self, actions):
        policy = {
            "Version": "2012-10-17",
            "Id": "",
            "Statement": [
                {
                    "Sid": "test",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": actions,
                    "Resource": "*",
                }
            ],
        }
        self.client.put_key_policy(
            Policy=json.dumps(policy), PolicyName="default", KeyId=self.key_id
        )
        key = self.client.describe_key(KeyId=self.key_id)["KeyMetadata"]
        assert key["Description"] == "t"


class TestKMSPolicyValidator:
    def test_input_can_be_none(self):
        validate_policy(None, None)

    def test_key_can_have_no_policy(self):
        validate_policy(self.create_key(policy=None), None)

    def test_key_can_have_unreadable_policy(self):
        validate_policy(self.create_key(policy="some policy"), None)

    @pytest.mark.parametrize(
        "action", ["kms:*", "kms:DescribeKey", "unknown", "", None]
    )
    def test_describe_key_is_allowed_for_actions(self, action):
        policy = {
            "Statement": [{"Effect": "Allow", "Action": [action], "Resource": "*"}]
        }
        key = self.create_key(policy=json.dumps(policy))
        validate_policy(key, "kms:DescribeKey")

    @pytest.mark.parametrize(
        "action", ["kms:DeleteKey", "awslambda:DescribeKey", "unknown", "", None]
    )
    def test_describe_key_is_allowed_if_other_actions_are_allowed(self, action):
        policy = {
            "Statement": [{"Effect": "denY", "Action": [action], "Resource": "*"}]
        }
        key = self.create_key(policy=json.dumps(policy))
        validate_policy(key, "kms:DescribeKey")

    @pytest.mark.parametrize("action", ["kms:*", "kms:Describe*", "kms:DescribeKey"])
    def test_describe_key_is_denied_for_all_possible_action_variations(self, action):
        policy = {
            "Statement": [{"Effect": "denY", "Action": [action], "Resource": "*"}]
        }
        key = self.create_key(policy=json.dumps(policy))
        with pytest.raises(AccessDeniedException):
            validate_policy(key, "kms:DescribeKey")

    @pytest.mark.parametrize("resource", ["arn", "kms:*"])
    def test_describe_key_is_allowed_for_unsupported_resources(self, resource):
        policy = {
            "Statement": [{"Effect": "denY", "Action": ["kms:*"], "Resource": resource}]
        }
        key = self.create_key(policy=json.dumps(policy))
        validate_policy(key, "kms:DescribeKey")

    def create_key(self, policy):
        with mock.patch.object(rsa, "generate_private_key", return_value=""):
            return Key(
                account_id=None,
                region=None,
                description=None,
                key_spec=None,
                key_usage=None,
                policy=policy,
            )
