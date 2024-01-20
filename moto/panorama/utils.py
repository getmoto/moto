import base64
import hashlib
from datetime import datetime
from typing import Any


def deep_convert_datetime_to_isoformat(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, list):
        return [deep_convert_datetime_to_isoformat(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: deep_convert_datetime_to_isoformat(v) for k, v in obj.items()}
    else:
        return obj


def hash_device_name(name: str) -> str:
    digest = hashlib.md5(name.encode("utf-8")).digest()
    token = base64.b64encode(digest)
    return token.decode("utf-8")
