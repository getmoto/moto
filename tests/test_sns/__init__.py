import json
import os
from functools import wraps
from unittest import SkipTest
from uuid import uuid4

import boto3
import botocore

from moto import mock_aws
from tests import allow_aws_request


def sns_aws_verified(func):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.
    """

    @wraps(func)
    def pagination_wrapper():
        allow_aws_request = (
            os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"
        )

        if allow_aws_request:
            ssm = boto3.client("ssm", "us-east-1")
            try:
                param = ssm.get_parameter(
                    Name="/moto/tests/ses/firebase_api_key", WithDecryption=True
                )
                api_key = param["Parameter"]["Value"]
                resp = func(api_key)
            except botocore.exceptions.ClientError:
                # SNS tests try to create a PlatformApplication that connects to GCM
                # (Google Cloud Messaging, also known as Firebase Messaging)
                # That requires an account and an API key
                # If the API key has not been configured in SSM, we'll just skip the test
                #
                # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sns/client/create_platform_application.html
                # AWS calls it 'API key', but Firebase calls it Server Key
                #
                # https://stackoverflow.com/a/75896532/13245310
                raise SkipTest("Can't execute SNS tests without Firebase API key")
        else:
            with mock_aws():
                resp = func("mock_api_key")
        return resp

    return pagination_wrapper


def sns_sqs_aws_verified():
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.

    This decorator will:
      - Create an SNS topic + SQS queue
      - Run the test, passing both names as an argument
      - Delete both resources
    """

    def inner(func):
        @wraps(func)
        def pagination_wrapper(**kwargs):
            topic_name = f"test_topic_{str(uuid4())[0:6]}"
            kwargs["topic_name"] = topic_name
            queue_name = f"test_queue_{str(uuid4())[0:6]}"
            kwargs["queue_name"] = queue_name

            def create_resources_and_test():
                client = boto3.client("sns", region_name="us-east-1")
                sqs_client = boto3.resource("sqs", region_name="us-east-1")

                topic_arn = client.create_topic(Name=topic_name)["TopicArn"]
                kwargs["topic_arn"] = topic_arn

                queue = sqs_client.create_queue(QueueName=queue_name)

                identity = boto3.client("sts", "us-east-1").get_caller_identity()
                queue_arn = f"arn:aws:sqs:us-east-1:{identity['Account']}:{queue_name}"

                # Give permissions to the queue
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "sns.amazonaws.com"},
                            "Action": "sqs:SendMessage",
                            "Resource": queue_arn,
                            "Condition": {"ArnEquals": {"aws:SourceArn": topic_arn}},
                        }
                    ],
                }
                queue.set_attributes(Attributes={"Policy": json.dumps(policy)})

                # Subscribe the Queue to the Topic
                subscription_arn = client.subscribe(
                    TopicArn=topic_arn,
                    Protocol="sqs",
                    Endpoint=queue_arn,
                )["SubscriptionArn"]

                try:
                    resp = func(**kwargs)
                finally:
                    client.unsubscribe(SubscriptionArn=subscription_arn)
                    client.delete_topic(TopicArn=topic_arn)
                    queue.delete()

                return resp

            if allow_aws_request():
                return create_resources_and_test()
            else:
                with mock_aws():
                    return create_resources_and_test()

        return pagination_wrapper

    return inner
