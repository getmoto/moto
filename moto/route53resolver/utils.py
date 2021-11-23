"""Pagination control model for Route53Resolver."""

PAGINATION_MODEL = {
    "list_resolver_endpoint_ip_addresses": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "page_ending_range_keys": ["IpId"],
    },
    "list_resolver_endpoints": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "page_ending_range_keys": ["id"],
    },
    "list_resolver_rules": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "page_ending_range_keys": ["id"],
    },
    "list_resolver_rule_associations": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "page_ending_range_keys": ["id"],
    },
    "list_tags_for_resource": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "page_ending_range_keys": ["Key"],
    },
}
