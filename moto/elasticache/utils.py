from enum import Enum

PAGINATION_MODEL = {
    "describe_cache_clusters": {
        "input_token": "marker",
        "limit_key": "max_records",
        "limit_default": 100,
        "unique_attribute": "cache_cluster_id",
    },
}


class AuthenticationTypes(str, Enum):
    NOPASSWORD = "no-password-required"
    PASSWORD = "password"
    IAM = "iam"


VALID_ENGINE_TYPES = ["Redis", "redis", "valkey"]
VALID_AUTH_MODE_KEYS = ["Type", "Passwords"]
