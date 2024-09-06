import json
from functools import wraps
from time import sleep
from uuid import uuid4

import boto3

from moto import mock_aws
from tests import allow_aws_request


def cognitoidp_aws_verified(
    username_attributes=None,
    read_attributes=None,
    explicit_auth_flows=None,
    generate_secret=False,
    recovery=None,
    verified_attributes=None,
    with_mfa=None,
    with_software_mfa=True,
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
                if with_mfa:
                    iam = boto3.client("iam", "us-east-1")
                    assume_policy_doc = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Sid": "Statement1",
                                "Effect": "Allow",
                                "Principal": {"Service": "cognito-idp.amazonaws.com"},
                                "Action": "sts:AssumeRole",
                            }
                        ],
                    }
                    role_name = f"test-role-{str(uuid4())[0:6]}"
                    role = iam.create_role(
                        RoleName=role_name,
                        AssumeRolePolicyDocument=json.dumps(assume_policy_doc),
                    )
                    role_arn = role["Role"]["Arn"]

                    policy_name = f"test-policy-{str(uuid4())[0:6]}"
                    policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": "sns:Publish",
                                "Resource": "*",
                            }
                        ],
                    }
                    policy_arn = iam.create_policy(
                        PolicyName=policy_name,
                        PolicyDocument=json.dumps(policy),
                        Path="/",
                    )["Policy"]["Arn"]
                    iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
                    if allow_aws_request():
                        # IAM roles are not immediately ready for use
                        sleep(10)
                    userpool_args["MfaConfiguration"] = with_mfa
                    userpool_args["SmsConfiguration"] = {"SnsCallerArn": role_arn}
                if verified_attributes:
                    userpool_args["AutoVerifiedAttributes"] = verified_attributes
                user_pool = conn.create_user_pool(PoolName=pool_name, **userpool_args)
                pool_id = user_pool["UserPool"]["Id"]

                if with_mfa and with_software_mfa:
                    conn.set_user_pool_mfa_config(
                        UserPoolId=pool_id,
                        SoftwareTokenMfaConfiguration={"Enabled": True},
                        MfaConfiguration=with_mfa,
                    )

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
                    if with_mfa:
                        iam.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
                        iam.delete_policy(PolicyArn=policy_arn)
                        iam.delete_role(RoleName=role_name)

                return resp

            if allow_aws_request():
                return create_user_pool_and_test()
            else:
                with mock_aws():
                    return create_user_pool_and_test()

        return pagination_wrapper

    return inner
