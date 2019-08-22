from __future__ import unicode_literals
import json

import boto
import boto3
from botocore.client import ClientError
from freezegun import freeze_time
from nose.tools import assert_raises
import sure  # noqa


from moto import mock_sts, mock_sts_deprecated, mock_iam, settings
from moto.iam.models import ACCOUNT_ID
from moto.sts.responses import MAX_FEDERATION_TOKEN_POLICY_LENGTH


@freeze_time("2012-01-01 12:00:00")
@mock_sts_deprecated
def test_get_session_token():
    conn = boto.connect_sts()
    token = conn.get_session_token(duration=123)

    token.expiration.should.equal('2012-01-01T12:02:03.000Z')
    token.session_token.should.equal(
        "AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE")
    token.access_key.should.equal("AKIAIOSFODNN7EXAMPLE")
    token.secret_key.should.equal("wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY")


@freeze_time("2012-01-01 12:00:00")
@mock_sts_deprecated
def test_get_federation_token():
    conn = boto.connect_sts()
    token_name = "Bob"
    token = conn.get_federation_token(duration=123, name=token_name)

    token.credentials.expiration.should.equal('2012-01-01T12:02:03.000Z')
    token.credentials.session_token.should.equal(
        "AQoDYXdzEPT//////////wEXAMPLEtc764bNrC9SAPBSM22wDOk4x4HIZ8j4FZTwdQWLWsKWHGBuFqwAeMicRXmxfpSPfIeoIYRqTflfKD8YUuwthAx7mSEI/qkPpKPi/kMcGdQrmGdeehM4IC1NtBmUpp2wUE8phUZampKsburEDy0KPkyQDYwT7WZ0wq5VSXDvp75YU9HFvlRd8Tx6q6fE8YQcHNVXAkiY9q6d+xo0rKwT38xVqr7ZD0u0iPPkUL64lIZbqBAz+scqKmlzm8FDrypNC9Yjc8fPOLn9FX9KSYvKTr4rvx3iSIlTJabIQwj2ICCR/oLxBA==")
    token.credentials.access_key.should.equal("AKIAIOSFODNN7EXAMPLE")
    token.credentials.secret_key.should.equal(
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY")
    token.federated_user_arn.should.equal(
        "arn:aws:sts::{account_id}:federated-user/{token_name}".format(account_id=ACCOUNT_ID, token_name=token_name))
    token.federated_user_id.should.equal(str(ACCOUNT_ID) + ":" + token_name)


@freeze_time("2012-01-01 12:00:00")
@mock_sts
def test_assume_role():
    client = boto3.client(
        "sts", region_name='us-east-1')

    session_name = "session-name"
    policy = json.dumps({
        "Statement": [
            {
                "Sid": "Stmt13690092345534",
                "Action": [
                    "S3:ListBucket"
                ],
                "Effect": "Allow",
                "Resource": [
                    "arn:aws:s3:::foobar-tester"
                ]
            },
        ]
    })
    role_name = "test-role"
    s3_role = "arn:aws:iam::{account_id}:role/{role_name}".format(account_id=ACCOUNT_ID, role_name=role_name)
    assume_role_response = client.assume_role(RoleArn=s3_role, RoleSessionName=session_name,
                                              Policy=policy, DurationSeconds=900)

    credentials = assume_role_response['Credentials']
    if not settings.TEST_SERVER_MODE:
        credentials['Expiration'].isoformat().should.equal('2012-01-01T12:15:00+00:00')
    credentials['SessionToken'].should.have.length_of(356)
    assert credentials['SessionToken'].startswith("FQoGZXIvYXdzE")
    credentials['AccessKeyId'].should.have.length_of(20)
    assert credentials['AccessKeyId'].startswith("ASIA")
    credentials['SecretAccessKey'].should.have.length_of(40)

    assume_role_response['AssumedRoleUser']['Arn'].should.equal("arn:aws:sts::{account_id}:assumed-role/{role_name}/{session_name}".format(
        account_id=ACCOUNT_ID, role_name=role_name, session_name=session_name))
    assert assume_role_response['AssumedRoleUser']['AssumedRoleId'].startswith("AROA")
    assert assume_role_response['AssumedRoleUser']['AssumedRoleId'].endswith(":" + session_name)
    assume_role_response['AssumedRoleUser']['AssumedRoleId'].should.have.length_of(21 + 1 + len(session_name))


@freeze_time("2012-01-01 12:00:00")
@mock_sts_deprecated
def test_assume_role_with_web_identity():
    conn = boto.connect_sts()

    policy = json.dumps({
        "Statement": [
            {
                "Sid": "Stmt13690092345534",
                "Action": [
                    "S3:ListBucket"
                ],
                "Effect": "Allow",
                "Resource": [
                    "arn:aws:s3:::foobar-tester"
                ]
            },
        ]
    })
    role_name = "test-role"
    s3_role = "arn:aws:iam::{account_id}:role/{role_name}".format(account_id=ACCOUNT_ID, role_name=role_name)
    session_name = "session-name"
    role = conn.assume_role_with_web_identity(
        s3_role, session_name, policy, duration_seconds=123)

    credentials = role.credentials
    credentials.expiration.should.equal('2012-01-01T12:02:03.000Z')
    credentials.session_token.should.have.length_of(356)
    assert credentials.session_token.startswith("FQoGZXIvYXdzE")
    credentials.access_key.should.have.length_of(20)
    assert credentials.access_key.startswith("ASIA")
    credentials.secret_key.should.have.length_of(40)

    role.user.arn.should.equal("arn:aws:sts::{account_id}:assumed-role/{role_name}/{session_name}".format(
        account_id=ACCOUNT_ID, role_name=role_name, session_name=session_name))
    role.user.assume_role_id.should.contain("session-name")


@mock_sts
def test_get_caller_identity_with_default_credentials():
    identity = boto3.client(
        "sts", region_name='us-east-1').get_caller_identity()

    identity['Arn'].should.equal('arn:aws:sts::{account_id}:user/moto'.format(account_id=ACCOUNT_ID))
    identity['UserId'].should.equal('AKIAIOSFODNN7EXAMPLE')
    identity['Account'].should.equal(str(ACCOUNT_ID))


@mock_sts
@mock_iam
def test_get_caller_identity_with_iam_user_credentials():
    iam_client = boto3.client("iam", region_name='us-east-1')
    iam_user_name = "new-user"
    iam_user = iam_client.create_user(UserName=iam_user_name)['User']
    access_key = iam_client.create_access_key(UserName=iam_user_name)['AccessKey']

    identity = boto3.client(
        "sts", region_name='us-east-1', aws_access_key_id=access_key['AccessKeyId'],
        aws_secret_access_key=access_key['SecretAccessKey']).get_caller_identity()

    identity['Arn'].should.equal(iam_user['Arn'])
    identity['UserId'].should.equal(iam_user['UserId'])
    identity['Account'].should.equal(str(ACCOUNT_ID))


@mock_sts
@mock_iam
def test_get_caller_identity_with_assumed_role_credentials():
    iam_client = boto3.client("iam", region_name='us-east-1')
    sts_client = boto3.client("sts", region_name='us-east-1')
    iam_role_name = "new-user"
    trust_policy_document = {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::{account_id}:root".format(account_id=ACCOUNT_ID)},
            "Action": "sts:AssumeRole"
        }
    }
    iam_role_arn = iam_client.role_arn = iam_client.create_role(
        RoleName=iam_role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy_document)
    )['Role']['Arn']
    session_name = "new-session"
    assumed_role = sts_client.assume_role(RoleArn=iam_role_arn,
                                          RoleSessionName=session_name)
    access_key = assumed_role['Credentials']

    identity = boto3.client(
        "sts", region_name='us-east-1', aws_access_key_id=access_key['AccessKeyId'],
        aws_secret_access_key=access_key['SecretAccessKey']).get_caller_identity()

    identity['Arn'].should.equal(assumed_role['AssumedRoleUser']['Arn'])
    identity['UserId'].should.equal(assumed_role['AssumedRoleUser']['AssumedRoleId'])
    identity['Account'].should.equal(str(ACCOUNT_ID))


@mock_sts
def test_federation_token_with_too_long_policy():
    "Trying to get a federation token with a policy longer than 2048 character should fail"
    cli = boto3.client("sts", region_name='us-east-1')
    resource_tmpl = 'arn:aws:s3:::yyyy-xxxxx-cloud-default/my_default_folder/folder-name-%s/*'
    statements = []
    for num in range(30):
        statements.append(
            {
                'Effect': 'Allow',
                'Action': ['s3:*'],
                'Resource': resource_tmpl % str(num)
            }
        )
    policy = {
        'Version': '2012-10-17',
        'Statement': statements
    }
    json_policy = json.dumps(policy)
    assert len(json_policy) > MAX_FEDERATION_TOKEN_POLICY_LENGTH

    with assert_raises(ClientError) as exc:
        cli.get_federation_token(Name='foo', DurationSeconds=3600, Policy=json_policy)
    exc.exception.response['Error']['Code'].should.equal('ValidationError')
    exc.exception.response['Error']['Message'].should.contain(
        str(MAX_FEDERATION_TOKEN_POLICY_LENGTH)
    )
