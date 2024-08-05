import logging
import os
from functools import wraps

from moto import mock_aws
from moto.core.config import default_user_config

# Disable extra logging for tests
logging.getLogger("boto").setLevel(logging.CRITICAL)
logging.getLogger("boto3").setLevel(logging.CRITICAL)
logging.getLogger("botocore").setLevel(logging.CRITICAL)

# Sample pre-loaded Image Ids for use with tests.
# (Source: moto/ec2/resources/amis.json)
EXAMPLE_AMI_ID = "ami-12c6146b"
EXAMPLE_AMI_ID2 = "ami-03cf127a"
EXAMPLE_AMI_PARAVIRTUAL = "ami-fa7cdd89"
EXAMPLE_AMI_WINDOWS = "ami-f4cf1d8d"

DEFAULT_ACCOUNT_ID = "123456789012"

# For the majority of tests we don't need the default AMI's
os.environ["MOTO_EC2_LOAD_DEFAULT_AMIS"] = "false"

# Don't reset boto3 Session, as it's unnecessarily slow
default_user_config["core"]["reset_boto3_session"] = False


def allow_aws_request() -> bool:
    return os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"


def aws_verified(func):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.
    """

    @wraps(func)
    def pagination_wrapper(**kwargs):
        if allow_aws_request():
            return func(**kwargs)
        else:
            with mock_aws():
                return func(**kwargs)

    return pagination_wrapper
