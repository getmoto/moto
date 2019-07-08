import base64
import os
import random
import string

import six

ACCOUNT_SPECIFIC_ACCESS_KEY_PREFIX = "8NWMTLYQ"
SESSION_TOKEN_PREFIX = "FQoGZXIvYXdzEBYaD"


def random_access_key_id():
    return ACCOUNT_SPECIFIC_ACCESS_KEY_PREFIX + ''.join(six.text_type(
        random.choice(
            string.ascii_uppercase + string.digits
        )) for _ in range(8)
    )


def random_secret_access_key():
    return base64.b64encode(os.urandom(30)).decode()


def random_session_token():
    return SESSION_TOKEN_PREFIX + base64.b64encode(os.urandom(266))[len(SESSION_TOKEN_PREFIX):].decode()
