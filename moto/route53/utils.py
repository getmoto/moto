"""Pagination control model for Route53."""
from .exceptions import InvalidPaginationToken

PAGINATION_MODEL = {
    "list_query_logging_configs": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "unique_attribute": "hosted_zone_id",
        "fail_on_invalid_token": InvalidPaginationToken,
    },
}
