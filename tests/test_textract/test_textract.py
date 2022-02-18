"""Unit tests for textract-supported APIs."""
import boto3

from moto import mock_textract

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html



# @mock_textract
# def test_get_document_text_detection():
#     client = boto3.client("textract", region_name="us-east-1")
#     resp = client.get_document_text_detection()

#     raise Exception("NotYetImplemented")


@mock_textract
def test_start_document_text_detection():
    client = boto3.client("textract", region_name="us-east-1")
    resp = client.start_document_text_detection(
        DocumentLocation={
            'S3Object': {
                'Bucket': 'bucket',
                'Name': 'name',
            }
        },
    )

    resp.should.have.key("JobId")
