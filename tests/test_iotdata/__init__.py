import os
from functools import wraps
from typing import TYPE_CHECKING, Callable, TypeVar
from uuid import uuid4

import boto3

from moto import mock_aws

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    P = ParamSpec("P")

T = TypeVar("T")


def iot_aws_verified() -> "Callable[[Callable[P, T]], Callable[P, T]]":
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.
    """

    def inner(func: "Callable[P, T]") -> "Callable[P, T]":
        @wraps(func)
        def pagination_wrapper(*args: "P.args", **kwargs: "P.kwargs") -> T:
            allow_aws_request = (
                os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"
            )

            if allow_aws_request:
                return _create_thing_and_execute_test(func, *args, **kwargs)
            else:
                with mock_aws():
                    return _create_thing_and_execute_test(func, *args, **kwargs)

        return pagination_wrapper

    return inner


def _create_thing_and_execute_test(
    func: "Callable[P, T]", *args: "P.args", **kwargs: "P.kwargs"
) -> T:
    iot_client = boto3.client("iot", region_name="ap-northeast-1")
    name = str(uuid4())

    iot_client.create_thing(thingName=name)

    try:
        return func(*args, **kwargs, name=name)  # type: ignore
    finally:
        iot_client.delete_thing(thingName=name)
