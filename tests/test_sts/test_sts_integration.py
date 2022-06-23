import unittest
import boto3
from moto import mock_sts, mock_iam


class TestStsAssumeRole(unittest.TestCase):
    @mock_iam
    @mock_sts
    def test_assume_role_in_different_account(self):

        # assume role to another aws account
        account_b = "111111111111"
        role_name = f"arn:aws:iam::{account_b}:role/my-role"
        sts = boto3.client("sts")
        response = sts.assume_role(
            RoleArn=role_name,
            RoleSessionName="test-session-name",
            ExternalId="test-external-id",
        )

        # Assume the new role
        iam_account_b = boto3.client(
            "iam",
            aws_access_key_id=response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
            aws_session_token=response["Credentials"]["SessionToken"],
            region_name="us-east-1",
        )

        # Verify new users belong to the different account
        user = iam_account_b.create_user(UserName="user-in-new-account")["User"]
        user["Arn"].should.equal(f"arn:aws:iam::{account_b}:user/user-in-new-account")
