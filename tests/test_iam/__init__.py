from functools import wraps
from uuid import uuid4

import boto3

from moto import mock_aws
from tests import allow_aws_request


def iam_aws_verified(create_user: bool = False):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.
    """

    def inner(func):
        def create_user_and_invoke_test():
            client = boto3.client("iam", "us-east-1")
            user_name = f"testuser_{str(uuid4())[0:6]}"
            try:
                if create_user:
                    client.create_user(UserName=user_name)
                return func(user_name=user_name)
            finally:
                if create_user:
                    certificates = client.list_signing_certificates(UserName=user_name)[
                        "Certificates"
                    ]

                    for cert in certificates:
                        client.delete_signing_certificate(
                            UserName=user_name, CertificateId=cert["CertificateId"]
                        )
                    client.delete_user(UserName=user_name)

        @wraps(func)
        def pagination_wrapper():
            if allow_aws_request():
                return create_user_and_invoke_test()
            else:
                with mock_aws():
                    return create_user_and_invoke_test()

        return pagination_wrapper

    return inner
