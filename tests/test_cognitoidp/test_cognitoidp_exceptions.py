from unittest import TestCase

import boto3
from moto import mock_cognitoidp
from botocore.exceptions import ClientError


@mock_cognitoidp
class TestCognitoUserDeleter(TestCase):
    def setUp(self) -> None:
        self.client = boto3.client("cognito-idp", "us-east-1")

        self.pool_id = self.client.create_user_pool(PoolName="test")["UserPool"]["Id"]

        self.client_id = self.client.create_user_pool_client(
            UserPoolId=self.pool_id, ClientName="test-client"
        )["UserPoolClient"]["ClientId"]

    def test_authenticate_with_signed_out_user(self):
        self.client.admin_create_user(
            UserPoolId=self.pool_id, Username="foo", TemporaryPassword="bar"
        )

        self.client.admin_set_user_password(
            UserPoolId=self.pool_id, Username="foo", Password="bar", Permanent=True
        )

        response = self.client.admin_initiate_auth(
            UserPoolId=self.pool_id,
            ClientId=self.client_id,
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": "foo", "PASSWORD": "bar"},
        )

        refresh_token = response["AuthenticationResult"]["RefreshToken"]

        self.client.admin_user_global_sign_out(UserPoolId=self.pool_id, Username="foo")

        with self.assertRaises(ClientError) as exc:
            self.client.admin_initiate_auth(
                UserPoolId=self.pool_id,
                ClientId=self.client_id,
                AuthFlow="REFRESH_TOKEN",
                AuthParameters={
                    "REFRESH_TOKEN": refresh_token,
                },
            )
        exc.exception.response["Error"]["Code"].should.equal("NotAuthorizedException")
