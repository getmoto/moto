"""Pagination control model for Route53."""

PAGINATION_MODEL = {
    "list_query_logging_configs": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "unique_attribute": "hosted_zone_id",
    },
}
