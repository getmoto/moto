import os
from functools import wraps

from moto import mock_aws


def sqs_aws_verified(func):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.
    """

    @wraps(func)
    def pagination_wrapper(*args, **kwargs):
        allow_aws_request = (
            os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"
        )

        if allow_aws_request:
            return func(*args, **kwargs)
        else:
            with mock_aws():
                return func(*args, **kwargs)

    return pagination_wrapper
