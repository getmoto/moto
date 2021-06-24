from botocore.exceptions import ClientError
from moto import mock_s3
import boto3
import pytest
import sure  # noqa


@mock_s3
def test_multipart_should_throw_nosuchupload_if_there_are_no_parts():
    bucket = boto3.resource("s3").Bucket("randombucketname")
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
