from functools import wraps
from uuid import uuid4

import boto3

from moto import mock_aws
from tests import allow_aws_request


def sqs_aws_verified():
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.

    This decorator will:
      - Create an SQS queue
      - Run the test and pass the queue_name as an argument
      - Delete the queue
    """

    def inner(func):
        @wraps(func)
        def pagination_wrapper(**kwargs):
            queue_name = "q" + str(uuid4())[0:6]
            kwargs["queue_name"] = queue_name

            def create_queue_and_test():
                client = boto3.client("sqs", region_name="us-east-1")

                queue_url = client.create_queue(QueueName=queue_name)["QueueUrl"]
                kwargs["queue_url"] = queue_url
                try:
                    resp = func(**kwargs)
                finally:
                    client.delete_queue(QueueUrl=queue_url)

                return resp

            if allow_aws_request():
                return create_queue_and_test()
            else:
                with mock_aws():
                    return create_queue_and_test()

        return pagination_wrapper

    return inner
