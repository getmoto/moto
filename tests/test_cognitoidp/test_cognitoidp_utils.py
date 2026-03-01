import time

import pyotp

from moto.cognitoidp.models import COGNITO_TOTP_MFA_SECRET
from moto.cognitoidp.utils import cognito_totp


def test_cognito_totp():
    client_totp = pyotp.TOTP(s=COGNITO_TOTP_MFA_SECRET)
    internal_totp = cognito_totp(COGNITO_TOTP_MFA_SECRET)

    client_code = client_totp.now()
    internal_code = internal_totp.generate(int(time.time())).decode("utf-8")

    assert internal_code == client_code
