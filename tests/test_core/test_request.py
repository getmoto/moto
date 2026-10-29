import pytest

from moto.core.request import Request, determine_request_protocol
from moto.core.utils import get_service_model


@pytest.mark.parametrize(
    "content_type,smithy_protocol,expected",
    [
        ("application/cbor", "rpc-v2-cbor", "smithy-rpc-v2-cbor"),
        # Operations without input have no body, and therefore no Content-Type
        (None, "rpc-v2-cbor", "smithy-rpc-v2-cbor"),
        ("application/x-amz-json-1.0", None, "json"),
        ("application/x-www-form-urlencoded; charset=utf-8", None, "query"),
    ],
)
def test_determine_request_protocol(
    content_type: str | None,
    smithy_protocol: str | None,
    expected: str,
) -> None:
    headers = {}
    if content_type is not None:
        headers["Content-Type"] = content_type
    if smithy_protocol is not None:
        headers["Smithy-Protocol"] = smithy_protocol
    request = Request.from_primitives(
        "POST", "https://monitoring.amazonaws.com/", headers
    )
    service_model = get_service_model("cloudwatch")
    protocol = determine_request_protocol(service_model, request)
    assert protocol == expected
