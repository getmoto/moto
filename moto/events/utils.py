PAGINATION_MODEL = {
    "list_rules": {
        "input_token": "next_token",
        "limit_key": "limit",
        "limit_default": 50,
        "unique_attribute": "arn",
        "fail_on_invalid_token": False,
    },
    "list_rule_names_by_target": {
        "input_token": "next_token",
        "limit_key": "limit",
        "limit_default": 50,
        "unique_attribute": "arn",
        "fail_on_invalid_token": False,
    },
}

_BASE_EVENT_MESSAGE = {
    "version": "0",
    "id": "17793124-05d4-b198-2fde-7ededc63b103",
    "detail-type": "",
    "source": "",
    "account": "",
    "time": "2021-11-12T00:00:00Z",
    "region": "",
    "resources": [],
    "detail": {},
}
