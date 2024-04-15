import boto3
import pytest

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
