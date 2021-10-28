"""Pagination control model for DirectoryService."""

PAGINATION_MODEL = {
    "describe_directories": {
        "input_token": "next_token",
        "limit_key": "limit",
        "limit_default": 100,  # This should be the sum of the directory limits
        "page_ending_range_keys": ["directory_id"],
    },
}
