import os
from functools import wraps

from moto import mock_aws


def cloudformation_aws_verified():
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.
    """

    def inner(func):
        @wraps(func)
        def pagination_wrapper():
            allow_aws_request = (
                os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"
            )

            if allow_aws_request:
                return func()
            else:
                with mock_aws():
                    return func()

        return pagination_wrapper

    return inner
