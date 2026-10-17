import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import sleep
from unittest import SkipTest

import boto3

from moto import mock_aws, settings
from tests import DEFAULT_ACCOUNT_ID

ROLE_ARN = f"arn:aws:iam::{DEFAULT_ACCOUNT_ID}:role/sf"


def _start_http_server():
    received = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            received.append({"path": self.path, "body": body.decode()})
            payload = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, received


def _run_to_completion(definition):
    client = boto3.client("stepfunctions", region_name="us-east-1")
    arn = client.create_state_machine(
        name="apigw-invoke", definition=json.dumps(definition), roleArn=ROLE_ARN
    )["stateMachineArn"]
    execution_arn = client.start_execution(stateMachineArn=arn, input="{}")[
        "executionArn"
    ]
    for _ in range(50):
        execution = client.describe_execution(executionArn=execution_arn)
        if execution["status"] != "RUNNING":
            return execution
        sleep(0.1)
    raise AssertionError("Execution did not finish")


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_state_machine_calling_apigateway_invoke():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point in testing this in ServerMode")
    server, received = _start_http_server()
    try:
        definition = {
            "StartAt": "Call",
            "States": {
                "Call": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::apigateway:invoke",
                    "TimeoutSeconds": 30,
                    "Parameters": {
                        "ApiEndpoint": f"http://127.0.0.1:{server.server_address[1]}",
                        "Method": "POST",
                        "Stage": "prod",
                        "Path": "/things",
                        "QueryParameters": {"mode": ["fast"]},
                        "RequestBody": {"hello": "world"},
                    },
                    "End": True,
                }
            },
        }
        execution = _run_to_completion(definition)
    finally:
        server.shutdown()

    assert execution["status"] == "SUCCEEDED", execution
    assert json.loads(execution["output"])["ResponseBody"] == {"ok": True}
    assert len(received) == 1
    assert received[0]["path"].endswith("/prod/_user_request_/things?mode=fast")
    assert json.loads(received[0]["body"]) == {"hello": "world"}


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_state_machine_calling_apigateway_invoke_failure_is_reported():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point in testing this in ServerMode")
    definition = {
        "StartAt": "Call",
        "States": {
            "Call": {
                "Type": "Task",
                "Resource": "arn:aws:states:::apigateway:invoke",
                "TimeoutSeconds": 30,
                "Parameters": {
                    # Nothing is listening here, so the request cannot succeed
                    "ApiEndpoint": "http://127.0.0.1:1",
                    "Method": "GET",
                },
                "End": True,
            }
        },
    }
    execution = _run_to_completion(definition)

    # A failing request must surface as a normal failed execution, not as an
    # internal States.Runtime error
    assert execution["status"] == "FAILED", execution
    assert execution["error"].startswith("ApiGateway.")
