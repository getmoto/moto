import boto3
import unittest

from base64 import b64encode
from moto import mock_dynamodb, mock_sts, mock_iam
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_sts
@mock_iam
@mock_dynamodb
class TestStsAssumeRole(unittest.TestCase):
    def setUp(self) -> None:
        self.account_b = "111111111111"
        self.sts = boto3.client("sts", region_name="us-east-1")

    def test_assume_role_in_different_account(self):
        # assume role to another aws account
        role_name = f"arn:aws:iam::{self.account_b}:role/my-role"
        response = self.sts.assume_role(
            RoleArn=role_name,
            RoleSessionName="test-session-name",
            ExternalId="test-external-id",
        )

        # Assume the new role
        sts_account_b = boto3.client(
            "sts",
            aws_access_key_id=response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
            aws_session_token=response["Credentials"]["SessionToken"],
            region_name="us-east-1",
        )
        assumed_arn = sts_account_b.get_caller_identity()["Arn"]
        assumed_arn.should.equal(
            f"arn:aws:sts::{self.account_b}:assumed-role/my-role/test-session-name"
        )
        iam_account_b = boto3.client(
            "iam",
            aws_access_key_id=response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
            aws_session_token=response["Credentials"]["SessionToken"],
            region_name="us-east-1",
        )

        # Verify new users belong to the different account
        user = iam_account_b.create_user(UserName="user-in-new-account")["User"]
        user["Arn"].should.equal(
            f"arn:aws:iam::{self.account_b}:user/user-in-new-account"
        )

    def test_assume_role_with_saml_in_different_account(self):
        role_name = "test-role"
        provider_name = "TestProvFed"
        fed_identifier = "7ca82df9-1bad-4dd3-9b2b-adb68b554282"
        fed_name = "testuser"
        role_input = f"arn:aws:iam::{self.account_b}:role/{role_name}"
        principal_role = f"arn:aws:iam:{ACCOUNT_ID}:saml-provider/{provider_name}"
        saml_assertion = f"""<?xml version="1.0"?>
        <samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" ID="_00000000-0000-0000-0000-000000000000" Version="2.0" IssueInstant="2012-01-01T12:00:00.000Z" Destination="https://signin.aws.amazon.com/saml" Consent="urn:oasis:names:tc:SAML:2.0:consent:unspecified">
          <Issuer xmlns="urn:oasis:names:tc:SAML:2.0:assertion">http://localhost/</Issuer>
          <samlp:Status>
            <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
          </samlp:Status>
          <Assertion xmlns="urn:oasis:names:tc:SAML:2.0:assertion" ID="_00000000-0000-0000-0000-000000000000" IssueInstant="2012-12-01T12:00:00.000Z" Version="2.0">
            <Issuer>http://localhost:3000/</Issuer>
            <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
              <ds:SignedInfo>
                <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                <ds:Reference URI="#_00000000-0000-0000-0000-000000000000">
                  <ds:Transforms>
                    <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                    <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                  </ds:Transforms>
                  <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                  <ds:DigestValue>NTIyMzk0ZGI4MjI0ZjI5ZGNhYjkyOGQyZGQ1NTZjODViZjk5YTY4ODFjOWRjNjkyYzZmODY2ZDQ4NjlkZjY3YSAgLQo=</ds:DigestValue>
                </ds:Reference>
              </ds:SignedInfo>
              <ds:SignatureValue>NTIyMzk0ZGI4MjI0ZjI5ZGNhYjkyOGQyZGQ1NTZjODViZjk5YTY4ODFjOWRjNjkyYzZmODY2ZDQ4NjlkZjY3YSAgLQo=</ds:SignatureValue>
              <KeyInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
                <ds:X509Data>
                  <ds:X509Certificate>NTIyMzk0ZGI4MjI0ZjI5ZGNhYjkyOGQyZGQ1NTZjODViZjk5YTY4ODFjOWRjNjkyYzZmODY2ZDQ4NjlkZjY3YSAgLQo=</ds:X509Certificate>
                </ds:X509Data>
              </KeyInfo>
            </ds:Signature>
            <Subject>
              <NameID Format="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent">{fed_identifier}</NameID>
              <SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <SubjectConfirmationData NotOnOrAfter="2012-01-01T13:00:00.000Z" Recipient="https://signin.aws.amazon.com/saml"/>
              </SubjectConfirmation>
            </Subject>
            <Conditions NotBefore="2012-01-01T12:00:00.000Z" NotOnOrAfter="2012-01-01T13:00:00.000Z">
              <AudienceRestriction>
                <Audience>urn:amazon:webservices</Audience>
              </AudienceRestriction>
            </Conditions>
            <AttributeStatement>
              <Attribute Name="https://aws.amazon.com/SAML/Attributes/RoleSessionName">
                <AttributeValue>{fed_name}</AttributeValue>
              </Attribute>
              <Attribute Name="https://aws.amazon.com/SAML/Attributes/Role">
                <AttributeValue>arn:aws:iam::{self.account_b}:role/{role_name},arn:aws:iam::{self.account_b}:saml-provider/{provider_name}</AttributeValue>
              </Attribute>
              <Attribute Name="https://aws.amazon.com/SAML/Attributes/SessionDuration">
                <AttributeValue>900</AttributeValue>
              </Attribute>
            </AttributeStatement>
            <AuthnStatement AuthnInstant="2012-01-01T12:00:00.000Z" SessionIndex="_00000000-0000-0000-0000-000000000000">
              <AuthnContext>
                <AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport</AuthnContextClassRef>
              </AuthnContext>
            </AuthnStatement>
          </Assertion>
        </samlp:Response>""".replace(
            "\n", ""
        )

        assume_role_response = self.sts.assume_role_with_saml(
            RoleArn=role_input,
            PrincipalArn=principal_role,
            SAMLAssertion=b64encode(saml_assertion.encode("utf-8")).decode("utf-8"),
        )

        # Assume the new role
        iam_account_b = boto3.client(
            "iam",
            aws_access_key_id=assume_role_response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=assume_role_response["Credentials"][
                "SecretAccessKey"
            ],
            aws_session_token=assume_role_response["Credentials"]["SessionToken"],
            region_name="us-east-1",
        )

        # Verify new users belong to the different account
        user = iam_account_b.create_user(UserName="user-in-new-account")["User"]
        user["Arn"].should.equal(
            f"arn:aws:iam::{self.account_b}:user/user-in-new-account"
        )

    def test_dynamodb_supports_multiple_accounts(self):
        ddb_client = boto3.client("dynamodb", region_name="us-east-1")

        ddb_client.create_table(
            TableName="table-in-default-account",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
        )
        # assume role to another aws account
        role_name = f"arn:aws:iam::{self.account_b}:role/my-role"
        response = self.sts.assume_role(
            RoleArn=role_name,
            RoleSessionName="test-session-name",
            ExternalId="test-external-id",
        )

        # Assume the new role
        ddb_account_b = boto3.client(
            "dynamodb",
            aws_access_key_id=response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
            aws_session_token=response["Credentials"]["SessionToken"],
            region_name="us-east-1",
        )

        # Verify new dynamodb belong to the different account
        ddb_account_b.create_table(
            TableName="table-in-new-account",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
        )

        table = ddb_client.describe_table(TableName="table-in-default-account")["Table"]
        table["TableArn"].should.equal(
            "arn:aws:dynamodb:us-east-1:123456789012:table/table-in-default-account"
        )

        table = ddb_account_b.describe_table(TableName="table-in-new-account")["Table"]
        table["TableArn"].should.equal(
            f"arn:aws:dynamodb:us-east-1:{self.account_b}:table/table-in-new-account"
        )
