PAGINATION_MODEL = {
    "list_rules": {
        "input_token": "next_token",
        "limit_key": "limit",
        "limit_default": 50,
        "page_ending_range_keys": ["arn"],
        "fail_on_invalid_token": False,
    },
    "list_rule_names_by_target": {
        "input_token": "next_token",
        "limit_key": "limit",
        "limit_default": 50,
        "page_ending_range_keys": ["arn"],
        "fail_on_invalid_token": False,
    },
}
