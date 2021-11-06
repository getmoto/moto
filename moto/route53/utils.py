"""Pagination control model for Route53."""

PAGINATION_MODEL = {
    "list_query_logging_configs": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "page_ending_range_keys": ["hosted_zone_id"],
    },
}
