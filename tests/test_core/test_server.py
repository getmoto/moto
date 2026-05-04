import gzip
import json
from collections.abc import Iterable
from unittest.mock import Mock, patch

import boto3
import pytest
import requests

from moto import server
from moto.server import ThreadedMotoServer, main


def test_wrong_arguments() -> None:
    try:
        main(["test1", "test2", "test3"])
        raise AssertionError(
            "main() when called with the incorrect number of args"
            " should raise a system exit"
        )
    except SystemExit:
        pass


@patch("moto.server.run_simple")
def test_right_arguments(run_simple: Mock) -> None:  # type: ignore[misc]
    main(["-r"])
    func_call = run_simple.call_args[0]
    assert func_call[0] == "127.0.0.1"
    assert func_call[1] == 5000


@patch("moto.server.run_simple")
def test_port_argument(run_simple: Mock) -> None:  # type: ignore[misc]
    main(["--port", "8080"])
    func_call = run_simple.call_args[0]
    assert func_call[0] == "127.0.0.1"
    assert func_call[1] == 8080


@pytest.fixture(scope="module")
def moto_server() -> Iterable[str]:
    """Fixture to run a mocked AWS server for testing."""
    # Note: pass `port=0` to get a random free port.
    server = ThreadedMotoServer(port=0)
    server.start()
    host, port = server.get_host_and_port()
    yield f"http://{host}:{port}"
    server.stop()


def test_s3_using_moto_fixture(moto_server: str) -> None:
    client = boto3.client("s3", endpoint_url=moto_server)
    client.list_buckets()


def test_request_decompression() -> None:
    backend = server.create_backend_app("rds")
    test_client = backend.test_client()
    headers = {
        "Content-Encoding": "gzip",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "rds.us-east-1.amazonaws.com",
    }
    data = gzip.compress(b"Action=DescribeDBInstances")
    resp = test_client.post(headers=headers, data=data)
    assert resp.status_code == 200
    assert "<DescribeDBInstancesResult>" in resp.data.decode("utf-8")


def test_date_header_is_not_duplicated(moto_server: str) -> None:
    client = boto3.client("glue", region_name="us-east-1", endpoint_url=moto_server)
    resp = client.get_connections()
    date_header_value = resp["ResponseMetadata"]["HTTPHeaders"]["date"]
    # RFC 2822 dates should only have 1 comma, e.g. 'Mon, 20 Nov 1995 19:12:08 GMT'
    # If multiple date headers exist, their values will be concatenated with a comma
    # and this assertion will fail.
    assert len(date_header_value.split(",")) == 2


def test_s3_create_multipart_upload_with_json_content_type(moto_server: str) -> None:
    # Regression test for https://github.com/getmoto/moto/issues/10010
    # aiobotocore sends Content-Type: application/json for CreateMultipartUpload;
    # moto should fall back to rest-xml (S3's default) instead of raising 500.
    client = boto3.client(
        "s3",
        region_name="us-east-1",
        endpoint_url=moto_server,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    client.create_bucket(Bucket="testbucket")

    resp = requests.post(
        f"{moto_server}/testbucket/testkey?uploads",
        headers={
            "Content-Type": "application/json",
            "Authorization": "AWS4-HMAC-SHA256 Credential=test/20260101/us-east-1/s3/aws4_request, SignedHeaders=host;x-amz-date, Signature=test",
            "x-amz-date": "20260101T000000Z",
            "Host": "testbucket.s3.amazonaws.com",
        },
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert "<CreateMultipartUploadResponse" in resp.text


def test_bedrock_service_resolution(moto_server: str) -> None:
    # Multiple Bedrock services use the same signing name (bedrock),
    # so this test checks that a bedrock-runtime request is correctly
    # differentiated in server mode (where there is no host name available).
    from botocore.exceptions import UnknownServiceError

    try:
        client = boto3.client(
            "bedrock-runtime", region_name="us-east-1", endpoint_url=moto_server
        )
    except UnknownServiceError:
        pytest.skip("Bedrock Runtime not supported in this version of Botocore.")
    else:
        resp = client.invoke_model(
            modelId="test-model-id",
            body=json.dumps({}),
            performanceConfigLatency="optimized",
            serviceTier="flex",
        )
        assert resp["performanceConfigLatency"] == "optimized"
        assert resp["serviceTier"] == "flex"
