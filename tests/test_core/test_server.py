from typing import Iterable
from unittest.mock import Mock, patch

import boto3
import pytest

from moto.server import ThreadedMotoServer, main


def test_wrong_arguments() -> None:
    try:
        main(["test1", "test2", "test3"])
        assert False, (
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


def test_s3_using_moto_fixture(moto_server: str) -> None:  # pylint: disable=redefined-outer-name
    client = boto3.client("s3", endpoint_url=moto_server)
    client.list_buckets()
