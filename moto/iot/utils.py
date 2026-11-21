from typing import Any


def decapitalize_str(obj: str) -> str:
    return obj[0].lower() + obj[1:]


def decapitalize_dict(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            decapitalize_str(key): decapitalize_dict(value)
            for key, value in obj.items()
        }
    else:
        return obj
