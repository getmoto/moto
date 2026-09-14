import json
from http.server import BaseHTTPRequestHandler
from unittest import SkipTest

import pytest

from moto import mock_aws, settings
from tests.test_core.utilities import SimpleServer

from . import verify_execution_result


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_state_machine_calling_apigateway_invoke():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point in testing this in ServerMode")

    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            received.append(
                {
                    "path": self.path,
                    "body": body.decode(),
                    "x_custom": self.headers.get("X-Custom"),
                }
            )
            payload = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = SimpleServer(Handler)
    server.start()
    _, port = server.get_host_and_port()

    try:
        exec_input = {
            "ApiEndpoint": f"http://127.0.0.1:{port}",
            "RequestBody": {"hello": "world"},
        }

        def _verify_result(client, execution, execution_arn):
            output = json.loads(execution["output"])
            assert output["StatusCode"] == 200
            assert output["StatusText"] == "OK"
            assert output["ResponseBody"] == {"ok": True}
            assert output["Headers"]["Content-Type"] == ["application/json"]
            assert output["Headers"]["Content-Length"] == ["12"]
            assert "x-amzn-RequestId" in output["Headers"]
            return True

        verify_execution_result(
            _verify_result,
            "SUCCEEDED",
            "services/apigw_invoke",
            exec_input=json.dumps(exec_input),
        )

        assert received == [
            {
                "path": "/prod/_user_request_/things/?mode=fast&mode=slow&limit=10&flag=0",
                "body": '{"hello": "world"}',
                "x_custom": "[a,b]",
            }
        ]
    finally:
        server.stop()


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_state_machine_calling_apigateway_invoke_get_without_stage_or_path():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point in testing this in ServerMode")

    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            received.append(
                {"path": self.path, "x_custom": self.headers.get("X-Custom")}
            )
            payload = b"not json"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = SimpleServer(Handler)
    server.start()
    _, port = server.get_host_and_port()

    try:
        exec_input = {"ApiEndpoint": f"http://127.0.0.1:{port}"}

        def _verify_result(client, execution, execution_arn):
            output = json.loads(execution["output"])
            assert output["StatusCode"] == 200
            assert output["StatusText"] == "OK"
            assert output["ResponseBody"] == "not json"
            # The response has no Content-Length, which used to raise a KeyError
            assert "Content-Length" not in output["Headers"]
            return True

        verify_execution_result(
            _verify_result,
            "SUCCEEDED",
            "services/apigw_invoke_get",
            exec_input=json.dumps(exec_input),
        )

        assert received == [
            {"path": "/_user_request_//?name=moto&empty=", "x_custom": "single"}
        ]
    finally:
        server.stop()


@pytest.mark.parametrize(
    "method,headers",
    [
        ("POST", {"Authorization": "Bearer token"}),
        ("POST", {"X-Amz-Custom": "value"}),
        ("GET", {}),
    ],
    ids=["forbidden_header", "forbidden_header_prefix", "body_with_get"],
)
@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_state_machine_calling_apigateway_invoke_with_invalid_parameters(
    method, headers
):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point in testing this in ServerMode")

    exec_input = {
        # The request is rejected before it is sent, so this endpoint is never called
        "ApiEndpoint": "http://127.0.0.1:1",
        "Method": method,
        "Headers": headers,
        "RequestBody": {"hello": "world"},
    }

    def _verify_result(client, execution, execution_arn):
        assert execution["error"] == "ApiGateway.ValueError"
        return True

    verify_execution_result(
        _verify_result,
        "FAILED",
        "services/apigw_invoke_dynamic",
        exec_input=json.dumps(exec_input),
    )


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_state_machine_calling_apigateway_invoke_error():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point in testing this in ServerMode")

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            payload = b'{"message": "broken"}'
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = SimpleServer(Handler)
    server.start()
    _, port = server.get_host_and_port()

    try:
        exec_input = {
            "ApiEndpoint": f"http://127.0.0.1:{port}",
            "RequestBody": {"hello": "world"},
        }

        def _verify_result(client, execution, execution_arn):
            assert execution["error"] == "ApiGateway.500"
            assert json.loads(execution["cause"]) == {"message": "broken"}
            return True

        verify_execution_result(
            _verify_result,
            "FAILED",
            "services/apigw_invoke",
            exec_input=json.dumps(exec_input),
        )
    finally:
        server.stop()
