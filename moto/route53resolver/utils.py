"""Pagination control model for Route53Resolver."""

PAGINATION_MODEL = {
    "list_tags_for_resource": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "page_ending_range_keys": ["Key"],
    },
}
