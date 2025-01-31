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
