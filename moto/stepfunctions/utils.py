PAGINATION_MODEL = {
    "list_executions": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "page_ending_range_keys": ["start_date", "execution_arn"],
    },
    "list_state_machines": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "page_ending_range_keys": ["creation_date", "arn"],
    },
}


def cfn_to_api_tags(cfn_tags_entry):
    api_tags = [{k.lower(): v for k, v in d.items()} for d in cfn_tags_entry]
    return api_tags


def api_to_cfn_tags(api_tags):
    cfn_tags_entry = [{k.capitalize(): v for k, v in d.items()} for d in api_tags]
    return cfn_tags_entry
