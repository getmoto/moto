import os
from functools import wraps

import pytest

from moto import mock_aws
from moto.core.utils import get_service_model

requires_cloudwatch_cbor = pytest.mark.skipif(
    "smithy-rpc-v2-cbor"
    not in get_service_model("cloudwatch").metadata.get("protocols", []),
    reason="This botocore version predates CloudWatch's smithy-rpc-v2-cbor support",
)


def cloudwatch_aws_verified(func):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.
    """

    @wraps(func)
    def pagination_wrapper(**kwargs):
        allow_aws_request = (
            os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"
        )

        if allow_aws_request:
            return func(**kwargs)
        else:
            with mock_aws():
                return func(**kwargs)

    return pagination_wrapper
