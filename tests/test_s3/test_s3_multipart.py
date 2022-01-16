from botocore.exceptions import ClientError
from moto import mock_s3
import boto3
import os
import pytest
import sure  # noqa # pylint: disable=unused-import

from .test_s3 import DEFAULT_REGION_NAME


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
def test_boto3_multipart_part_size():
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
            "ETag": u.Part(i).upload(Body=os.urandom(5 * (2 ** 20)))["ETag"],
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
