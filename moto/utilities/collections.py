from typing import Any, List

from moto.core.versions import PYTHON_39


def select_attributes(obj: Any, attributes: List[str]) -> Any:
    """Select a subset of attributes from the given dict (returns a copy)"""
    attributes = attributes if isinstance(attributes, (list, tuple)) else [attributes]  # type: ignore
    return {k: v for k, v in obj.items() if k in attributes}


def select_from_typed_dict(typed_dict: Any, obj: Any, filter: bool = False) -> Any:
    """
    Select a subset of attributes from a dictionary based on the keys of a given `TypedDict`.
    :param typed_dict: the `TypedDict` blueprint
    :param obj: the object to filter
    :param filter: if True, remove all keys with an empty (e.g., empty string or dictionary) or `None` value
    :return: the resulting dictionary (it returns a copy)
    """
    if not PYTHON_39:
        # Python 3.8 does not have __required_keys__, __optional_keys__
        return dict(obj)
    selection = select_attributes(
        obj, [*typed_dict.__required_keys__, *typed_dict.__optional_keys__]
    )
    if filter:
        selection = {k: v for k, v in selection.items() if v}
    return selection
