"""Unit tests for textract-supported APIs."""
from random import randint
from botocore.exceptions import ClientError, ParamValidationError
import pytest
import boto3

from unittest import SkipTest
from moto.textract.models import TextractBackend
from moto import settings, mock_textract

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_textract
def test_get_document_text_detection():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cannot set textract backend values in server mode")

    TextractBackend.JOB_STATUS = "SUCCEEDED"
    TextractBackend.PAGES = randint(5, 500)
    TextractBackend.BLOCKS = [
        {
            "Text": "This is a test",
            "Id": "0",
            "Confidence": "100",
            "Geometry": {
                "BoundingBox": {
                    "Width": "0.5",
                    "Height": "0.5",
                    "Left": "0.5",
                    "Top": "0.5",
                },
            },
        }
    ]

    client = boto3.client("textract", region_name="us-east-1")
    job = client.start_document_text_detection(
        DocumentLocation={"S3Object": {"Bucket": "bucket", "Name": "name"}}
    )

    resp = client.get_document_text_detection(JobId=job["JobId"])

    assert resp["Blocks"][0]["Text"] == "This is a test"
    assert resp["Blocks"][0]["Id"] == "0"
    assert resp["Blocks"][0]["Confidence"] == "100"
    assert resp["Blocks"][0]["Geometry"]["BoundingBox"]["Width"] == "0.5"
    assert resp["Blocks"][0]["Geometry"]["BoundingBox"]["Height"] == "0.5"
    assert resp["Blocks"][0]["Geometry"]["BoundingBox"]["Left"] == "0.5"
    assert resp["Blocks"][0]["Geometry"]["BoundingBox"]["Top"] == "0.5"
    assert resp["JobStatus"] == "SUCCEEDED"
    assert resp["DocumentMetadata"]["Pages"] == TextractBackend.PAGES


@mock_textract
def test_start_document_text_detection():
    client = boto3.client("textract", region_name="us-east-1")
    resp = client.start_document_text_detection(
        DocumentLocation={"S3Object": {"Bucket": "bucket", "Name": "name"}}
    )

    assert "JobId" in resp


@mock_textract
def test_get_document_text_detection_without_job_id():
    client = boto3.client("textract", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.get_document_text_detection(JobId="Invalid Job Id")

    assert e.value.response["Error"]["Code"] == "InvalidJobIdException"


@mock_textract
def test_get_document_text_detection_without_document_location():
    client = boto3.client("textract", region_name="us-east-1")
    with pytest.raises(ParamValidationError) as e:
        client.start_document_text_detection()

    assert e.typename == "ParamValidationError"
    assert (
        'Parameter validation failed:\nMissing required parameter in input: "DocumentLocation"'
        in e.value.args
    )
