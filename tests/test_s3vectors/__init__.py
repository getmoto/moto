from functools import wraps
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

from moto import mock_aws
from tests import allow_aws_request


def s3vectors_aws_verified(
    create_bucket: bool = True,
):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.

    This decorator will:
      - Create a S3Vector bucket
      - Run the test and pass the bucket_name as an argument
      - Delete the bucket
    """

    def inner(func):
        @wraps(func)
        def pagination_wrapper(**kwargs):
            bucket_name = str(uuid4())
            if create_bucket:
                kwargs["bucket_name"] = bucket_name

            def create_bucket_and_test():
                client = boto3.client("s3vectors", region_name="us-east-1")

                client.create_vector_bucket(
                    vectorBucketName=kwargs["bucket_name"],
                )
                try:
                    resp = func(**kwargs)
                finally:
                    try:
                        indexes = client.list_indexes(vectorBucketName=bucket_name)[
                            "indexes"
                        ]
                        for index in indexes:
                            client.delete_index(
                                vectorBucketName=bucket_name,
                                indexName=index["indexName"],
                            )
                        client.delete_vector_bucket(vectorBucketName=bucket_name)
                    except ClientError as e:
                        # Bucket may have been deleted in the test itself
                        assert e.response["Error"]["Code"] == "NotFoundException", e

                return resp

            if allow_aws_request():
                if create_bucket:
                    print(f"Test {func} will create Vector Bucket {bucket_name}")  # noqa
                    return create_bucket_and_test()
                else:
                    return func(**kwargs)
            else:
                with mock_aws():
                    if create_bucket:
                        return create_bucket_and_test()
                    else:
                        return func(**kwargs)

        return pagination_wrapper

    return inner
