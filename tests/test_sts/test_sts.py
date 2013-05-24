import json

import boto
from boto.exception import BotoServerError
from freezegun import freeze_time
import sure  # flake8: noqa

from moto import mock_sts


@freeze_time("2012-01-01 12:00:00")
@mock_sts
def test_get_session_token():
    conn = boto.connect_sts()
    token = conn.get_session_token(duration=123)

    token.expiration.should.equal('2012-01-01T12:02:03Z')
    token.session_token.should.equal("AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE")
    token.access_key.should.equal("AKIAIOSFODNN7EXAMPLE")
    token.secret_key.should.equal("wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY")


@freeze_time("2012-01-01 12:00:00")
@mock_sts
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
    role = conn.assume_role(s3_role, "session-name", policy, duration_seconds=123)

    credentials = role.credentials
    credentials.expiration.should.equal('2012-01-01T12:02:03Z')
    credentials.session_token.should.equal("BQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE")
    credentials.access_key.should.equal("AKIAIOSFODNN7EXAMPLE")
    credentials.secret_key.should.equal("aJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY")

    role.user.arn.should.equal("arn:aws:iam::123456789012:role/test-role")
    role.user.assume_role_id.should.contain("session-name")
