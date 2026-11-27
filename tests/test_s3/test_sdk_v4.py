"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_s3 import S3Client, S3Config
    from aws_sdk_s3.models import NoSuchKey
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-s3 is not installed", allow_module_level=True)


@mock_aws
def test_document_archive():
    """Upload documents, list and download them, then move them to an archive."""
    config = S3Config.resolve(region="us-east-1")
    bucket = f"documents-{uuid4()}"

    with S3Client(config=config) as client:
        client.create_bucket(bucket=bucket)
        for name in ["invoice-001.txt", "invoice-002.txt"]:
            client.put_object(
                bucket=bucket,
                key=f"inbox/{name}",
                body=f"contents of {name}".encode(),
                content_type="text/plain",
                metadata={"customer": "acme"},
            )

        listing = client.list_objects_v2(bucket=bucket, prefix="inbox/")
        assert [obj.key for obj in listing.contents or []] == [
            "inbox/invoice-001.txt",
            "inbox/invoice-002.txt",
        ]

        document = client.get_object(bucket=bucket, key="inbox/invoice-001.txt")
        assert document.body.read() == b"contents of invoice-001.txt"
        assert document.content_type == "text/plain"
        assert document.metadata == {"customer": "acme"}

        # Move every document from the inbox to the archive
        for obj in listing.contents or []:
            client.copy_object(
                bucket=bucket,
                copy_source=f"{bucket}/{obj.key}",
                key=obj.key.replace("inbox/", "archive/"),
            )
        deleted = client.delete_objects(
            bucket=bucket,
            delete={"objects": [{"key": obj.key} for obj in listing.contents or []]},
        )
        assert len(deleted.deleted or []) == 2

        archive = client.list_objects_v2(bucket=bucket)
        assert [obj.key for obj in archive.contents or []] == [
            "archive/invoice-001.txt",
            "archive/invoice-002.txt",
        ]

        with pytest.raises(NoSuchKey):
            client.get_object(bucket=bucket, key="inbox/invoice-001.txt")
