import gzip
from collections.abc import Iterable
from unittest.mock import Mock, patch

import boto3
import pytest

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
