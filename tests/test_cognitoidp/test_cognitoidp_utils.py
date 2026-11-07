import time

import pyotp

from moto.cognitoidp.models import COGNITO_TOTP_MFA_SECRET
from moto.cognitoidp.utils import cognito_totp, java_hashset_order


def test_cognito_totp():
    client_totp = pyotp.TOTP(s=COGNITO_TOTP_MFA_SECRET)
    internal_totp = cognito_totp(COGNITO_TOTP_MFA_SECRET)

    client_code = client_totp.now()
    internal_code = internal_totp.generate(int(time.time())).decode("utf-8")

    assert internal_code == client_code


def test_java_hashset_order():
    # Scope orders as returned by AWS
    assert java_hashset_order(["api/read", "free-text-scope"]) == [
        "free-text-scope",
        "api/read",
    ]
    assert java_hashset_order(
        ["aws.cognito.signin.user.admin", "zeta", "alpha", "res/s3", "mid"]
    ) == ["zeta", "aws.cognito.signin.user.admin", "res/s3", "alpha", "mid"]
    assert java_hashset_order(["res/s3", "abc/x", "res/s1", "res/s4", "res/s2"]) == [
        "res/s1",
        "res/s2",
        "res/s3",
        "res/s4",
        "abc/x",
    ]
