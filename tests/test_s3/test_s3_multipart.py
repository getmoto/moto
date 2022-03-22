import boto3
import os
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.client import ClientError
from functools import wraps
from io import BytesIO

from moto.s3.responses import DEFAULT_REGION_NAME


from moto import settings, mock_s3
import moto.s3.models as s3model
from moto.settings import get_s3_default_key_buffer_size, S3_UPLOAD_PART_MIN_SIZE

if settings.TEST_SERVER_MODE:
    REDUCED_PART_SIZE = S3_UPLOAD_PART_MIN_SIZE
    EXPECTED_ETAG = '"140f92a6df9f9e415f74a1463bcee9bb-2"'
else:
    REDUCED_PART_SIZE = 256
    EXPECTED_ETAG = '"66d1a1a2ed08fd05c137f316af4ff255-2"'


def reduced_min_part_size(f):
    """speed up tests by temporarily making the multipart minimum part size
    small
    """
    orig_size = S3_UPLOAD_PART_MIN_SIZE

    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            s3model.S3_UPLOAD_PART_MIN_SIZE = REDUCED_PART_SIZE
            return f(*args, **kwargs)
        finally:
            s3model.S3_UPLOAD_PART_MIN_SIZE = orig_size

    return wrapped


@mock_s3
def test_default_key_buffer_size():
    # save original DEFAULT_KEY_BUFFER_SIZE environment variable content
    original_default_key_buffer_size = os.environ.get(
        "MOTO_S3_DEFAULT_KEY_BUFFER_SIZE", None
    )

    os.environ["MOTO_S3_DEFAULT_KEY_BUFFER_SIZE"] = "2"  # 2 bytes
    assert get_s3_default_key_buffer_size() == 2
    fk = s3model.FakeKey("a", os.urandom(1))  # 1 byte string
    assert fk._value_buffer._rolled is False

    os.environ["MOTO_S3_DEFAULT_KEY_BUFFER_SIZE"] = "1"  # 1 byte
    assert get_s3_default_key_buffer_size() == 1
    fk = s3model.FakeKey("a", os.urandom(3))  # 3 byte string
    assert fk._value_buffer._rolled is True

    # if no MOTO_S3_DEFAULT_KEY_BUFFER_SIZE env variable is present the buffer size should be less than
    # S3_UPLOAD_PART_MIN_SIZE to prevent in memory caching of multi part uploads
    del os.environ["MOTO_S3_DEFAULT_KEY_BUFFER_SIZE"]
    assert get_s3_default_key_buffer_size() < S3_UPLOAD_PART_MIN_SIZE

    # restore original environment variable content
    if original_default_key_buffer_size:
        os.environ["MOTO_S3_DEFAULT_KEY_BUFFER_SIZE"] = original_default_key_buffer_size


@mock_s3
def test_multipart_upload_too_small():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    mp = client.create_multipart_upload(Bucket="foobar", Key="the-key")
    up1 = client.upload_part(
        Body=BytesIO(b"hello"),
        PartNumber=1,
        Bucket="foobar",
        Key="the-key",
        UploadId=mp["UploadId"],
    )
    up2 = client.upload_part(
        Body=BytesIO(b"world"),
        PartNumber=2,
        Bucket="foobar",
        Key="the-key",
        UploadId=mp["UploadId"],
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
            UploadId=mp["UploadId"],
        )
    ex.value.response["Error"]["Code"].should.equal("EntityTooSmall")
    ex.value.response["Error"]["Message"].should.equal(
        "Your proposed upload is smaller than the minimum allowed object size."
    )


@mock_s3
@reduced_min_part_size
def test_multipart_upload():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    part1 = b"0" * REDUCED_PART_SIZE
    part2 = b"1"
    mp = client.create_multipart_upload(Bucket="foobar", Key="the-key")
    up1 = client.upload_part(
        Body=BytesIO(part1),
        PartNumber=1,
        Bucket="foobar",
        Key="the-key",
        UploadId=mp["UploadId"],
    )
    up2 = client.upload_part(
        Body=BytesIO(part2),
        PartNumber=2,
        Bucket="foobar",
        Key="the-key",
        UploadId=mp["UploadId"],
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
        UploadId=mp["UploadId"],
    )
    # we should get both parts as the key contents
    response = client.get_object(Bucket="foobar", Key="the-key")
    response["Body"].read().should.equal(part1 + part2)


@mock_s3
@reduced_min_part_size
def test_multipart_upload_out_of_order():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    part1 = b"0" * REDUCED_PART_SIZE
    part2 = b"1"
    mp = client.create_multipart_upload(Bucket="foobar", Key="the-key")
    up1 = client.upload_part(
        Body=BytesIO(part1),
        PartNumber=4,
        Bucket="foobar",
        Key="the-key",
        UploadId=mp["UploadId"],
    )
    up2 = client.upload_part(
        Body=BytesIO(part2),
        PartNumber=2,
        Bucket="foobar",
        Key="the-key",
        UploadId=mp["UploadId"],
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
        UploadId=mp["UploadId"],
    )
    # we should get both parts as the key contents
    response = client.get_object(Bucket="foobar", Key="the-key")
    response["Body"].read().should.equal(part1 + part2)


@mock_s3
@reduced_min_part_size
def test_multipart_upload_with_headers():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    part1 = b"0" * REDUCED_PART_SIZE
    mp = client.create_multipart_upload(
        Bucket="foobar", Key="the-key", Metadata={"meta": "data"}
    )
    up1 = client.upload_part(
        Body=BytesIO(part1),
        PartNumber=1,
        Bucket="foobar",
        Key="the-key",
        UploadId=mp["UploadId"],
    )

    client.complete_multipart_upload(
        Bucket="foobar",
        Key="the-key",
        MultipartUpload={"Parts": [{"ETag": up1["ETag"], "PartNumber": 1}]},
        UploadId=mp["UploadId"],
    )
    # we should get both parts as the key contents
    response = client.get_object(Bucket="foobar", Key="the-key")
    response["Metadata"].should.equal({"meta": "data"})


@pytest.mark.parametrize(
    "original_key_name",
    [
        "original-key",
        "the-unicode-💩-key",
        "key-with?question-mark",
        "key-with%2Fembedded%2Furl%2Fencoding",
    ],
)
@mock_s3
@reduced_min_part_size
def test_multipart_upload_with_copy_key(original_key_name):
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")
    s3.put_object(Bucket="foobar", Key=original_key_name, Body="key_value")

    mpu = s3.create_multipart_upload(Bucket="foobar", Key="the-key")
    part1 = b"0" * REDUCED_PART_SIZE
    up1 = s3.upload_part(
        Bucket="foobar",
        Key="the-key",
        PartNumber=1,
        UploadId=mpu["UploadId"],
        Body=BytesIO(part1),
    )
    up2 = s3.upload_part_copy(
        Bucket="foobar",
        Key="the-key",
        CopySource={"Bucket": "foobar", "Key": original_key_name},
        CopySourceRange="0-3",
        PartNumber=2,
        UploadId=mpu["UploadId"],
    )
    s3.complete_multipart_upload(
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
    response = s3.get_object(Bucket="foobar", Key="the-key")
    response["Body"].read().should.equal(part1 + b"key_")


@mock_s3
@reduced_min_part_size
def test_multipart_upload_cancel():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    mpu = s3.create_multipart_upload(Bucket="foobar", Key="the-key")
    part1 = b"0" * REDUCED_PART_SIZE
    s3.upload_part(
        Bucket="foobar",
        Key="the-key",
        PartNumber=1,
        UploadId=mpu["UploadId"],
        Body=BytesIO(part1),
    )

    uploads = s3.list_multipart_uploads(Bucket="foobar")["Uploads"]
    uploads.should.have.length_of(1)
    uploads[0]["Key"].should.equal("the-key")

    s3.abort_multipart_upload(Bucket="foobar", Key="the-key", UploadId=mpu["UploadId"])

    s3.list_multipart_uploads(Bucket="foobar").shouldnt.have.key("Uploads")


@mock_s3
@reduced_min_part_size
def test_multipart_etag_quotes_stripped():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")
    s3.put_object(Bucket="foobar", Key="original-key", Body="key_value")

    mpu = s3.create_multipart_upload(Bucket="foobar", Key="the-key")
    part1 = b"0" * REDUCED_PART_SIZE
    up1 = s3.upload_part(
        Bucket="foobar",
        Key="the-key",
        PartNumber=1,
        UploadId=mpu["UploadId"],
        Body=BytesIO(part1),
    )
    etag1 = up1["ETag"].replace('"', "")
    up2 = s3.upload_part_copy(
        Bucket="foobar",
        Key="the-key",
        CopySource={"Bucket": "foobar", "Key": "original-key"},
        CopySourceRange="0-3",
        PartNumber=2,
        UploadId=mpu["UploadId"],
    )
    etag2 = up2["CopyPartResult"]["ETag"].replace('"', "")
    s3.complete_multipart_upload(
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
    response = s3.get_object(Bucket="foobar", Key="the-key")
    response["Body"].read().should.equal(part1 + b"key_")


@mock_s3
@reduced_min_part_size
def test_multipart_duplicate_upload():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    part1 = b"0" * REDUCED_PART_SIZE
    part2 = b"1"
    mp = client.create_multipart_upload(Bucket="foobar", Key="the-key")
    client.upload_part(
        Body=BytesIO(part1),
        PartNumber=1,
        Bucket="foobar",
        Key="the-key",
        UploadId=mp["UploadId"],
    )
    # same part again
    up1 = client.upload_part(
        Body=BytesIO(part1),
        PartNumber=1,
        Bucket="foobar",
        Key="the-key",
        UploadId=mp["UploadId"],
    )
    up2 = client.upload_part(
        Body=BytesIO(part2),
        PartNumber=2,
        Bucket="foobar",
        Key="the-key",
        UploadId=mp["UploadId"],
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
        UploadId=mp["UploadId"],
    )
    # we should get both parts as the key contents
    response = client.get_object(Bucket="foobar", Key="the-key")
    response["Body"].read().should.equal(part1 + part2)


@mock_s3
def test_list_multiparts():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="foobar")

    mpu1 = s3.create_multipart_upload(Bucket="foobar", Key="one-key")
    mpu2 = s3.create_multipart_upload(Bucket="foobar", Key="two-key")

    uploads = s3.list_multipart_uploads(Bucket="foobar")["Uploads"]
    uploads.should.have.length_of(2)
    {u["Key"]: u["UploadId"] for u in uploads}.should.equal(
        {"one-key": mpu1["UploadId"], "two-key": mpu2["UploadId"]}
    )

    s3.abort_multipart_upload(Bucket="foobar", Key="the-key", UploadId=mpu2["UploadId"])

    uploads = s3.list_multipart_uploads(Bucket="foobar")["Uploads"]
    uploads.should.have.length_of(1)
    uploads[0]["Key"].should.equal("one-key")

    s3.abort_multipart_upload(Bucket="foobar", Key="the-key", UploadId=mpu1["UploadId"])

    res = s3.list_multipart_uploads(Bucket="foobar")
    res.shouldnt.have.key("Uploads")


@mock_s3
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
    err["Code"].should.equal("NoSuchUpload")
    err["Message"].should.equal(
        "The specified upload does not exist. The upload ID may be invalid, or the upload may have been aborted or completed."
    )
    err["UploadId"].should.equal(multipart_upload.id)


@mock_s3
def test_multipart_wrong_partnumber():
    bucket_name = "mputest-3593"
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket=bucket_name)

    mpu = s3.create_multipart_upload(Bucket=bucket_name, Key="the-key")
    mpu_id = mpu["UploadId"]

    body = b"111"
    with pytest.raises(ClientError) as ex:
        s3.upload_part(
            Bucket=bucket_name,
            Key="the-key",
            PartNumber=-1,
            UploadId=mpu_id,
            Body=body,
            ContentLength=len(body),
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("NoSuchUpload")
    err["Message"].should.equal(
        "The specified upload does not exist. The upload ID may be invalid, or the upload may have been aborted or completed."
    )


@mock_s3
def test_multipart_upload_with_tags():
    bucket = "mybucket"
    key = "test/multipartuploadtag/file.txt"
    tags = "a=b"

    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket=bucket)

    response = client.create_multipart_upload(Bucket=bucket, Key=key, Tagging=tags)
    u = boto3.resource("s3").MultipartUpload(bucket, key, response["UploadId"])
    parts = [
        {
            "ETag": u.Part(i).upload(Body=os.urandom(5 * (2**20)))["ETag"],
            "PartNumber": i,
        }
        for i in range(1, 3)
    ]

    u.complete(MultipartUpload={"Parts": parts})

    # check tags
    response = client.get_object_tagging(Bucket=bucket, Key=key)
    actual = {t["Key"]: t["Value"] for t in response.get("TagSet", [])}
    actual.should.equal({"a": "b"})


@mock_s3
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
    part_nrs.should.equal([1, 2, 10000])


@mock_s3
def test_multipart_upload_without_parts():
    bucket = "dummybucket"
    s3_client = boto3.client("s3", "us-east-1")

    key = "test_file"
    s3_client.create_bucket(Bucket=bucket)

    mpu = s3_client.create_multipart_upload(Bucket=bucket, Key=key)
    mpu_id = mpu["UploadId"]

    list_parts_result = s3_client.list_parts(Bucket=bucket, Key=key, UploadId=mpu_id)
    list_parts_result["IsTruncated"].should.equal(False)


@mock_s3
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
    err["Code"].should.equal("InvalidArgument")
    err["Message"].should.equal(
        "Part number must be an integer between 1 and 10000, inclusive"
    )
    err["ArgumentName"].should.equal("partNumber")
    err["ArgumentValue"].should.equal(f"{part_nr}")


@mock_s3
def test_s3_abort_multipart_data_with_invalid_upload_and_key():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    client.create_bucket(Bucket="blah")

    with pytest.raises(Exception) as err:
        client.abort_multipart_upload(
            Bucket="blah", Key="foobar", UploadId="dummy_upload_id"
        )
    err = err.value.response["Error"]
    err["Code"].should.equal("NoSuchUpload")
    err["Message"].should.equal(
        "The specified upload does not exist. The upload ID may be invalid, or the upload may have been aborted or completed."
    )
    err["UploadId"].should.equal("dummy_upload_id")


@mock_s3
@reduced_min_part_size
def test_multipart_etag():
    # Create Bucket so that test can run
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")

    upload_id = s3.create_multipart_upload(Bucket="mybucket", Key="the-key")["UploadId"]
    part1 = b"0" * REDUCED_PART_SIZE
    etags = []
    etags.append(
        s3.upload_part(
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
        s3.upload_part(
            Bucket="mybucket",
            Key="the-key",
            PartNumber=2,
            UploadId=upload_id,
            Body=part2,
        )["ETag"]
    )

    s3.complete_multipart_upload(
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
    resp = s3.get_object(Bucket="mybucket", Key="the-key")
    resp["ETag"].should.equal(EXPECTED_ETAG)


@mock_s3
@reduced_min_part_size
def test_multipart_version():
    # Create Bucket so that test can run
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")

    s3.put_bucket_versioning(
        Bucket="mybucket", VersioningConfiguration={"Status": "Enabled"}
    )

    upload_id = s3.create_multipart_upload(Bucket="mybucket", Key="the-key")["UploadId"]
    part1 = b"0" * REDUCED_PART_SIZE
    etags = []
    etags.append(
        s3.upload_part(
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
        s3.upload_part(
            Bucket="mybucket",
            Key="the-key",
            PartNumber=2,
            UploadId=upload_id,
            Body=part2,
        )["ETag"]
    )
    response = s3.complete_multipart_upload(
        Bucket="mybucket",
        Key="the-key",
        UploadId=upload_id,
        MultipartUpload={
            "Parts": [
                {"ETag": etag, "PartNumber": i} for i, etag in enumerate(etags, 1)
            ]
        },
    )

    response["VersionId"].should.should_not.be.none


@mock_s3
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
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "mybucketasdfljoqwerasdfas"
    s3.create_bucket(Bucket=bucket_name)

    mpu = s3.create_multipart_upload(Bucket=bucket_name, Key="the-key")
    mpu_id = mpu["UploadId"]

    def get_parts(**kwarg):
        s3.list_parts(Bucket=bucket_name, Key="the-key", UploadId=mpu_id, **kwarg)

    with pytest.raises(ClientError) as err:
        get_parts(**{"MaxParts": part_nr})
    e = err.value.response["Error"]
    e["Code"].should.equal("InvalidArgument")
    e["Message"].should.equal(msg)

    with pytest.raises(ClientError) as err:
        get_parts(**{"PartNumberMarker": part_nr})
    e = err.value.response["Error"]
    e["Code"].should.equal("InvalidArgument")
    e["Message"].should.equal(msg2)


@mock_s3
@reduced_min_part_size
def test_multipart_list_parts():
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "mybucketasdfljoqwerasdfas"
    s3.create_bucket(Bucket=bucket_name)

    mpu = s3.create_multipart_upload(Bucket=bucket_name, Key="the-key")
    mpu_id = mpu["UploadId"]

    parts = []
    n_parts = 10

    def get_parts_all(i):
        # Get uploaded parts using default values
        uploaded_parts = []

        uploaded = s3.list_parts(Bucket=bucket_name, Key="the-key", UploadId=mpu_id)

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
            uploaded = s3.list_parts(
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
        part = s3.upload_part(
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

    s3.complete_multipart_upload(
        Bucket=bucket_name,
        Key="the-key",
        UploadId=mpu_id,
        MultipartUpload={"Parts": parts},
    )


@mock_s3
@reduced_min_part_size
def test_multipart_part_size():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")

    mpu = s3.create_multipart_upload(Bucket="mybucket", Key="the-key")
    mpu_id = mpu["UploadId"]

    parts = []
    n_parts = 10
    for i in range(1, n_parts + 1):
        part_size = REDUCED_PART_SIZE + i
        body = b"1" * part_size
        part = s3.upload_part(
            Bucket="mybucket",
            Key="the-key",
            PartNumber=i,
            UploadId=mpu_id,
            Body=body,
            ContentLength=len(body),
        )
        parts.append({"PartNumber": i, "ETag": part["ETag"]})

    s3.complete_multipart_upload(
        Bucket="mybucket",
        Key="the-key",
        UploadId=mpu_id,
        MultipartUpload={"Parts": parts},
    )

    for i in range(1, n_parts + 1):
        obj = s3.head_object(Bucket="mybucket", Key="the-key", PartNumber=i)
        assert obj["ContentLength"] == REDUCED_PART_SIZE + i


@mock_s3
def test_complete_multipart_with_empty_partlist():
    """
    When completing a MultipartUpload with an empty part list, AWS responds with an InvalidXML-error

    Verify that we send the same error, to duplicate boto3's behaviour
    """
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
    err["Code"].should.equal("MalformedXML")
    err["Message"].should.equal(
        "The XML you provided was not well-formed or did not validate against our published schema"
    )
