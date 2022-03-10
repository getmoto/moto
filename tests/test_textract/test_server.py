"""Test different server responses."""
import sure  # noqa # pylint: disable=unused-import

import json
import moto.server as server
from moto import mock_textract


@mock_textract
def test_textract_start_text_detection():
    backend = server.create_backend_app("textract")
    test_client = backend.test_client()

    headers = {"X-Amz-Target": "X-Amz-Target=Textract.StartDocumentTextDetection"}
    request_body = {
        "DocumentLocation": {
            "S3Object": {"Bucket": "bucket", "Name": "name", "Version": "version"}
        }
    }

    resp = test_client.post("/", headers=headers, json=request_body)
    data = json.loads(resp.data.decode("utf-8"))
    resp.status_code.should.equal(200)
    data["JobId"].should.be.an(str)


@mock_textract
def test_textract_start_text_detection_without_document_location():
    backend = server.create_backend_app("textract")
    test_client = backend.test_client()

    headers = {"X-Amz-Target": "X-Amz-Target=Textract.StartDocumentTextDetection"}
    resp = test_client.post("/", headers=headers, json={})
    data = json.loads(resp.data.decode("utf-8"))
    resp.status_code.should.equal(400)
    data["__type"].should.equal("InvalidParameterException")
    data["message"].should.equal(
        "An input parameter violated a constraint. For example, in synchronous operations, an InvalidParameterException exception occurs when neither of the S3Object or Bytes values are supplied in the Document request parameter. Validate your parameter before calling the API operation again."
    )


@mock_textract
def test_textract_get_text_detection():
    backend = server.create_backend_app("textract")
    test_client = backend.test_client()

    headers = {"X-Amz-Target": "X-Amz-Target=Textract.StartDocumentTextDetection"}
    request_body = {
        "DocumentLocation": {
            "S3Object": {"Bucket": "bucket", "Name": "name", "Version": "version"}
        }
    }

    resp = test_client.post("/", headers=headers, json=request_body)
    start_job_data = json.loads(resp.data.decode("utf-8"))

    headers = {"X-Amz-Target": "X-Amz-Target=Textract.GetDocumentTextDetection"}
    request_body = {
        "JobId": start_job_data["JobId"],
    }
    resp = test_client.post("/", headers=headers, json=request_body)
    resp.status_code.should.equal(200)
    data = json.loads(resp.data.decode("utf-8"))
    data["JobStatus"].should.equal("SUCCEEDED")


@mock_textract
def test_textract_get_text_detection_without_job_id():
    backend = server.create_backend_app("textract")
    test_client = backend.test_client()

    headers = {"X-Amz-Target": "X-Amz-Target=Textract.GetDocumentTextDetection"}
    request_body = {
        "JobId": "invalid_job_id",
    }
    resp = test_client.post("/", headers=headers, json=request_body)
    resp.status_code.should.equal(400)
    data = json.loads(resp.data.decode("utf-8"))
    data["__type"].should.equal("InvalidJobIdException")
    data["message"].should.equal("An invalid job identifier was passed.")
