from unittest import SkipTest, mock

import boto3
import pytest

from moto import mock_aws, settings

from . import s3_aws_verified


@pytest.mark.aws_verified
@s3_aws_verified
def test_s3_filter_with_manual_marker(name=None) -> None:
    """
    Batch manually:
    1. Get list of all items, but only take first 5
    2. Get list of items, starting at position 5 - only take first 5
    3. Get list of items, starting at position 10 - only take first 5
    4. Get list of items starting at position 15

    If the user paginates using the PageSize-argument, Moto stores/returns a custom NextMarker-attribute

    This test verifies that it is possible to pass an existing key-name as the Marker-attribute
    """
    bucket = boto3.resource("s3", "us-east-1").Bucket(name)

    def batch_from(marker: str, *, batch_size: int):
        first: str | None = None
        ret = []

        for obj in bucket.objects.filter(Marker=marker):
            if first is None:
                first = obj.key
            ret.append(obj)
            if len(ret) >= batch_size:
                break

        return ret

    keys = [f"key_{i:02d}" for i in range(17)]
    for key in keys:
        bucket.put_object(Body=f"hello {key}".encode(), Key=key)

    marker = ""
    batch_size = 5
    pages = []

    while batch := batch_from(marker, batch_size=batch_size):
        pages.append([b.key for b in batch])
        marker = batch[-1].key

    assert len(pages) == 4
    assert pages[0] == ["key_00", "key_01", "key_02", "key_03", "key_04"]
    assert pages[1] == ["key_05", "key_06", "key_07", "key_08", "key_09"]
    assert pages[2] == ["key_10", "key_11", "key_12", "key_13", "key_14"]
    assert pages[3] == ["key_15", "key_16"]


@mock_aws
@mock.patch.dict("os.environ", {"MOTO_S3_DEFAULT_MAX_KEYS": "5"})
def test_list_object_versions_with_custom_limit():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only set env var in DecoratorMode")
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_resource = boto3.resource("s3", region_name="us-east-1")
    bucket_name = "foobar"
    bucket = s3_resource.Bucket(bucket_name)
    bucket.create()

    for i in range(8):
        s3_client.put_object(Bucket=bucket_name, Key=f"obj_{i}", Body=b"data")

    page1 = s3_client.list_objects(Bucket=bucket_name)
    assert page1["MaxKeys"] == 5
    assert len(page1["Contents"]) == 5

    page2 = s3_client.list_objects(Bucket=bucket_name, Marker=page1["NextMarker"])
    assert page2["MaxKeys"] == 5
    assert len(page2["Contents"]) == 3

    page1 = s3_client.list_objects_v2(Bucket=bucket_name)
    assert page1["MaxKeys"] == 5
    assert len(page1["Contents"]) == 5

    page2 = s3_client.list_objects_v2(
        Bucket=bucket_name, ContinuationToken=page1["NextContinuationToken"]
    )
    assert page2["MaxKeys"] == 5
    assert len(page2["Contents"]) == 3
