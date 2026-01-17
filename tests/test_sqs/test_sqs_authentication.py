import json

import boto3
import pytest

from moto import mock_aws, settings
from moto.core import enable_iam_authentication


@mock_aws
def test_access_for_specific_arn_to_all_sqs_actions():
    if not settings.TEST_DECORATOR_MODE:
        pytest.skip("ContextManagers can only be tested in DecoratorMode")
    sqs = boto3.resource("sqs", "us-east-1")
    queue = sqs.create_queue(QueueName="test-queue")
    queue_arn = queue.attributes["QueueArn"]

    iam = boto3.client("iam", "us-east-1")
    role_arn = iam.create_role(
        RoleName="test-role",
        AssumeRolePolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
    )["Role"]["Arn"]

    policy_arn = iam.create_policy(
        PolicyName="test-policy",
        PolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {"Effect": "Allow", "Action": "sqs:*", "Resource": queue_arn}
                ],
            }
        ),
    )["Policy"]["Arn"]

    iam.attach_role_policy(RoleName="test-role", PolicyArn=policy_arn)

    sts = boto3.client("sts", "us-east-1")
    credentials = sts.assume_role(RoleArn=role_arn, RoleSessionName="test-session")[
        "Credentials"
    ]

    with enable_iam_authentication():
        restricted_sqs = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        ).resource("sqs", "us-east-1")
        restricted_queue = restricted_sqs.Queue(queue.url)
        restricted_queue.send_message(MessageBody="Test message with IAM auth")
