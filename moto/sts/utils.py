import base64
import os
import random
import string

ACCOUNT_SPECIFIC_ACCESS_KEY_PREFIX = "8NWMTLYQ"
ACCOUNT_SPECIFIC_ASSUMED_ROLE_ID_PREFIX = "3X42LBCD"
SESSION_TOKEN_PREFIX = "FQoGZXIvYXdzEBYaD"
DEFAULT_STS_SESSION_DURATION = 3600


def random_access_key_id():
    return ACCOUNT_SPECIFIC_ACCESS_KEY_PREFIX + _random_uppercase_or_digit_sequence(8)


def random_secret_access_key():
    return base64.b64encode(os.urandom(30)).decode()


def random_session_token():
    return (
        SESSION_TOKEN_PREFIX
        + base64.b64encode(os.urandom(266))[len(SESSION_TOKEN_PREFIX) :].decode()
    )


def random_assumed_role_id():
    return (
        ACCOUNT_SPECIFIC_ASSUMED_ROLE_ID_PREFIX + _random_uppercase_or_digit_sequence(9)
    )


def _random_uppercase_or_digit_sequence(length):
    return "".join(
        str(random.choice(string.ascii_uppercase + string.digits))
        for _ in range(length)
    )
