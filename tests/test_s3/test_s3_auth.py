import json
from unittest import SkipTest

import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_iam, mock_s3, mock_sts, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID, set_initial_no_auth_action_count


@mock_s3
@set_initial_no_auth_action_count(0)
def test_load_unexisting_object_without_auth_should_return_403():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Auth decorator does not work in server mode")

    # Head an S3 object we should have no access to.
    resource = boto3.resource("s3", region_name="us-east-1")

    obj = resource.Object("myfakebucket", "myfakekey")
    with pytest.raises(ClientError) as ex:
        obj.load()
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidAccessKeyId"
    assert err["Message"] == (
        "The AWS Access Key Id you provided does not exist in our records."
    )


@set_initial_no_auth_action_count(4)
@mock_s3
def test_head_bucket_with_correct_credentials():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Auth decorator does not work in server mode")

    # These calls are all unauthenticated
    iam_keys = create_user_with_access_key_and_policy()

    # This S3-client has correct credentials
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=iam_keys["AccessKeyId"],
        aws_secret_access_key=iam_keys["SecretAccessKey"],
    )
    s3_client.create_bucket(Bucket="mock_bucket")

    # Calling head_bucket with the correct credentials works
    my_head_bucket(
        "mock_bucket",
        aws_access_key_id=iam_keys["AccessKeyId"],
        aws_secret_access_key=iam_keys["SecretAccessKey"],
    )

    # Verify we can make calls that contain a querystring.  Specifically,
    # verify that we are able to build/match the AWS signature for a URL
    # with a querystring.
    s3_client.get_bucket_location(Bucket="mock_bucket")
    s3_client.list_objects_v2(Bucket="mock_bucket")


@set_initial_no_auth_action_count(4)
@mock_s3
def test_head_bucket_with_incorrect_credentials():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Auth decorator does not work in server mode")

    # These calls are all authenticated
    iam_keys = create_user_with_access_key_and_policy()

    # Create the bucket with correct credentials
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=iam_keys["AccessKeyId"],
        aws_secret_access_key=iam_keys["SecretAccessKey"],
    )
    s3_client.create_bucket(Bucket="mock_bucket")

    # Call head_bucket with incorrect credentials
    with pytest.raises(ClientError) as ex:
        my_head_bucket(
            "mock_bucket",
            aws_access_key_id=iam_keys["AccessKeyId"],
            aws_secret_access_key="invalid",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "SignatureDoesNotMatch"
    assert err["Message"] == (
        "The request signature we calculated does not match the signature you provided. "
        "Check your key and signing method."
    )


def my_head_bucket(bucket, aws_access_key_id, aws_secret_access_key):
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    s3_client.head_bucket(Bucket=bucket)


@mock_iam
def create_user_with_access_key_and_policy(user_name="test-user"):
    """
    Should create a user with attached policy allowing read/write operations on S3.
    """
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}],
    }

    # Create client and user
    client = boto3.client("iam", region_name="us-east-1")
    client.create_user(UserName=user_name)

    # Create and attach the policy
    policy_arn = client.create_policy(
        PolicyName="policy1", PolicyDocument=json.dumps(policy_document)
    )["Policy"]["Arn"]
    client.attach_user_policy(UserName=user_name, PolicyArn=policy_arn)

    # Return the access keys
    return client.create_access_key(UserName=user_name)["AccessKey"]


@mock_iam
@mock_sts
def create_role_with_attached_policy_and_assume_it(
    role_name,
    trust_policy_document,
    policy_document,
    session_name="session1",
    policy_name="policy1",
):
    iam_client = boto3.client("iam", region_name="us-east-1")
    sts_client = boto3.client("sts", region_name="us-east-1")
    role_arn = iam_client.create_role(
        RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust_policy_document)
    )["Role"]["Arn"]
    policy_arn = iam_client.create_policy(
        PolicyName=policy_name, PolicyDocument=json.dumps(policy_document)
    )["Policy"]["Arn"]
    iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    return sts_client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)[
        "Credentials"
    ]


@set_initial_no_auth_action_count(7)
@mock_iam
@mock_s3
@mock_sts
def test_delete_objects_without_access_throws_custom_error():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Auth decorator does not work in server mode")

    role_name = "some-test-role"
    bucket_name = "some-test-bucket"

    # Setup Bucket
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket=bucket_name)
    client.put_object(Bucket=bucket_name, Key="some/prefix/test_file.txt")

    trust_policy_document = {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Principal": {"AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"},
            "Action": "sts:AssumeRole",
        },
    }

    # Setup User with the correct access
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
                "Resource": f"arn:aws:s3:::{bucket_name}",
            },
            {
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:GetObject"],
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
            },
        ],
    }
    credentials = create_role_with_attached_policy_and_assume_it(
        role_name, trust_policy_document, policy_document
    )

    session = boto3.session.Session(region_name="us-east-1")
    s3_resource = session.resource(
        "s3",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    bucket = s3_resource.Bucket(bucket_name)

    # This action is not allowed.
    # It should return a 200-response, with the body indicating that we
    # do not have access.
    response = bucket.objects.filter(Prefix="some/prefix").delete()[0]
    assert len(response["Errors"]) == 1

    error = response["Errors"][0]
    assert error["Key"] == "some/prefix/test_file.txt"
    assert error["Code"] == "AccessDenied"
    assert error["Message"] == "Access Denied"
