"""Test different server responses."""
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
    assert resp.status_code == 200
    assert isinstance(data["JobId"], str)


@mock_textract
def test_textract_start_text_detection_without_document_location():
    backend = server.create_backend_app("textract")
    test_client = backend.test_client()

    headers = {"X-Amz-Target": "X-Amz-Target=Textract.StartDocumentTextDetection"}
    resp = test_client.post("/", headers=headers, json={})
    data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 400
    assert data["__type"] == "InvalidParameterException"
    assert (
        data["message"]
        == "An input parameter violated a constraint. For example, in synchronous operations, an InvalidParameterException exception occurs when neither of the S3Object or Bytes values are supplied in the Document request parameter. Validate your parameter before calling the API operation again."
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
    assert resp.status_code == 200
    data = json.loads(resp.data.decode("utf-8"))
    assert data["JobStatus"] == "SUCCEEDED"


@mock_textract
def test_textract_get_text_detection_without_job_id():
    backend = server.create_backend_app("textract")
    test_client = backend.test_client()

    headers = {"X-Amz-Target": "X-Amz-Target=Textract.GetDocumentTextDetection"}
    request_body = {
        "JobId": "invalid_job_id",
    }
    resp = test_client.post("/", headers=headers, json=request_body)
    assert resp.status_code == 400
    data = json.loads(resp.data.decode("utf-8"))
    assert data["__type"] == "InvalidJobIdException"
    assert data["message"] == "An invalid job identifier was passed."
