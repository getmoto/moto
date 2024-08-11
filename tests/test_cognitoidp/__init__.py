import os
from functools import wraps
from uuid import uuid4

import boto3

from moto import mock_aws


def cognitoidp_aws_verified(
    username_attributes=None,
    read_attributes=None,
    explicit_auth_flows=None,
    generate_secret=False,
    recovery=None,
    verified_attributes=None,
):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.

    This decorator will:
      - Create a UserPool
      - Run the test and pass the name as an argument
      - Delete the UserPool
    """

    def inner(func):
        @wraps(func)
        def pagination_wrapper(*args, **kwargs):
            def create_user_pool_and_test():
                conn = boto3.client("cognito-idp", "us-west-2")
                pool_name = f"TestUserPool_{str(uuid4())[0:6]}"
                userpool_args = {}
                if username_attributes:
                    userpool_args["UsernameAttributes"] = username_attributes
                if recovery:
                    userpool_args["AccountRecoverySetting"] = {
                        "RecoveryMechanisms": recovery
                    }
                if verified_attributes:
                    userpool_args["AutoVerifiedAttributes"] = verified_attributes
                user_pool = conn.create_user_pool(PoolName=pool_name, **userpool_args)
                pool_id = user_pool["UserPool"]["Id"]
                pool_client_kwargs = {}
                if read_attributes:
                    pool_client_kwargs["ReadAttributes"] = read_attributes
                if explicit_auth_flows:
                    pool_client_kwargs["ExplicitAuthFlows"] = explicit_auth_flows
                if generate_secret:
                    pool_client_kwargs["GenerateSecret"] = True

                try:
                    user_pool_client = conn.create_user_pool_client(
                        UserPoolId=pool_id,
                        ClientName="TestAppClient",
                        **pool_client_kwargs,
                    )

                    kwargs["user_pool"] = user_pool
                    kwargs["user_pool_client"] = user_pool_client
                    resp = func(*args, **kwargs)
                finally:
                    conn.delete_user_pool(UserPoolId=pool_id)

                return resp

            allow_aws_request = (
                os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"
            )

            if allow_aws_request:
                return create_user_pool_and_test()
            else:
                with mock_aws():
                    return create_user_pool_and_test()

        return pagination_wrapper

    return inner
