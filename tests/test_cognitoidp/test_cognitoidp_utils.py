import time

import pyotp

from moto.cognitoidp.utils import cognito_totp


def test_cognito_totp():
    key = "asdfasdfasdf"
    client_totp = pyotp.TOTP(s=key)
    internal_totp = cognito_totp(key)

    client_code = client_totp.now()
    internal_code = internal_totp.generate(int(time.time())).decode("utf-8")

    assert internal_code == client_code
