import boto3
import json
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_iam, mock_s3, settings
from moto.core import set_initial_no_auth_action_count
from unittest import SkipTest


@mock_s3
@set_initial_no_auth_action_count(0)
def test_load_unexisting_object_without_auth_should_return_403():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Auth decorator does not work in server mode")

    """Head an S3 object we should have no access to."""
    resource = boto3.resource("s3", region_name="us-east-1")

    obj = resource.Object("myfakebucket", "myfakekey")
    with pytest.raises(ClientError) as ex:
        obj.load()
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidAccessKeyId")
    err["Message"].should.equal(
        "The AWS Access Key Id you provided does not exist in our records."
    )


@set_initial_no_auth_action_count(4)
@mock_s3
def test_head_bucket_with_correct_credentials():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Auth decorator does not work in server mode")

    # These calls are all unauthenticated
    iam_keys = create_user_with_access_key_and_policy()

    # This S3-client has correct credentials
    s3 = boto3.client(
        "s3",
        aws_access_key_id=iam_keys["AccessKeyId"],
        aws_secret_access_key=iam_keys["SecretAccessKey"],
    )
    s3.create_bucket(Bucket="mock_bucket")

    # Calling head_bucket with the correct credentials works
    my_head_bucket(
        "mock_bucket",
        aws_access_key_id=iam_keys["AccessKeyId"],
        aws_secret_access_key=iam_keys["SecretAccessKey"],
    )


@set_initial_no_auth_action_count(4)
@mock_s3
def test_head_bucket_with_incorrect_credentials():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Auth decorator does not work in server mode")

    # These calls are all authenticated
    iam_keys = create_user_with_access_key_and_policy()

    # Create the bucket with correct credentials
    s3 = boto3.client(
        "s3",
        aws_access_key_id=iam_keys["AccessKeyId"],
        aws_secret_access_key=iam_keys["SecretAccessKey"],
    )
    s3.create_bucket(Bucket="mock_bucket")

    # Call head_bucket with incorrect credentials
    with pytest.raises(ClientError) as ex:
        my_head_bucket(
            "mock_bucket",
            aws_access_key_id=iam_keys["AccessKeyId"],
            aws_secret_access_key="invalid",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("SignatureDoesNotMatch")
    err["Message"].should.equal(
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
