from collections import namedtuple
from functools import partial
from typing import Any, Callable

ARN = namedtuple("ARN", ["region", "account", "function_name", "version"])
LAYER_ARN = namedtuple("LAYER_ARN", ["region", "account", "layer_name", "version"])


def make_arn(resource_type: str, region: str, account: str, name: str) -> str:
    return f"arn:aws:lambda:{region}:{account}:{resource_type}:{name}"


make_function_arn = partial(make_arn, "function")
make_layer_arn = partial(make_arn, "layer")


def make_ver_arn(
    resource_type: str, region: str, account: str, name: str, version: str = "1"
) -> str:
    arn = make_arn(resource_type, region, account, name)
    return f"{arn}:{version}"


make_function_ver_arn = partial(make_ver_arn, "function")
make_layer_ver_arn = partial(make_ver_arn, "layer")


def split_arn(arn_type: Callable[[str, str, str, str], str], arn: str) -> Any:
    arn = arn.replace("arn:aws:lambda:", "")

    region, account, _, name, version = arn.split(":")

    return arn_type(region, account, name, version)


split_function_arn = partial(split_arn, ARN)
split_layer_arn = partial(split_arn, LAYER_ARN)
