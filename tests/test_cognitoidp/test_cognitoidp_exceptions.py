from unittest import TestCase

import boto3
import pytest

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
            UserPoolId=self.pool_id, Username="foo", TemporaryPassword="P2$Sword"
        )

        self.client.admin_set_user_password(
            UserPoolId=self.pool_id,
            Username="foo",
            Password="P2$Sword2",
            Permanent=True,
        )

        response = self.client.admin_initiate_auth(
            UserPoolId=self.pool_id,
            ClientId=self.client_id,
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": "foo", "PASSWORD": "P2$Sword2"},
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


@mock_cognitoidp
class TestCognitoUserPoolDuplidateEmails(TestCase):
    def setUp(self) -> None:
        self.client = boto3.client("cognito-idp", "us-east-1")

        self.pool_id1 = self.client.create_user_pool(PoolName="test")["UserPool"]["Id"]
        self.pool_id2 = self.client.create_user_pool(
            PoolName="test", UsernameAttributes=["email"]
        )["UserPool"]["Id"]

        # create two users
        for user in ["user1", "user2"]:
            self.client.admin_create_user(
                UserPoolId=self.pool_id1,
                Username=user,
                UserAttributes=[{"Name": "email", "Value": f"{user}@test.com"}],
            )
            self.client.admin_create_user(
                UserPoolId=self.pool_id2,
                Username=f"{user}@test.com",
                UserAttributes=[{"Name": "email", "Value": f"{user}@test.com"}],
            )

    def test_use_existing_email__when_email_is_login(self):
        with pytest.raises(ClientError) as exc:
            self.client.admin_update_user_attributes(
                UserPoolId=self.pool_id2,
                Username="user1@test.com",
                UserAttributes=[{"Name": "email", "Value": "user2@test.com"}],
            )
        err = exc.value.response["Error"]
        err["Code"].should.equal("AliasExistsException")
        err["Message"].should.equal("An account with the given email already exists.")

    def test_use_existing_email__when_username_is_login(self):
        # Because we cannot use the email as username,
        # multiple users can have the same email address
        self.client.admin_update_user_attributes(
            UserPoolId=self.pool_id1,
            Username="user1",
            UserAttributes=[{"Name": "email", "Value": "user2@test.com"}],
        )
