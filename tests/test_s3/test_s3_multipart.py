import os
import re
from functools import wraps
from io import BytesIO
from unittest import SkipTest

import boto3
import pytest
import requests
from botocore.client import ClientError

import moto.s3.models as s3model
from moto import mock_aws, settings
from moto.s3.responses import DEFAULT_REGION_NAME
from moto.settings import (
    S3_UPLOAD_PART_MIN_SIZE,
    get_s3_default_key_buffer_size,
    is_test_proxy_mode,
)
from tests import DEFAULT_ACCOUNT_ID

from .test_s3 import add_proxy_details

if settings.TEST_DECORATOR_MODE:
    REDUCED_PART_SIZE = 256
    EXPECTED_ETAG = '"66d1a1a2ed08fd05c137f316af4ff255-2"'
else:
    REDUCED_PART_SIZE = S3_UPLOAD_PART_MIN_SIZE
    EXPECTED_ETAG = '"140f92a6df9f9e415f74a1463bcee9bb-2"'


def reduced_min_part_size(func):
    """Speed up tests by temporarily making multipart min. part size small."""
    orig_size = S3_UPLOAD_PART_MIN_SIZE

    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            s3model.S3_UPLOAD_PART_MIN_SIZE = REDUCED_PART_SIZE
            return func(*args, **kwargs)
        finally:
            s3model.S3_UPLOAD_PART_MIN_SIZE = orig_size

    return wrapped


@mock_aws
def test_default_key_buffer_size():
    # save original DEFAULT_KEY_BUFFER_SIZE environment variable content
    original_default_key_buffer_size = os.environ.get(
        "MOTO_S3_DEFAULT_KEY_BUFFER_SIZE", None
    )

    os.environ["MOTO_S3_DEFAULT_KEY_BUFFER_SIZE"] = "2"  # 2 bytes
    assert get_s3_default_key_buffer_size() == 2
    fake_key = s3model.FakeKey("a", os.urandom(1), account_id=DEFAULT_ACCOUNT_ID)
    assert fake_key._value_buffer._rolled is False

    os.environ["MOTO_S3_DEFAULT_KEY_BUFFER_SIZE"] = "1"  # 1 byte
    assert get_s3_default_key_buffer_size() == 1
    fake_key = s3model.FakeKey("a", os.urandom(3), account_id=DEFAULT_ACCOUNT_ID)
    assert fake_key._value_buffer._rolled is True

    # if no MOTO_S3_DEFAULT_KEY_BUFFER_SIZE env variable is present the
    # buffer size should be less than S3_UPLOAD_PART_MIN_SIZE to prevent
    # in memory caching of multi part uploads.
    del os.environ["MOTO_S3_DEFAULT_KEY_BUFFER_SIZE"]
    assert get_s3_default_key_buffer_size() < S3_UPLOAD_PART_MIN_SIZE

    # restore original environment variable content
    if original_default_key_buffer_size:
        os.environ["MOTO_S3_DEFAULT_KEY_BUFFER_SIZE"] = original_default_key_buffer_size


@mock_aws
def test_multipart_upload_too_small():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket="foobar")

    multipart = client.create_multipart_upload(Bucket="foobar", Key="the-key")
    up1 = client.upload_part(
        Body=BytesIO(b"hello"),
        PartNumber=1,
        Bucket="foobar",
        Key="the-key",
        UploadId=multipart["UploadId"],
    )
    up2 = client.upload_part(
        Body=BytesIO(b"world"),
        PartNumber=2,
        Bucket="foobar",
        Key="the-key",
        UploadId=multipart["UploadId"],
    )
    # Multipart with total size under 5MB is refused
    with pytest.raises(ClientError) as ex:
        client.complete_multipart_upload(
            Bucket="foobar",
            Key="the-key",
            MultipartUpload={
                "Parts": [
                    {"ETag": up1["ETag"], "PartNumber": 1},
                    {"ETag": up2["ETag"], "PartNumber": 2},
                ]
            },
            UploadId=multipart["UploadId"],
        )
    assert ex.value.response["Error"]["Code"] == "EntityTooSmall"
    assert ex.value.response["Error"]["Message"] == (
        "Your proposed upload is smaller than the minimum allowed object size."
    )


@pytest.mark.parametrize("key", ["the-key", "the%20key"])
@mock_aws
@reduced_min_part_size
def test_multipart_upload(key: str):
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket="foobar")

    part1 = b"0" * REDUCED_PART_SIZE
    part2 = b"1"
    multipart = client.create_multipart_upload(Bucket="foobar", Key=key)
    up1 = client.upload_part(
        Body=BytesIO(part1),
        PartNumber=1,
        Bucket="foobar",
        Key=key,
        UploadId=multipart["UploadId"],
    )
    up2 = client.upload_part(
        Body=BytesIO(part2),
        PartNumber=2,
        Bucket="foobar",
        Key=key,
        UploadId=multipart["UploadId"],
    )

    client.complete_multipart_upload(
        Bucket="foobar",
        Key=key,
        MultipartUpload={
            "Parts": [
                {"ETag": up1["ETag"], "PartNumber": 1},
                {"ETag": up2["ETag"], "PartNumber": 2},
            ]
        },
        UploadId=multipart["UploadId"],
    )
    # we should get both parts as the key contents
    response = client.get_object(Bucket="foobar", Key=key)
    assert response["Body"].read() == part1 + part2


@mock_aws
@reduced_min_part_size
def test_multipart_upload_out_of_order():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket="foobar")

    part1 = b"0" * REDUCED_PART_SIZE
    part2 = b"1"
    multipart = client.create_multipart_upload(Bucket="foobar", Key="the-key")
    up1 = client.upload_part(
        Body=BytesIO(part1),
        PartNumber=4,
        Bucket="foobar",
        Key="the-key",
        UploadId=multipart["UploadId"],
    )
    up2 = client.upload_part(
        Body=BytesIO(part2),
        PartNumber=2,
        Bucket="foobar",
        Key="the-key",
        UploadId=multipart["UploadId"],
    )

    client.complete_multipart_upload(
        Bucket="foobar",
        Key="the-key",
        MultipartUpload={
            "Parts": [
                {"ETag": up1["ETag"], "PartNumber": 4},
                {"ETag": up2["ETag"], "PartNumber": 2},
            ]
        },
        UploadId=multipart["UploadId"],
    )
    # we should get both parts as the key contents
    response = client.get_object(Bucket="foobar", Key="the-key")
    assert response["Body"].read() == part1 + part2


@mock_aws
@reduced_min_part_size
def test_multipart_upload_with_headers():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "fancymultiparttest"
    key_name = "the-key"
    s3_resource.create_bucket(Bucket=bucket_name)

    part1 = b"0" * REDUCED_PART_SIZE
    multipart = client.create_multipart_upload(
        Bucket=bucket_name,
        Key=key_name,
        Metadata={"meta": "data"},
        StorageClass="STANDARD_IA",
        ACL="authenticated-read",
    )
    up1 = client.upload_part(
        Body=BytesIO(part1),
        PartNumber=1,
        Bucket=bucket_name,
        Key=key_name,
        UploadId=multipart["UploadId"],
    )

    client.complete_multipart_upload(
        Bucket=bucket_name,
        Key=key_name,
        MultipartUpload={"Parts": [{"ETag": up1["ETag"], "PartNumber": 1}]},
        UploadId=multipart["UploadId"],
    )
    # we should get both parts as the key contents
    response = client.get_object(Bucket=bucket_name, Key=key_name)
    assert response["Metadata"] == {"meta": "data"}
    assert response["StorageClass"] == "STANDARD_IA"

    grants = client.get_object_acl(Bucket=bucket_name, Key=key_name)["Grants"]
    assert len(grants) == 2
    assert {
        "Grantee": {
            "Type": "Group",
            "URI": "http://acs.amazonaws.com/groups/global/AuthenticatedUsers",
        },
        "Permission": "READ",
    } in grants


@pytest.mark.parametrize(
    "original_key_name",
    [
        "original-key",
        "the-unicode-💩-key",
        "key-with?question-mark",
        "key-with%2Fembedded%2Furl%2Fencoding",
    ],
)
@mock_aws
@reduced_min_part_size
def test_multipart_upload_with_copy_key(original_key_name):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="foobar")
    s3_client.put_object(Bucket="foobar", Key=original_key_name, Body="key_value")

    mpu = s3_client.create_multipart_upload(Bucket="foobar", Key="the-key")
    part1 = b"0" * REDUCED_PART_SIZE
    up1 = s3_client.upload_part(
        Bucket="foobar",
        Key="the-key",
        PartNumber=1,
        UploadId=mpu["UploadId"],
        Body=BytesIO(part1),
    )
    up2 = s3_client.upload_part_copy(
        Bucket="foobar",
        Key="the-key",
        CopySource={"Bucket": "foobar", "Key": original_key_name},
        CopySourceRange="0-3",
        PartNumber=2,
        UploadId=mpu["UploadId"],
    )
    s3_client.complete_multipart_upload(
        Bucket="foobar",
        Key="the-key",
        MultipartUpload={
            "Parts": [
                {"ETag": up1["ETag"], "PartNumber": 1},
                {"ETag": up2["CopyPartResult"]["ETag"], "PartNumber": 2},
            ]
        },
        UploadId=mpu["UploadId"],
    )
    response = s3_client.get_object(Bucket="foobar", Key="the-key")
    assert response["Body"].read() == part1 + b"key_"


@mock_aws
@reduced_min_part_size
def test_multipart_upload_cancel():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="foobar")

    mpu = s3_client.create_multipart_upload(Bucket="foobar", Key="the-key")
    part1 = b"0" * REDUCED_PART_SIZE
    s3_client.upload_part(
        Bucket="foobar",
        Key="the-key",
        PartNumber=1,
        UploadId=mpu["UploadId"],
        Body=BytesIO(part1),
    )

    uploads = s3_client.list_multipart_uploads(Bucket="foobar")["Uploads"]
    assert len(uploads) == 1
    assert uploads[0]["Key"] == "the-key"

    s3_client.abort_multipart_upload(
        Bucket="foobar", Key="the-key", UploadId=mpu["UploadId"]
    )

    assert "Uploads" not in s3_client.list_multipart_uploads(Bucket="foobar")


@mock_aws
@reduced_min_part_size
def test_multipart_etag_quotes_stripped():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="foobar")
    s3_client.put_object(Bucket="foobar", Key="original-key", Body="key_value")

    mpu = s3_client.create_multipart_upload(Bucket="foobar", Key="the-key")
    part1 = b"0" * REDUCED_PART_SIZE
    up1 = s3_client.upload_part(
        Bucket="foobar",
        Key="the-key",
        PartNumber=1,
        UploadId=mpu["UploadId"],
        Body=BytesIO(part1),
    )
    etag1 = up1["ETag"].replace('"', "")
    up2 = s3_client.upload_part_copy(
        Bucket="foobar",
        Key="the-key",
        CopySource={"Bucket": "foobar", "Key": "original-key"},
        CopySourceRange="0-3",
        PartNumber=2,
        UploadId=mpu["UploadId"],
    )
    etag2 = up2["CopyPartResult"]["ETag"].replace('"', "")
    s3_client.complete_multipart_upload(
        Bucket="foobar",
        Key="the-key",
        MultipartUpload={
            "Parts": [
                {"ETag": etag1, "PartNumber": 1},
                {"ETag": etag2, "PartNumber": 2},
            ]
        },
        UploadId=mpu["UploadId"],
    )
    response = s3_client.get_object(Bucket="foobar", Key="the-key")
    assert response["Body"].read() == part1 + b"key_"


@mock_aws
@reduced_min_part_size
def test_multipart_duplicate_upload():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource.create_bucket(Bucket="foobar")

    part1 = b"0" * REDUCED_PART_SIZE
    part2 = b"1"
    multipart = client.create_multipart_upload(Bucket="foobar", Key="the-key")
    client.upload_part(
        Body=BytesIO(part1),
        PartNumber=1,
        Bucket="foobar",
        Key="the-key",
        UploadId=multipart["UploadId"],
    )
    # same part again
    up1 = client.upload_part(
        Body=BytesIO(part1),
        PartNumber=1,
        Bucket="foobar",
        Key="the-key",
        UploadId=multipart["UploadId"],
    )
    up2 = client.upload_part(
        Body=BytesIO(part2),
        PartNumber=2,
        Bucket="foobar",
        Key="the-key",
        UploadId=multipart["UploadId"],
    )

    client.complete_multipart_upload(
        Bucket="foobar",
        Key="the-key",
        MultipartUpload={
            "Parts": [
                {"ETag": up1["ETag"], "PartNumber": 1},
                {"ETag": up2["ETag"], "PartNumber": 2},
            ]
        },
        UploadId=multipart["UploadId"],
    )
    # we should get both parts as the key contents
    response = client.get_object(Bucket="foobar", Key="the-key")
    assert response["Body"].read() == part1 + part2


@mock_aws
def test_list_multiparts():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="foobar")

    mpu1 = s3_client.create_multipart_upload(Bucket="foobar", Key="one-key")
    mpu2 = s3_client.create_multipart_upload(Bucket="foobar", Key="two-key")

    uploads = s3_client.list_multipart_uploads(Bucket="foobar")["Uploads"]
    assert len(uploads) == 2
    assert {u["Key"]: u["UploadId"] for u in uploads} == (
        {"one-key": mpu1["UploadId"], "two-key": mpu2["UploadId"]}
    )

    s3_client.abort_multipart_upload(
        Bucket="foobar", Key="the-key", UploadId=mpu2["UploadId"]
    )

    uploads = s3_client.list_multipart_uploads(Bucket="foobar")["Uploads"]
    assert len(uploads) == 1
    assert uploads[0]["Key"] == "one-key"

    s3_client.abort_multipart_upload(
        Bucket="foobar", Key="the-key", UploadId=mpu1["UploadId"]
    )

    res = s3_client.list_multipart_uploads(Bucket="foobar")
    assert "Uploads" not in res


@mock_aws
def test_multipart_should_throw_nosuchupload_if_there_are_no_parts():
    bucket = boto3.resource("s3", region_name=DEFAULT_REGION_NAME).Bucket(
        "randombucketname"
    )
    bucket.create()
    s3_object = bucket.Object("my/test2")

    multipart_upload = s3_object.initiate_multipart_upload()
    multipart_upload.abort()

    with pytest.raises(ClientError) as ex:
        list(multipart_upload.parts.all())
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchUpload"
    assert err["Message"] == (
        "The specified upload does not exist. The upload ID may be invalid, "
        "or the upload may have been aborted or completed."
    )
    assert err["UploadId"] == multipart_upload.id


@mock_aws
def test_multipart_wrong_partnumber():
    bucket_name = "mputest-3593"
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)

    mpu = s3_client.create_multipart_upload(Bucket=bucket_name, Key="the-key")
    mpu_id = mpu["UploadId"]

    body = b"111"
    with pytest.raises(ClientError) as ex:
        s3_client.upload_part(
            Bucket=bucket_name,
            Key="the-key",
            PartNumber=-1,
            UploadId=mpu_id,
            Body=body,
            ContentLength=len(body),
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchUpload"
    assert err["Message"] == (
        "The specified upload does not exist. The upload ID may be invalid, "
        "or the upload may have been aborted or completed."
    )


@mock_aws
def test_multipart_upload_with_tags():
    bucket = "mybucket"
    key = "test/multipartuploadtag/file.txt"
    tags = "a=b"

    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket=bucket)

    response = client.create_multipart_upload(Bucket=bucket, Key=key, Tagging=tags)
    upload = boto3.resource("s3").MultipartUpload(bucket, key, response["UploadId"])
    parts = [
        {
            "ETag": upload.Part(i).upload(Body=os.urandom(5 * (2**20)))["ETag"],
            "PartNumber": i,
        }
        for i in range(1, 3)
    ]

    upload.complete(MultipartUpload={"Parts": parts})

    # check tags
    response = client.get_object_tagging(Bucket=bucket, Key=key)
    actual = {t["Key"]: t["Value"] for t in response.get("TagSet", [])}
    assert actual == {"a": "b"}


@mock_aws
def test_multipart_upload_should_return_part_10000():
    bucket = "dummybucket"
    s3_client = boto3.client("s3", "us-east-1")

    key = "test_file"
    s3_client.create_bucket(Bucket=bucket)

    mpu = s3_client.create_multipart_upload(Bucket=bucket, Key=key)
    mpu_id = mpu["UploadId"]
    s3_client.upload_part(
        Bucket=bucket, Key=key, PartNumber=1, UploadId=mpu_id, Body="data"
    )
    s3_client.upload_part(
        Bucket=bucket, Key=key, PartNumber=2, UploadId=mpu_id, Body="data"
    )
    s3_client.upload_part(
        Bucket=bucket, Key=key, PartNumber=10000, UploadId=mpu_id, Body="data"
    )

    all_parts = s3_client.list_parts(Bucket=bucket, Key=key, UploadId=mpu_id)["Parts"]
    part_nrs = [part["PartNumber"] for part in all_parts]
    assert part_nrs == [1, 2, 10000]


@mock_aws
def test_multipart_upload_without_parts():
    bucket = "dummybucket"
    s3_client = boto3.client("s3", "us-east-1")

    key = "test_file"
    s3_client.create_bucket(Bucket=bucket)

    mpu = s3_client.create_multipart_upload(Bucket=bucket, Key=key)
    mpu_id = mpu["UploadId"]

    list_parts_result = s3_client.list_parts(Bucket=bucket, Key=key, UploadId=mpu_id)
    assert list_parts_result["IsTruncated"] is False


@mock_aws
@pytest.mark.parametrize("part_nr", [10001, 10002, 20000])
def test_s3_multipart_upload_cannot_upload_part_over_10000(part_nr):
    bucket = "dummy"
    s3_client = boto3.client("s3", "us-east-1")

    key = "test_file"
    s3_client.create_bucket(Bucket=bucket)

    mpu = s3_client.create_multipart_upload(Bucket=bucket, Key=key)
    mpu_id = mpu["UploadId"]

    with pytest.raises(ClientError) as exc:
        s3_client.upload_part(
            Bucket=bucket, Key=key, PartNumber=part_nr, UploadId=mpu_id, Body="data"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidArgument"
    assert err["Message"] == (
        "Part number must be an integer between 1 and 10000, inclusive"
    )
    assert err["ArgumentName"] == "partNumber"
    assert err["ArgumentValue"] == f"{part_nr}"


@mock_aws
def test_s3_abort_multipart_data_with_invalid_upload_and_key():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    client.create_bucket(Bucket="blah")

    with pytest.raises(ClientError) as exc:
        client.abort_multipart_upload(
            Bucket="blah", Key="foobar", UploadId="dummy_upload_id"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchUpload"
    assert err["Message"] == (
        "The specified upload does not exist. The upload ID may be invalid, "
        "or the upload may have been aborted or completed."
    )
    assert err["UploadId"] == "dummy_upload_id"


@mock_aws
@reduced_min_part_size
def test_multipart_etag():
    # Create Bucket so that test can run
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")

    upload_id = s3_client.create_multipart_upload(Bucket="mybucket", Key="the-key")[
        "UploadId"
    ]
    part1 = b"0" * REDUCED_PART_SIZE
    etags = []
    etags.append(
        s3_client.upload_part(
            Bucket="mybucket",
            Key="the-key",
            PartNumber=1,
            UploadId=upload_id,
            Body=part1,
        )["ETag"]
    )
    # last part, can be less than 5 MB
    part2 = b"1"
    etags.append(
        s3_client.upload_part(
            Bucket="mybucket",
            Key="the-key",
            PartNumber=2,
            UploadId=upload_id,
            Body=part2,
        )["ETag"]
    )

    s3_client.complete_multipart_upload(
        Bucket="mybucket",
        Key="the-key",
        UploadId=upload_id,
        MultipartUpload={
            "Parts": [
                {"ETag": etag, "PartNumber": i} for i, etag in enumerate(etags, 1)
            ]
        },
    )
    # we should get both parts as the key contents
    resp = s3_client.get_object(Bucket="mybucket", Key="the-key")
    assert resp["ETag"] == EXPECTED_ETAG


@mock_aws
@reduced_min_part_size
def test_multipart_version():
    # Create Bucket so that test can run
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")

    s3_client.put_bucket_versioning(
        Bucket="mybucket", VersioningConfiguration={"Status": "Enabled"}
    )

    upload_id = s3_client.create_multipart_upload(Bucket="mybucket", Key="the-key")[
        "UploadId"
    ]
    part1 = b"0" * REDUCED_PART_SIZE
    etags = []
    etags.append(
        s3_client.upload_part(
            Bucket="mybucket",
            Key="the-key",
            PartNumber=1,
            UploadId=upload_id,
            Body=part1,
        )["ETag"]
    )
    # last part, can be less than 5 MB
    part2 = b"1"
    etags.append(
        s3_client.upload_part(
            Bucket="mybucket",
            Key="the-key",
            PartNumber=2,
            UploadId=upload_id,
            Body=part2,
        )["ETag"]
    )
    response = s3_client.complete_multipart_upload(
        Bucket="mybucket",
        Key="the-key",
        UploadId=upload_id,
        MultipartUpload={
            "Parts": [
                {"ETag": etag, "PartNumber": i} for i, etag in enumerate(etags, 1)
            ]
        },
    )

    assert re.match("[-a-z0-9]+", response["VersionId"])


@mock_aws
@pytest.mark.parametrize(
    "part_nr,msg,msg2",
    [
        (
            -42,
            "Argument max-parts must be an integer between 0 and 2147483647",
            "Argument part-number-marker must be an integer between 0 and 2147483647",
        ),
        (
            2147483647 + 42,
            "Provided max-parts not an integer or within integer range",
            "Provided part-number-marker not an integer or within integer range",
        ),
    ],
)
def test_multipart_list_parts_invalid_argument(part_nr, msg, msg2):
    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "mybucketasdfljoqwerasdfas"
    s3_client.create_bucket(Bucket=bucket_name)

    mpu = s3_client.create_multipart_upload(Bucket=bucket_name, Key="the-key")
    mpu_id = mpu["UploadId"]

    def get_parts(**kwarg):
        s3_client.list_parts(
            Bucket=bucket_name, Key="the-key", UploadId=mpu_id, **kwarg
        )

    with pytest.raises(ClientError) as err:
        get_parts(**{"MaxParts": part_nr})
    err_rsp = err.value.response["Error"]
    assert err_rsp["Code"] == "InvalidArgument"
    assert err_rsp["Message"] == msg

    with pytest.raises(ClientError) as err:
        get_parts(**{"PartNumberMarker": part_nr})
    err_rsp = err.value.response["Error"]
    assert err_rsp["Code"] == "InvalidArgument"
    assert err_rsp["Message"] == msg2


@mock_aws
@reduced_min_part_size
def test_multipart_list_parts():
    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "mybucketasdfljoqwerasdfas"
    s3_client.create_bucket(Bucket=bucket_name)

    mpu = s3_client.create_multipart_upload(Bucket=bucket_name, Key="the-key")
    mpu_id = mpu["UploadId"]

    parts = []
    n_parts = 10

    def get_parts_all(i):
        # Get uploaded parts using default values
        uploaded_parts = []

        uploaded = s3_client.list_parts(
            Bucket=bucket_name, Key="the-key", UploadId=mpu_id
        )

        assert uploaded["PartNumberMarker"] == 0

        # Parts content check
        if i > 0:
            for part in uploaded["Parts"]:
                uploaded_parts.append(
                    {"ETag": part["ETag"], "PartNumber": part["PartNumber"]}
                )
            assert uploaded_parts == parts

            next_part_number_marker = uploaded["Parts"][-1]["PartNumber"]
        else:
            next_part_number_marker = 0

        assert uploaded["NextPartNumberMarker"] == next_part_number_marker

        assert not uploaded["IsTruncated"]

    def get_parts_by_batch(i):
        # Get uploaded parts by batch of 2
        part_number_marker = 0
        uploaded_parts = []

        while "there are parts":
            uploaded = s3_client.list_parts(
                Bucket=bucket_name,
                Key="the-key",
                UploadId=mpu_id,
                PartNumberMarker=part_number_marker,
                MaxParts=2,
            )

            assert uploaded["PartNumberMarker"] == part_number_marker

            if i > 0:
                # We should received maximum 2 parts
                assert len(uploaded["Parts"]) <= 2

                # Store parts content for the final check
                for part in uploaded["Parts"]:
                    uploaded_parts.append(
                        {"ETag": part["ETag"], "PartNumber": part["PartNumber"]}
                    )

            # No more parts, get out the loop
            if not uploaded["IsTruncated"]:
                break

            # Next parts batch will start with that number
            part_number_marker = uploaded["NextPartNumberMarker"]
            assert part_number_marker == i + 1 if len(parts) > i else i

        # Final check: we received all uploaded parts
        assert uploaded_parts == parts

    # Check ListParts API parameters when no part was uploaded
    get_parts_all(0)
    get_parts_by_batch(0)

    for i in range(1, n_parts + 1):
        part_size = REDUCED_PART_SIZE + i
        body = b"1" * part_size
        part = s3_client.upload_part(
            Bucket=bucket_name,
            Key="the-key",
            PartNumber=i,
            UploadId=mpu_id,
            Body=body,
            ContentLength=len(body),
        )
        parts.append({"PartNumber": i, "ETag": part["ETag"]})

        # Check ListParts API parameters while there are uploaded parts
        get_parts_all(i)
        get_parts_by_batch(i)

    # Check ListParts API parameters when all parts were uploaded
    get_parts_all(11)
    get_parts_by_batch(11)

    s3_client.complete_multipart_upload(
        Bucket=bucket_name,
        Key="the-key",
        UploadId=mpu_id,
        MultipartUpload={"Parts": parts},
    )


@mock_aws
@reduced_min_part_size
def test_multipart_part_size():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")

    mpu = s3_client.create_multipart_upload(Bucket="mybucket", Key="the-key")
    mpu_id = mpu["UploadId"]

    parts = []
    n_parts = 10
    for i in range(1, n_parts + 1):
        part_size = REDUCED_PART_SIZE + i
        body = b"1" * part_size
        part = s3_client.upload_part(
            Bucket="mybucket",
            Key="the-key",
            PartNumber=i,
            UploadId=mpu_id,
            Body=body,
            ContentLength=len(body),
        )
        parts.append({"PartNumber": i, "ETag": part["ETag"]})

    s3_client.complete_multipart_upload(
        Bucket="mybucket",
        Key="the-key",
        UploadId=mpu_id,
        MultipartUpload={"Parts": parts},
    )

    for i in range(1, n_parts + 1):
        obj = s3_client.head_object(Bucket="mybucket", Key="the-key", PartNumber=i)
        assert obj["ContentLength"] == REDUCED_PART_SIZE + i


@mock_aws
def test_complete_multipart_with_empty_partlist():
    """Verify InvalidXML-error sent for MultipartUpload with empty part list."""
    bucket = "testbucketthatcompletesmultipartuploadwithoutparts"
    key = "test-multi-empty"

    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket=bucket)

    response = client.create_multipart_upload(Bucket=bucket, Key=key)
    uid = response["UploadId"]

    upload = boto3.resource("s3").MultipartUpload(bucket, key, uid)

    with pytest.raises(ClientError) as exc:
        upload.complete(MultipartUpload={"Parts": []})
    err = exc.value.response["Error"]
    assert err["Code"] == "MalformedXML"
    assert err["Message"] == (
        "The XML you provided was not well-formed or did not validate "
        "against our published schema"
    )


@mock_aws
def test_ssm_key_headers_in_create_multipart():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    bucket_name = "ssm-headers-bucket"
    s3_client.create_bucket(Bucket=bucket_name)

    kms_key_id = "random-id"
    key_name = "test-file.txt"

    create_multipart_response = s3_client.create_multipart_upload(
        Bucket=bucket_name,
        Key=key_name,
        ServerSideEncryption="aws:kms",
        SSEKMSKeyId=kms_key_id,
    )
    assert create_multipart_response["ServerSideEncryption"] == "aws:kms"
    assert create_multipart_response["SSEKMSKeyId"] == kms_key_id

    upload_part_response = s3_client.upload_part(
        Body=b"bytes",
        Bucket=bucket_name,
        Key=key_name,
        PartNumber=1,
        UploadId=create_multipart_response["UploadId"],
    )
    assert upload_part_response["ServerSideEncryption"] == "aws:kms"
    assert upload_part_response["SSEKMSKeyId"] == kms_key_id

    parts = {"Parts": [{"PartNumber": 1, "ETag": upload_part_response["ETag"]}]}
    complete_multipart_response = s3_client.complete_multipart_upload(
        Bucket=bucket_name,
        Key=key_name,
        UploadId=create_multipart_response["UploadId"],
        MultipartUpload=parts,
    )
    assert complete_multipart_response["ServerSideEncryption"] == "aws:kms"
    assert complete_multipart_response["SSEKMSKeyId"] == kms_key_id


@mock_aws
@reduced_min_part_size
def test_generate_presigned_url_on_multipart_upload_without_acl():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    bucket_name = "testing"
    client.create_bucket(Bucket=bucket_name)

    object_key = "test_multipart_object"
    multipart_response = client.create_multipart_upload(
        Bucket=bucket_name, Key=object_key
    )
    upload_id = multipart_response["UploadId"]

    parts = []
    n_parts = 10
    for i in range(1, n_parts + 1):
        part_size = REDUCED_PART_SIZE + i
        body = b"1" * part_size
        part = client.upload_part(
            Bucket=bucket_name,
            Key=object_key,
            PartNumber=i,
            UploadId=upload_id,
            Body=body,
            ContentLength=len(body),
        )
        parts.append({"PartNumber": i, "ETag": part["ETag"]})

    client.complete_multipart_upload(
        Bucket=bucket_name,
        Key=object_key,
        UploadId=upload_id,
        MultipartUpload={"Parts": parts},
    )

    url = client.generate_presigned_url(
        "head_object", Params={"Bucket": bucket_name, "Key": object_key}
    )
    kwargs = {}
    if is_test_proxy_mode():
        add_proxy_details(kwargs)
    res = requests.get(url, **kwargs)
    assert res.status_code == 200


@mock_aws
@reduced_min_part_size
def test_head_object_returns_part_count():
    bucket = "telstra-energy-test"
    key = "test-single-multi-part"

    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket=bucket)

    mp_id = client.create_multipart_upload(Bucket=bucket, Key=key)["UploadId"]

    num_parts = 2
    parts = []

    for part in range(1, num_parts + 1):
        response = client.upload_part(
            Body=b"x" * (REDUCED_PART_SIZE + part),
            Bucket=bucket,
            Key=key,
            PartNumber=part,
            UploadId=mp_id,
        )

        parts.append({"ETag": response["ETag"], "PartNumber": part})

    client.complete_multipart_upload(
        Bucket=bucket,
        Key=key,
        MultipartUpload={"Parts": parts},
        UploadId=mp_id,
    )

    resp = client.head_object(Bucket=bucket, Key=key, PartNumber=1)
    assert resp["PartsCount"] == num_parts

    # Header is not returned when we do not pass PartNumber
    resp = client.head_object(Bucket=bucket, Key=key)
    assert "PartsCount" not in resp


@mock_aws
@reduced_min_part_size
def test_generate_presigned_url_for_multipart_upload():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point in testing this outside decorator mode")
    bucket_name = "mock-bucket"
    file_name = "mock-file"
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket=bucket_name)

    mpu = s3_client.create_multipart_upload(
        Bucket=bucket_name,
        Key=file_name,
    )
    upload_id = mpu["UploadId"]

    url = s3_client.generate_presigned_url(
        "upload_part",
        Params={
            "Bucket": bucket_name,
            "Key": file_name,
            "PartNumber": 1,
            "UploadId": upload_id,
        },
    )
    data = b"0" * REDUCED_PART_SIZE

    resp = requests.put(url, data=data)
    assert resp.status_code == 200
