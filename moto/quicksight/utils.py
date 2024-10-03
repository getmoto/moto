PAGINATION_MODEL = {
    "list_users": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,  # This should be the sum of the directory limits
        "unique_attribute": "arn",
    },
    "list_user_groups": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,  # This should be the sum of the directory limits
        "unique_attribute": "arn",
    },
    "list_groups": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,  # This should be the sum of the directory limits
        "unique_attribute": "arn",
    },
    "list_group_memberships": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,  # This should be the sum of the directory limits
        "unique_attribute": "arn",
    },
}
