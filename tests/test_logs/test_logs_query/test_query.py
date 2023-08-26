from moto.core import DEFAULT_ACCOUNT_ID
from moto.logs.models import LogGroup
from moto.logs.logs_query import execute_query
from moto.core.utils import unix_time, unix_time_millis

from unittest import TestCase
from uuid import uuid4


DEFAULT_QUERY = """fields @timestamp, @message, @logStream, @log
| sort @timestamp desc
| limit 20"""

SIMPLIFIED_ONE_LINE_QUERY = "fields @timestamp, @message | sort @timestamp asc"


class TestLogsQueries(TestCase):
    def setUp(self) -> None:
        self.log_group = LogGroup(
            account_id=DEFAULT_ACCOUNT_ID, region="us-east-1", name="test", tags={}
        )
        self.stream_1_name = f"2022/02/02/[$LATEST]{uuid4()}"
        self.log_group.create_log_stream(self.stream_1_name)
        event1 = {
            "timestamp": unix_time_millis() - 1000,
            "message": "my previous message",
        }
        event2 = {"timestamp": unix_time_millis(), "message": "my current message"}
        self.events = [event1, event2]
        self.log_group.streams[self.stream_1_name].put_log_events(self.events)

    def test_default_query(self):
        resp = execute_query(
            [self.log_group],
            DEFAULT_QUERY,
            start_time=unix_time() - 2000,
            end_time=unix_time() + 2000,
        )
        for event in resp:
            event.pop("@ptr")
        assert resp == [
            {
                "@timestamp": event["timestamp"],
                "@message": event["message"],
                "@logStream": self.stream_1_name,
                "@log": "test",
            }
            for event in self.events
        ]

    def test_simplified_query(self):
        resp = execute_query(
            [self.log_group],
            SIMPLIFIED_ONE_LINE_QUERY,
            start_time=unix_time() - 2000,
            end_time=unix_time() + 2000,
        )
        for event in resp:
            event.pop("@ptr")
        assert resp == [
            {"@timestamp": event["timestamp"], "@message": event["message"]}
            for event in reversed(self.events)
        ]
