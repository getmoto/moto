from __future__ import unicode_literals
import json

import boto
import boto3
from freezegun import freeze_time
import sure  # noqa

from moto import mock_sts, mock_sts_deprecated


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
    token = conn.get_federation_token(duration=123, name="Bob")

    token.credentials.expiration.should.equal('2012-01-01T12:02:03.000Z')
    token.credentials.session_token.should.equal(
        "AQoDYXdzEPT//////////wEXAMPLEtc764bNrC9SAPBSM22wDOk4x4HIZ8j4FZTwdQWLWsKWHGBuFqwAeMicRXmxfpSPfIeoIYRqTflfKD8YUuwthAx7mSEI/qkPpKPi/kMcGdQrmGdeehM4IC1NtBmUpp2wUE8phUZampKsburEDy0KPkyQDYwT7WZ0wq5VSXDvp75YU9HFvlRd8Tx6q6fE8YQcHNVXAkiY9q6d+xo0rKwT38xVqr7ZD0u0iPPkUL64lIZbqBAz+scqKmlzm8FDrypNC9Yjc8fPOLn9FX9KSYvKTr4rvx3iSIlTJabIQwj2ICCR/oLxBA==")
    token.credentials.access_key.should.equal("AKIAIOSFODNN7EXAMPLE")
    token.credentials.secret_key.should.equal(
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY")
    token.federated_user_arn.should.equal(
        "arn:aws:sts::123456789012:federated-user/Bob")
    token.federated_user_id.should.equal("123456789012:Bob")


@freeze_time("2012-01-01 12:00:00")
@mock_sts_deprecated
def test_assume_role():
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
    s3_role = "arn:aws:iam::123456789012:role/test-role"
    role = conn.assume_role(s3_role, "session-name",
                            policy, duration_seconds=123)

    credentials = role.credentials
    credentials.expiration.should.equal('2012-01-01T12:02:03.000Z')
    credentials.session_token.should.equal(
        "BQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE")
    credentials.access_key.should.equal("AKIAIOSFODNN7EXAMPLE")
    credentials.secret_key.should.equal(
        "aJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY")

    role.user.arn.should.equal("arn:aws:iam::123456789012:role/test-role")
    role.user.assume_role_id.should.contain("session-name")


@mock_sts
def test_get_caller_identity():
    identity = boto3.client(
        "sts", region_name='us-east-1').get_caller_identity()

    identity['Arn'].should.equal('arn:aws:sts::123456789012:user/moto')
    identity['UserId'].should.equal('AKIAIOSFODNN7EXAMPLE')
    identity['Account'].should.equal('123456789012')
