import binascii
import json
import struct
from typing import Any

PAGINATION_MODEL = {
    "describe_log_groups": {
        "input_token": "next_token",
        "limit_key": "limit",
        "limit_default": 50,
        "unique_attribute": "arn",
        "fail_on_invalid_token": False,
    },
    "describe_log_streams": {
        "input_token": "next_token",
        "limit_key": "limit",
        "limit_default": 50,
        "unique_attribute": "arn",
    },
}


class FilterPattern:
    def __init__(self, term: str):
        self.term = term


class QuotedTermFilterPattern(FilterPattern):
    def matches(self, message: str) -> bool:
        # We still have the quotes around the term - we should remove those in the parser
        return self.term[1:-1] in message


class SingleTermFilterPattern(FilterPattern):
    def matches(self, message: str) -> bool:
        required_words = self.term.split(" ")
        return all(word in message for word in required_words)


class UnsupportedFilterPattern(FilterPattern):
    def matches(self, message: str) -> bool:
        return True


class EventMessageFilter:
    def __init__(self, pattern: str):
        current_phrase = ""
        current_type: type[FilterPattern] = None  # type: ignore
        if pattern:
            for char in pattern:
                if not current_type:
                    if char.isalpha():
                        current_type = SingleTermFilterPattern
                    elif char == '"':
                        current_type = QuotedTermFilterPattern
                    else:
                        current_type = UnsupportedFilterPattern
                current_phrase += char
        else:
            current_type = UnsupportedFilterPattern
        self.filter_type = current_type(current_phrase)

    def matches(self, message: str) -> bool:
        return self.filter_type.matches(message)  # type: ignore


def _create_event_stream_header(key: bytes, value: bytes) -> bytes:
    return struct.pack("b", len(key)) + key + struct.pack("!bh", 7, len(value)) + value


def _create_event_stream_message(event_type: bytes, payload: bytes) -> bytes:
    headers = _create_event_stream_header(b":message-type", b"event")
    headers += _create_event_stream_header(b":event-type", event_type)
    headers += _create_event_stream_header(b":content-type", b"application/json")

    headers_length = struct.pack("!I", len(headers))
    total_length = struct.pack("!I", len(payload) + len(headers) + 16)
    prelude = total_length + headers_length

    prelude_crc = struct.pack("!I", binascii.crc32(prelude))
    message_crc = struct.pack(
        "!I", binascii.crc32(prelude + prelude_crc + headers + payload)
    )

    return prelude + prelude_crc + headers + payload + message_crc


def serialize_start_live_tail(
    session_start: dict[str, Any], session_update: dict[str, Any]
) -> bytes:
    """Serialize a minimal CloudWatch Logs StartLiveTail event stream."""
    return (
        _create_event_stream_message(b"initial-response", b"{}")
        + _create_event_stream_message(
            b"sessionStart", json.dumps(session_start).encode("utf-8")
        )
        + _create_event_stream_message(
            b"sessionUpdate", json.dumps(session_update).encode("utf-8")
        )
    )
