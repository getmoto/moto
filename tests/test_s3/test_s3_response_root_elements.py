"""Verify the root XML element of S3 responses match AWS.

boto3 ignores the root element when parsing rest-xml responses,
but other SDK clients fail if it's not an exact match.
"""

import uuid
import xml.etree.ElementTree as ET

import boto3
import pytest

from moto import mock_aws
from moto.s3.responses import DEFAULT_REGION_NAME


def _create_multipart_upload_with_part(client, bucket):
    upload_id = client.create_multipart_upload(Bucket=bucket, Key="key")["UploadId"]
    etag = client.upload_part(
        Bucket=bucket, Key="key", UploadId=upload_id, PartNumber=1, Body=b"data"
    )["ETag"]
    return upload_id, etag


def _complete_multipart_upload(client, bucket):
    upload_id, etag = _create_multipart_upload_with_part(client, bucket)
    client.complete_multipart_upload(
        Bucket=bucket,
        Key="key",
        UploadId=upload_id,
        MultipartUpload={"Parts": [{"ETag": etag, "PartNumber": 1}]},
    )


def _get_bucket_accelerate_configuration(client, bucket):
    client.put_bucket_accelerate_configuration(
        Bucket=bucket, AccelerateConfiguration={"Status": "Enabled"}
    )
    client.get_bucket_accelerate_configuration(Bucket=bucket)


def _get_bucket_versioning(client, bucket):
    client.put_bucket_versioning(
        Bucket=bucket, VersioningConfiguration={"Status": "Enabled"}
    )
    client.get_bucket_versioning(Bucket=bucket)


def _list_bucket_inventory_configurations(client, bucket):
    client.list_bucket_inventory_configurations(Bucket=bucket)


def _list_parts(client, bucket):
    upload_id, _ = _create_multipart_upload_with_part(client, bucket)
    client.list_parts(Bucket=bucket, Key="key", UploadId=upload_id)


@pytest.mark.parametrize(
    "operation_name,call,expected_root",
    [
        (
            "CompleteMultipartUpload",
            _complete_multipart_upload,
            "CompleteMultipartUploadResult",
        ),
        (
            "GetBucketAccelerateConfiguration",
            _get_bucket_accelerate_configuration,
            "AccelerateConfiguration",
        ),
        ("GetBucketVersioning", _get_bucket_versioning, "VersioningConfiguration"),
        (
            "ListBucketInventoryConfigurations",
            _list_bucket_inventory_configurations,
            "ListInventoryConfigurationsResult",
        ),
        ("ListParts", _list_parts, "ListPartsResult"),
    ],
)
@mock_aws
def test_response_root_element(operation_name, call, expected_root):
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = str(uuid.uuid4())
    client.create_bucket(Bucket=bucket)

    raw_bodies = {}

    def capture_body(http_response, model, **kwargs):
        raw_bodies[model.name] = http_response.content

    client.meta.events.register("after-call.s3", capture_body)

    call(client, bucket)

    root = ET.fromstring(raw_bodies[operation_name])
    assert root.tag == f"{{http://s3.amazonaws.com/doc/2006-03-01/}}{expected_root}"
