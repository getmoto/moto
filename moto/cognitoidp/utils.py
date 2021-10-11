from __future__ import unicode_literals
import random
import string
import hashlib
import hmac
import base64


PAGINATION_MODEL = {
    "list_user_pools": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 60,
        "page_ending_range_keys": ["arn"],
    },
    "list_user_pool_clients": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 60,
        "page_ending_range_keys": ["id"],
    },
    "list_identity_providers": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 60,
        "page_ending_range_keys": ["name"],
    },
    "list_users": {
        "input_token": "pagination_token",
        "limit_key": "limit",
        "limit_default": 60,
        "page_ending_range_keys": ["id"],
    },
}


def create_id():
    size = 26
    chars = list(range(10)) + list(string.ascii_lowercase)
    return "".join(str(random.choice(chars)) for x in range(size))


def check_secret_hash(app_client_secret, app_client_id, username, secret_hash):
    key = bytes(str(app_client_secret).encode("latin-1"))
    msg = bytes(str(username + app_client_id).encode("latin-1"))
    new_digest = hmac.new(key, msg, hashlib.sha256).digest()
    SECRET_HASH = base64.b64encode(new_digest).decode()
    return SECRET_HASH == secret_hash
