"""Unit tests for rekognition-supported APIs."""
import random
import string

import boto3

import sure  # noqa # pylint: disable=unused-import
from moto import mock_rekognition

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_rekognition
def test_start_text_detection():
    client = boto3.client("rekognition", region_name="ap-southeast-1")
    video = {
        "S3Object": {
            "Bucket": "bucket",
            "Name": "key",
        }
    }

    resp = client.start_text_detection(Video=video)

    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    resp.should.have.key("JobId")


@mock_rekognition
def test_get_text_detection():
    client = boto3.client("rekognition", region_name="us-east-2")
    job_id = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(64)
    )

    resp = client.get_text_detection(JobId=job_id)

    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    resp["JobStatus"].should.equal("SUCCEEDED")
    resp["TextDetections"][0]["TextDetection"]["DetectedText"].should.equal(
        "Hello world"
    )
