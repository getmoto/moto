import struct
from datetime import datetime, timezone
from unittest import SkipTest

import pytest
from botocore.eventstream import ChecksumMismatch, EventStreamBuffer

from moto.core.serialize import (
    EventStreamEncoder,
    JSONSerializer,
    RestJSONSerializer,
    S3Serializer,
)
from moto.core.utils import get_service_model
from moto.core.versions import BOTOCORE_VERSION, LooseVersion


def _decode(message_bytes: bytes):  # type: ignore
    buf = EventStreamBuffer()
    buf.add_data(message_bytes)
    return list(buf)


def test_framer_encodes_basic_message_with_string_headers() -> None:
    encoded = EventStreamEncoder().encode_message(
        {":message-type": "event", ":event-type": "End"}, b""
    )
    [msg] = _decode(encoded)
    assert msg.headers == {":message-type": "event", ":event-type": "End"}
    assert msg.payload == b""


def test_framer_encodes_payload_and_content_type_header() -> None:
    payload = b"<Stats><BytesScanned>10</BytesScanned></Stats>"
    encoded = EventStreamEncoder().encode_message(
        {
            ":message-type": "event",
            ":event-type": "Stats",
            ":content-type": "text/xml",
        },
        payload,
    )
    [msg] = _decode(encoded)
    assert msg.headers[":content-type"] == "text/xml"
    assert msg.payload == payload


def test_framer_supports_all_modeled_header_types() -> None:
    encoded = EventStreamEncoder().encode_message(
        {
            "true": True,
            "false": False,
            "int": 7,
            "string": "hello",
            "bytes": b"\x01\x02\x03",
            "ts": datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        },
        b"",
    )
    [msg] = _decode(encoded)
    assert msg.headers["true"] is True
    assert msg.headers["false"] is False
    assert msg.headers["int"] == 7
    assert msg.headers["string"] == "hello"
    assert msg.headers["bytes"] == b"\x01\x02\x03"
    # botocore decodes timestamps as the int64 it stored (ms since epoch).
    assert msg.headers["ts"] == int(
        datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc).timestamp() * 1000
    )


def test_framer_rejects_overlong_header_name() -> None:
    too_long = "x" * 300
    with pytest.raises(ValueError):
        EventStreamEncoder().encode_message({too_long: "v"}, b"")


def test_framer_message_crc_detects_corruption() -> None:
    encoded = bytearray(
        EventStreamEncoder().encode_message(
            {":message-type": "event", ":event-type": "End"}, b""
        )
    )
    # Flip a byte inside the headers and confirm botocore's decoder raises.
    encoded[20] ^= 0xFF
    buf = EventStreamBuffer()
    buf.add_data(bytes(encoded))
    with pytest.raises(ChecksumMismatch):
        list(buf)


def test_framer_total_length_matches_prelude() -> None:
    payload = b"hello"
    encoded = EventStreamEncoder().encode_message(
        {":message-type": "event", ":event-type": "X"}, payload
    )
    total_length = struct.unpack("!I", encoded[:4])[0]
    assert total_length == len(encoded)


def test_s3_select_object_content_serialization() -> None:
    operation_model = get_service_model("s3").operation_model("SelectObjectContent")
    serializer = S3Serializer(operation_model=operation_model)
    result = {
        "Payload": [
            {"Records": {"Payload": b"row1\nrow2\n"}},
            {
                "Stats": {
                    "Details": {
                        "BytesScanned": 100,
                        "BytesProcessed": 100,
                        "BytesReturned": 10,
                    }
                }
            },
            {"End": {}},
        ]
    }
    response = serializer.serialize(result)
    assert response["status_code"] == 200
    assert response["headers"]["Content-Type"] == "application/vnd.amazon.eventstream"
    body = response["body"]
    assert isinstance(body, bytes)
    messages = _decode(body)
    assert [m.headers[":event-type"] for m in messages] == ["Records", "Stats", "End"]
    assert messages[0].headers[":content-type"] == "application/octet-stream"
    assert messages[0].payload == b"row1\nrow2\n"
    assert messages[1].headers[":content-type"] == "text/xml"
    assert b"<BytesScanned>100</BytesScanned>" in messages[1].payload
    assert b"<BytesReturned>10</BytesReturned>" in messages[1].payload
    assert ":content-type" not in messages[2].headers
    assert messages[2].payload == b""


def test_logs_start_live_tail_json_event_stream() -> None:
    if LooseVersion(BOTOCORE_VERSION) < LooseVersion("1.33.13"):
        raise SkipTest(
            "StartLiveTail operation is not available in older Botocore versions."
        )
    operation_model = get_service_model("logs").operation_model("StartLiveTail")
    serializer = JSONSerializer(operation_model=operation_model)
    result = {
        "responseStream": [
            {
                "sessionStart": {
                    "requestId": "req-1",
                    "sessionId": "sess-1",
                    "logGroupIdentifiers": ["arn:aws:logs:::lg"],
                    "logStreamNames": [],
                    "logStreamNamePrefixes": [],
                    "logEventFilterPattern": "",
                }
            },
            {
                "sessionUpdate": {
                    "sessionMetadata": {"sampled": False},
                    "sessionResults": [
                        {
                            "logStreamName": "stream-1",
                            "logGroupIdentifier": "arn:aws:logs:::lg",
                            "message": "hello",
                            "timestamp": 1700000000000,
                            "ingestionTime": 1700000000000,
                        }
                    ],
                }
            },
        ]
    }
    response = serializer.serialize(result)
    assert response["headers"]["Content-Type"] == "application/vnd.amazon.eventstream"
    body = response["body"]
    assert isinstance(body, bytes)
    messages = _decode(body)
    initial_response = messages[0]
    assert initial_response.headers[":event-type"] == "initial-response"
    messages = messages[1:]
    assert [m.headers[":event-type"] for m in messages] == [
        "sessionStart",
        "sessionUpdate",
    ]
    for msg in messages:
        assert msg.headers[":content-type"] == "application/json"
    import json

    start_payload = json.loads(messages[0].payload)
    assert start_payload["requestId"] == "req-1"
    update_payload = json.loads(messages[1].payload)
    assert update_payload["sessionResults"][0]["logStreamName"] == "stream-1"


def test_polly_start_speech_synthesis_stream_event_stream() -> None:
    if LooseVersion(BOTOCORE_VERSION) < LooseVersion("1.42.72"):
        raise SkipTest(
            "StartSpeechSynthesisStream operation is not available in older Botocore versions."
        )
    operation_model = get_service_model("polly").operation_model(
        "StartSpeechSynthesisStream"
    )
    serializer = RestJSONSerializer(operation_model=operation_model)
    audio_chunk = b"\x00\x01\x02audio-bytes"
    result = {
        "EventStream": [
            {"AudioEvent": {"AudioChunk": audio_chunk}},
            {"StreamClosedEvent": {"RequestCharacters": 42}},
        ]
    }
    response = serializer.serialize(result)
    assert response["headers"]["Content-Type"] == "application/vnd.amazon.eventstream"
    body = response["body"]
    assert isinstance(body, bytes)
    messages = _decode(body)
    assert [m.headers[":event-type"] for m in messages] == [
        "AudioEvent",
        "StreamClosedEvent",
    ]
    assert messages[0].headers[":content-type"] == "application/octet-stream"
    assert messages[0].payload == audio_chunk
    assert messages[1].headers[":content-type"] == "application/json"
    import json

    closed_payload = json.loads(messages[1].payload)
    assert closed_payload["RequestCharacters"] == 42


def test_initial_response_emitted_for_non_stream_output_members() -> None:
    """Synthetic operation: output has both an event-stream member and a regular
    member, exercising the initial-response branch."""
    from moto.core.model import ServiceModel

    model = {
        "metadata": {
            "protocol": "json",
            "apiVersion": "2024-01-01",
            "endpointPrefix": "test",
        },
        "documentation": "",
        "operations": {
            "Op": {
                "name": "Op",
                "http": {"method": "POST", "requestUri": "/"},
                "output": {"shape": "OpOutput"},
            }
        },
        "shapes": {
            "OpOutput": {
                "type": "structure",
                "members": {
                    "Greeting": {"shape": "StringType"},
                    "Stream": {"shape": "EventUnion"},
                },
            },
            "EventUnion": {
                "type": "structure",
                "eventstream": True,
                "members": {
                    "Tick": {"shape": "TickEvent"},
                    "String": {"shape": "StringEvent"},
                },
            },
            "TickEvent": {
                "type": "structure",
                "event": True,
                "members": {"value": {"shape": "StringType"}},
            },
            "StringEvent": {
                "type": "structure",
                "members": {"value": {"shape": "StringType", "eventpayload": True}},
                "event": True,
            },
            "StringType": {"type": "string"},
        },
    }
    service_model = ServiceModel(model)
    operation_model = service_model.operation_model("Op")
    serializer = JSONSerializer(operation_model=operation_model)
    result = {
        "Greeting": "hi",
        "Stream": [{"Tick": {"value": "one"}}, {"String": {"value": "two"}}],
    }
    response = serializer.serialize(result)
    messages = _decode(response["body"])  # type: ignore
    assert messages[0].headers[":event-type"] == "initial-response"
    import json

    assert json.loads(messages[0].payload) == {"Greeting": "hi"}
    assert messages[1].headers[":event-type"] == "Tick"
    assert json.loads(messages[1].payload) == {"value": "one"}

    assert messages[2].headers[":event-type"] == "String"
    assert messages[2].headers[":content-type"] == "text/plain"
    assert messages[2].payload == b"two"
