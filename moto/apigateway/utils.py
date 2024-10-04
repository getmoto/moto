import json
import string
from typing import Any, Dict

import yaml

from moto.moto_api._internal import mock_random as random
from moto.utilities.id_generator import generate_str_id


def create_apigw_id(account_id: str, region: str, resource: str, name: str) -> str:
    return generate_str_id(
        account_id,
        region,
        "apigateway",
        resource,
        name,
        length=10,
        include_digits=True,
        lower_case=True,
    )


def create_id() -> str:
    size = 10
    chars = list(range(10)) + list(string.ascii_lowercase)
    return "".join(str(random.choice(chars)) for x in range(size))


def deserialize_body(body: str) -> Dict[str, Any]:
    try:
        api_doc = json.loads(body)
    except json.JSONDecodeError:
        api_doc = yaml.safe_load(body)

    if "openapi" in api_doc or "swagger" in api_doc:
        return api_doc

    return {}


def to_path(prop: str) -> str:
    return "/" + prop
