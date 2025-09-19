from enum import Enum
from typing import Dict, List

PAGINATION_MODEL = {
    "describe_cache_clusters": {
        "input_token": "marker",
        "limit_key": "max_records",
        "limit_default": 100,
        "unique_attribute": "cache_cluster_id",
    },
    "describe_cache_subnet_groups": {
        "input_token": "marker",
        "limit_key": "max_records",
        "limit_default": 100,
        "unique_attribute": "cache_subnet_group_name",
    },
    "describe_replication_groups": {
        "input_token": "marker",
        "limit_key": "max_records",
        "limit_default": 100,
        "unique_attribute": "replication_group_id",
    },
}
VALID_AUTH_MODE_KEYS = ["Type", "Passwords"]
VALID_ENGINE_TYPES = ["redis", "valkey"]


class AuthenticationTypes(str, Enum):
    NOPASSWORD = "no-password-required"
    PASSWORD = "password"
    IAM = "iam"


def _normalize_tags(tags: List[Dict[str, str]]) -> List[Dict[str, str]]:
    # Created to handle XFormedDict tags
    if not tags:
        return []

    normalized = []
    for t in tags:
        if "Key" in t and "Value" in t:
            normalized.append({"Key": t["Key"], "Value": t["Value"]})
        elif "key" in t and "value" in t:
            normalized.append({"Key": t["key"], "Value": t["value"]})
        else:
            raise ValueError(f"Unrecognized tag format: {t}")
    return normalized
