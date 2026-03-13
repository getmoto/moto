# mypy: ignore-errors
import base64
import copy
import json
import os
import re
from calendar import timegm
from enum import Enum
from urllib.parse import parse_qs, urlparse

import pytest
from botocore.awsrequest import HeadersDict
from botocore.utils import parse_timestamp
from dateutil.tz import tzutc

from moto.core.model import OperationModel, ServiceModel
from moto.core.parse import PROTOCOL_PARSERS
from moto.core.responses import BaseResponse
from moto.core.serialize import SERIALIZERS

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "protocols")
PROTOCOL_TEST_BLACKLIST = [
    "REST XML Event Stream",
    "RPC JSON Event Stream",
]


class TestType(Enum):
    __test__ = False  # Tell test runner to ignore this class

    INPUT = "input"
    OUTPUT = "output"


def _compliance_tests(test_type=None):
    inp = test_type is None or test_type is TestType.INPUT
    out = test_type is None or test_type is TestType.OUTPUT

    for full_path in _walk_files():
        if full_path.endswith(".json"):
            for model, case, protocol in _load_cases(full_path):
                if model.get("description") in PROTOCOL_TEST_BLACKLIST:
                    continue
                description = case["description"]
                test_name = f"{protocol}-protocol-{description}"
                if "params" in case and inp:
                    yield pytest.param(model, case, protocol, id=test_name)
                elif "response" in case and out:
                    yield pytest.param(model, case, protocol, id=test_name)


def _walk_files():
    for root, _, filenames in os.walk(TEST_DIR):
        for filename in filenames:
            yield os.path.join(root, filename)


def _load_cases(full_path):
    all_test_data = json.load(open(full_path))
    protocol = os.path.basename(full_path).split(".")[0]
    for test_data in all_test_data:
        cases = test_data.pop("cases")
        description = test_data["description"]
        for index, case in enumerate(cases):
            case["description"] = description
            case["id"] = index
            yield test_data, case, protocol


def _compliance_blob_parser(value):
    # By default, Blobs are returned as bytes type because it's possible
    # that the blob contains binary data that actually can't be decoded.
    # For the compliance tests, we decode to a string for easier asserts.
    return base64.b64decode(value).decode("utf-8")


def _compliance_timestamp_parser(value):
    datetime = parse_timestamp(value)
    datetime = datetime.astimezone(tzutc())
    epoch_time = int(timegm(datetime.timetuple()))
    return epoch_time


def _build_query_params(query_string, body, headers):
    def mock_multidict(data):
        params = parse_qs(data, keep_blank_values=True)
        params = {k: v if len(v) > 1 else v[0] for k, v in params.items()}
        return params

    query_params = mock_multidict(query_string)
    if headers.get("Content-Type", "").startswith("application/x-www-form-urlencoded"):
        body_params = mock_multidict(body)
        query_params.update(body_params)
    return query_params


def _create_request_dict(given, serialized):
    method = serialized.get("method", given.get("http", {}).get("method", "POST"))
    # We need the headers to be case-insensitive
    headers = HeadersDict(serialized.get("headers", {}))
    uri = serialized.get("uri", "/")
    parsed_uri = urlparse(uri)
    query_string = parsed_uri.query
    url_path = parsed_uri.path
    body = serialized["body"]
    values = _build_query_params(query_string, serialized["body"], headers)
    uri_template = given.get("http", {}).get("requestUri", "/")
    uri_regex = BaseResponse.uri_to_regexp(uri_template)
    uri_match = re.match(uri_regex, url_path)
    uri_params = uri_match.groupdict() if uri_match else {}
    request_dict = {
        "method": method,
        "body": body,
        "headers": headers,
        "values": values,
        "url_path": url_path,
        "url_params": uri_params,
    }
    return request_dict


@pytest.mark.parametrize(
    "json_description, case, protocol", _compliance_tests(TestType.INPUT)
)
def test_input_compliance(json_description: dict, case: dict, protocol: str):
    service_description = copy.deepcopy(json_description)
    model = ServiceModel(service_description)
    operation_model = OperationModel(case["given"], model)
    protocol_parser = PROTOCOL_PARSERS[protocol]
    parser = protocol_parser(
        operation_model,
        blob_parser=_compliance_blob_parser,
        timestamp_parser=_compliance_timestamp_parser,
    )
    request_dict = _create_request_dict(case["given"], case["serialized"])
    parsed = parser.parse(request_dict)
    assert parsed == case.get("params", {})


@pytest.mark.parametrize(
    "json_description, case, protocol", _compliance_tests(TestType.OUTPUT)
)
def test_output_compliance(json_description: dict, case: dict, protocol):
    service_description = copy.deepcopy(json_description)
    model = ServiceModel(service_description)
    operation_model = OperationModel(case["given"], model)
    protocol_serializer = SERIALIZERS[protocol]
    serializer = protocol_serializer(operation_model)
    result = case["result"] if "error" not in case else _create_exception(case)
    resp = serializer.serialize(result)  # _to_response(result)
    assert resp["body"] == case["response"]["body"]
    assert "Content-Type" in resp["headers"]
    protocol_to_content_type = {
        "ec2": "text/xml",
        "json": "application/x-amz-json-1.0",
        "query": "text/xml",
        "query-json": "application/json",
        "rest-xml": "text/xml",
        "rest-json": "application/json",
    }
    assert resp["headers"]["Content-Type"] == protocol_to_content_type[protocol]
    headers_expected = case["response"]["headers"]
    # TODO: Get rid of this if once we get the headers sorted for all responses
    if headers_expected:
        del resp["headers"]["Content-Type"]
        assert resp["headers"] == headers_expected
    assert resp["status_code"] == case["response"]["status_code"]


def _create_exception(case):
    exc = type(case["errorCode"], (Exception,), {})()
    exc.code = case["errorCode"]
    if "errorMessage" in case:
        exc.message = case["errorMessage"]
        exc.Message = case["errorMessage"]
    for key, value in case["error"].items():
        setattr(exc, key, value)
    return exc
