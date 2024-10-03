from typing import TYPE_CHECKING, Any, Dict, List

from moto.core.common_models import BaseModel

from .exceptions import InvalidParameterValueException

if TYPE_CHECKING:
    from .models import QuicksightGroup
else:
    QuicksightGroup = Any

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
    "search_groups": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,  # This should be the sum of the directory limits
        "unique_attribute": "arn",
    },
}


class QuicksightFilter(BaseModel):
    def __init__(self, operator: str, name: str, value: str):
        self.operator = operator
        self.name = name
        self.value = value

    def to_json(self) -> Dict[str, Any]:
        return {"Operator": self.operator, "Name": self.name, "Value": self.value}

    def match(self, group: QuicksightGroup) -> bool:
        if self.name == "GROUP_NAME":
            group_attribute = group.group_name
        else:
            raise InvalidParameterValueException(
                "GroupSearchFilter supports ony Name=GROUP_NAME"
            )
        if self.operator == "StartsWith":
            return group_attribute.lower().startswith(self.value.lower())
        else:
            raise InvalidParameterValueException(
                "GroupSearchFilter supports ony Operator=StartsWith"
            )

    @classmethod
    def parse_filter(cls, filter: Dict[str, str]) -> "QuicksightFilter":
        attribute_list = ["Operator", "Name", "Value"]
        if not all([attribute in filter for attribute in attribute_list]):
            raise InvalidParameterValueException(
                "Attribute missing in GroupSearchFilter"
            )
        return QuicksightFilter(
            operator=filter.get("Operator", ""),
            name=filter.get("Name", ""),
            value=filter.get("Value", ""),
        )


class QuicksightFilterList(BaseModel):
    def __init__(self, filters: List[QuicksightFilter]):
        self.filters = filters

    def to_json(self) -> Dict[str, Any]:
        return {"Filters": [filter.to_json() for filter in self.filters]}

    def match(self, group: QuicksightGroup) -> bool:
        return any([filter.match(group) for filter in self.filters])

    @classmethod
    def parse_filters(cls, filter_list: List[Dict[str, str]]) -> "QuicksightFilterList":
        filters: list[QuicksightFilter] = [
            QuicksightFilter.parse_filter(filter) for filter in filter_list
        ]
        if len(filters) > 1:
            raise InvalidParameterValueException("Only 1 filter is allowed.")
        return QuicksightFilterList(filters)
