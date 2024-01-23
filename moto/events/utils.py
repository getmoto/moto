from typing import TYPE_CHECKING, List, TypedDict

if TYPE_CHECKING:
    from typing_extentions import Any, Dict, Required, Union


# NOTE: Typing is based on the following document https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html
EventMessageType = TypedDict(
    "EventMessageType",
    {
        "version": str,
        "id": str,
        "detail-type": "Required[Union[str, List[str]]]",
        "source": "Required[Union[str, List[str]]]",
        "account": str,
        "time": str,
        "region": str,
        "resources": List[str],
        "detail": "Required[Dict[str, Any]]",
    },
)

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
