from botocore.exceptions import ClientError
from moto import mock_s3
import boto3
import os
import pytest
import sure  # pylint: disable=unused-import

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
