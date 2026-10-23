from typing import Any

import pytest
from werkzeug.exceptions import NotFound

from moto.core.model import ServiceModel
from moto.core.request import Request
from moto.core.routing import (
    ActionConstraintContext,
    RequiredHeader,
    ServiceOperationRouter,
    get_service_router,
)
from moto.s3control.responses import S3ControlResponse


@pytest.mark.parametrize(
    "service,method,url,expected_op,expected_args",
    [
        pytest.param(
            "mq",
            "POST",
            "/v1/brokers/broker-id-test/users/username-test",
            "CreateUser",
            {"broker-id": "broker-id-test", "username": "username-test"},
            id="mq",
        ),
        pytest.param(
            "route53",
            "POST",
            "https://route53.us-east-1.amazon.com/2013-04-01/keysigningkey/HostedZoneId/Name/activate",
            "ActivateKeySigningKey",
            {"HostedZoneId": "HostedZoneId", "Name": "Name"},
            id="route53",
        ),
    ],
)
def test_rest_uri_params(
    service: str,
    method: str,
    url: str,
    expected_op: str,
    expected_args: dict[str, str],
) -> None:
    router = get_service_router(service)
    op, args = router.match(Request.from_primitives(method, url, {}))
    assert op.name == expected_op
    assert args == expected_args


@pytest.mark.parametrize(
    "url,expected_op,expected_bucket",
    [
        pytest.param("/my-bucket-name", "ListObjects", "my-bucket-name", id="path"),
        pytest.param(
            "/my-bucket-name?list-type=2",
            "ListObjectsV2",
            "my-bucket-name",
            id="path with query arg",
        ),
        pytest.param(
            "https://my-bucket-name.localhost/?list-type=2",
            "ListObjectsV2",
            "my-bucket-name",
            id="host prefix with query arg",
        ),
        pytest.param(
            "https://foobaz.localhost:5000/",
            "ListObjects",
            "foobaz",
            id="localhost with port",
        ),
        pytest.param(
            "https://b7525d4a-4973-4207-9f07-a73b4ec3ff65.s3.amazonaws.com/?tagging",
            "GetBucketTagging",
            "b7525d4a-4973-4207-9f07-a73b4ec3ff65",
            id="aws host",
        ),
    ],
)
def test_s3_bucket_routing(url: str, expected_op: str, expected_bucket: str) -> None:
    router = get_service_router("s3")
    op, args = router.match(Request.from_primitives("GET", url, {}))
    assert op.name == expected_op
    assert args == {"Bucket": expected_bucket}


@pytest.mark.parametrize(
    "url,expected_op,expected_args",
    [
        pytest.param(
            "https://123456789012.s3-control.us-east-1.amazonaws.com/v20180820/accesspoint/my-access-point",
            "GetAccessPoint",
            # AccountId comes from the host prefix, when the host has it.
            {"name": "my-access-point", "AccountId": "123456789012"},
            id="aws host",
        ),
        pytest.param(
            "http://localhost:5000/v20180820/accesspoint/my-access-point",
            "GetAccessPoint",
            # No host prefix, so no AccountId (the parser falls back to the header).
            {"name": "my-access-point"},
            id="server mode",
        ),
    ],
)
def test_s3_control_routing(
    url: str, expected_op: str, expected_args: dict[str, str]
) -> None:
    router = get_service_router("s3control")
    req = Request.from_primitives("GET", url, {"x-amz-account-id": "0123456789012"})
    op, args = router.match(req)
    assert op.name == expected_op
    assert args == expected_args


@pytest.mark.parametrize(
    "url,expected_account_id",
    [
        pytest.param(
            "https://111111111111.s3-control.us-east-1.amazonaws.com",
            "111111111111",
            id="host prefix",
        ),
        pytest.param("http://localhost:5000", "222222222222", id="header fallback"),
    ],
)
def test_s3_control_account_id_host_label(url: str, expected_account_id: str) -> None:
    response = S3ControlResponse()
    req = Request.from_primitives(
        "GET",
        f"{url}/v20180820/accesspoint/my-access-point",
        {"x-amz-account-id": "222222222222"},
    )
    response.setup_class(req, req.url)
    assert response._get_param("AccountId") == expected_account_id
    assert response._get_param("Name") == "my-access-point"


def test_s3_key_trailing_slash_is_preserved() -> None:
    router = get_service_router("s3")
    req = Request.from_primitives("PUT", "https://s3.amazonaws.com/bucket/dir/", {})
    op, args = router.match(req)
    assert op.name == "PutObject"
    assert args["Key"] == "dir/"


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("https://s3.amazonaws.com/bucket", id="without slash"),
        pytest.param("https://s3.amazonaws.com/bucket/", id="with slash"),
    ],
)
def test_s3_bucket_trailing_slash_is_optional(url: str) -> None:
    router = get_service_router("s3")
    op, args = router.match(Request.from_primitives("PUT", url, {}))
    assert op.name == "CreateBucket"
    assert args == {"Bucket": "bucket"}


def test_uri_params_are_decoded_once() -> None:
    router = get_service_router("s3")
    req = Request.from_primitives("PUT", "https://s3.amazonaws.com/bucket/a%2525b", {})
    _, args = router.match(req)
    assert args["Key"] == "a%25b"


def test_last_label_is_implicitly_greedy() -> None:
    router = get_service_router("mwaa")
    arn = "arn:aws:airflow:us-east-1:123456789012:environment/my-env"
    req = Request.from_primitives("GET", f"https://localhost/tags/{arn}", {})
    op, args = router.match(req)
    assert op.name == "ListTagsForResource"
    assert args["ResourceArn"] == arn


def test_implicitly_greedy_label_excludes_trailing_slash() -> None:
    router = get_service_router("s3")
    req = Request.from_primitives("GET", "https://s3.amazonaws.com/bucket/?tagging", {})
    op, args = router.match(req)
    assert op.name == "GetBucketTagging"
    assert args == {"Bucket": "bucket"}


def test_s3_virtual_host_key_with_leading_slash() -> None:
    router = get_service_router("s3")
    req = Request.from_primitives("PUT", "https://bucket.s3.amazonaws.com//key", {})
    op, args = router.match(req)
    assert op.name == "PutObject"
    assert args == {"Bucket": "bucket", "Key": "/key"}


def test_rest_query_arg_constraints_ignore_form_body() -> None:
    router = get_service_router("s3")
    body = b"delete="
    req = Request.from_primitives(
        "POST",
        "https://s3.amazonaws.com/bucket",
        {"Content-Type": "application/x-www-form-urlencoded"},
        body,
    )
    op, _ = router.match(req)
    # The form body doesn't satisfy DeleteObjects' `?delete` query literal...
    assert op.name == "PostObject"
    # ...and matching didn't consume the request body.
    assert req.get_data() == body


@pytest.mark.parametrize(
    "method,url,body",
    [
        pytest.param(
            "POST",
            "https://sts.amazonaws.com/",
            "Action=GetCallerIdentity",
            id="form body",
        ),
        pytest.param(
            "GET",
            "https://sts.amazonaws.com/?Action=GetCallerIdentity",
            None,
            id="query string",
        ),
        pytest.param(
            "POST",
            "https://sts.amazonaws.com/any/path",
            "Action=GetCallerIdentity",
            id="path ignored",
        ),
    ],
)
def test_query_protocol_routes_by_action(
    method: str, url: str, body: str | None
) -> None:
    router = get_service_router("sts")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    op, args = router.match(Request.from_primitives(method, url, headers, body))
    assert op.name == "GetCallerIdentity"
    assert args == {}


@pytest.mark.parametrize(
    "service,headers,body",
    [
        pytest.param(
            "sts",
            {"Content-Type": "application/x-www-form-urlencoded"},
            "Action=NotAnAction",
            id="query unknown action",
        ),
        pytest.param(
            "sts",
            {"Content-Type": "application/x-www-form-urlencoded"},
            "Version=2011-06-15",
            id="query missing action",
        ),
        pytest.param(
            "sqs",
            {
                "Content-Type": "application/x-amz-json-1.0",
                "X-Amz-Target": "Wrong.SendMessage",
            },
            b"{}",
            id="json wrong target prefix",
        ),
    ],
)
def test_query_and_json_protocol_not_found(
    service: str, headers: dict[str, str], body: str | bytes
) -> None:
    router = get_service_router(service)
    req = Request.from_primitives("POST", "https://localhost:5000/", headers, body)
    with pytest.raises(NotFound):
        router.match(req)


@pytest.mark.parametrize(
    "headers,body",
    [
        pytest.param(
            {
                "Content-Type": "application/x-amz-json-1.0",
                "X-Amz-Target": "AmazonSQS.SendMessage",
            },
            b"{}",
            id="json",
        ),
        pytest.param(
            {"Content-Type": "application/x-www-form-urlencoded"},
            "Action=SendMessage",
            id="query",
        ),
    ],
)
def test_sqs_queue_url_path_params(headers: dict[str, str], body: str | bytes) -> None:
    router = get_service_router("sqs")
    url = "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
    op, args = router.match(Request.from_primitives("POST", url, headers, body))
    assert op.name == "SendMessage"
    assert args == {"AccountId": "123456789012", "QueueName": "my-queue"}


@pytest.mark.parametrize(
    "method,url,expected_op,expected_args",
    [
        pytest.param(
            "GET",
            "https://my.dotted.bucket.s3.amazonaws.com/key",
            "GetObject",
            {"Bucket": "my.dotted.bucket", "Key": "key"},
            id="object",
        ),
        pytest.param(
            "GET",
            "https://my.dotted.bucket.s3.us-west-2.amazonaws.com/?tagging",
            "GetBucketTagging",
            {"Bucket": "my.dotted.bucket"},
            id="bucket",
        ),
    ],
)
def test_s3_virtual_host_dotted_bucket_name(
    method: str, url: str, expected_op: str, expected_args: dict[str, str]
) -> None:
    router = get_service_router("s3")
    op, args = router.match(Request.from_primitives(method, url, {}))
    assert op.name == expected_op
    assert args == expected_args


@pytest.mark.parametrize(
    "url,expected_op",
    [
        pytest.param("/bucket/key?uploadId=abc", "ListParts", id="required arg"),
        pytest.param("/bucket/key", "GetObject", id="missing required arg"),
    ],
)
def test_rest_required_query_arg_constraint(url: str, expected_op: str) -> None:
    router = get_service_router("s3")
    op, _ = router.match(Request.from_primitives("GET", url, {}))
    assert op.name == expected_op


def test_rest_leading_slash_of_greedy_first_label_is_preserved() -> None:
    router = get_service_router("mediastore-data")
    op, args = router.match(
        Request.from_primitives("GET", "http://localhost:5000//folder/file", {})
    )
    assert op.name == "GetObject"
    assert args == {"Path": "/folder/file"}


def test_rest_method_not_allowed_is_not_found() -> None:
    router = get_service_router("mq")
    req = Request.from_primitives("PATCH", "/v1/brokers/broker-id/users/username", {})
    with pytest.raises(NotFound):
        router.match(req)


def test_protocol_without_router_is_not_found() -> None:
    router = get_service_router("cloudwatch")
    headers = {"Content-Type": "application/cbor", "Smithy-Protocol": "rpc-v2-cbor"}
    req = Request.from_primitives(
        "POST", "/service/GraniteServiceVersion20100801/operation/ListMetrics", headers
    )
    with pytest.raises(NotFound):
        router.match(req)


def _rest_json_model(operations: dict[str, dict[str, Any]]) -> ServiceModel:
    return ServiceModel(
        {
            "metadata": {
                "protocol": "rest-json",
                "serviceId": "Test",
                "endpointPrefix": "test",
            },
            "operations": {
                name: {"name": name, "http": op["http"], "input": {"shape": name}}
                for name, op in operations.items()
            },
            "shapes": {
                **{
                    name: {
                        "type": "structure",
                        "required": list(op["members"]),
                        "members": op["members"],
                    }
                    for name, op in operations.items()
                },
                "String": {"type": "string"},
            },
        },
        service_name="test",
    )


def test_rest_query_literal_that_is_also_a_required_member() -> None:
    type_member = {"shape": "String", "location": "querystring", "locationName": "type"}
    model = _rest_json_model(
        {
            "ListFoos": {
                "http": {"method": "GET", "requestUri": "/things?type=foo"},
                "members": {"Type": type_member},
            },
            "ListThings": {
                "http": {"method": "GET", "requestUri": "/things"},
                "members": {"Type": type_member},
            },
        }
    )
    router = ServiceOperationRouter(model)
    # The literal value constrains ListFoos, rather than just requiring the arg.
    op, _ = router.match(Request.from_primitives("GET", "/things?type=bar", {}))
    assert op.name == "ListThings"
    op, _ = router.match(Request.from_primitives("GET", "/things?type=foo", {}))
    assert op.name == "ListFoos"


def test_rest_no_candidate_accepts_request_is_not_found() -> None:
    model = _rest_json_model(
        {
            "GetThing": {
                "http": {"method": "GET", "requestUri": "/things"},
                "members": {
                    "Id": {
                        "shape": "String",
                        "location": "header",
                        "locationName": "x-id",
                    }
                },
            },
        }
    )
    router = ServiceOperationRouter(model)
    op, _ = router.match(Request.from_primitives("GET", "/things", {"x-id": "1"}))
    assert op.name == "GetThing"
    with pytest.raises(NotFound):
        router.match(Request.from_primitives("GET", "/things", {}))


@pytest.mark.parametrize(
    "headers,accepted",
    [
        pytest.param({"x-mode": "fast"}, True, id="matching value"),
        pytest.param({"x-mode": "slow"}, False, id="different value"),
        pytest.param({}, False, id="missing header"),
    ],
)
def test_required_header_with_value(headers: dict[str, str], accepted: bool) -> None:
    context = ActionConstraintContext(Request.from_primitives("GET", "/", headers))
    assert RequiredHeader("x-mode", "fast").accept(context) is accepted
