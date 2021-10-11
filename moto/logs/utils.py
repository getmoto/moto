PAGINATION_MODEL = {
    "describe_log_groups": {
        "input_token": "next_token",
        "limit_key": "limit",
        "limit_default": 50,
        "page_ending_range_keys": ["arn"],
        "fail_on_invalid_token": False,
    },
    "describe_log_streams": {
        "input_token": "next_token",
        "limit_key": "limit",
        "limit_default": 50,
        "page_ending_range_keys": ["arn"],
    },
}
