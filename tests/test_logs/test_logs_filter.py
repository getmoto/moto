import boto3
from unittest import TestCase
from datetime import timedelta

from moto import mock_logs
from moto.core.utils import unix_time_millis, utcnow

TEST_REGION = "eu-west-1"


class TestLogFilter(TestCase):
    def setUp(self) -> None:
        self.conn = boto3.client("logs", TEST_REGION)
        self.log_group_name = "dummy"
        self.log_stream_name = "stream"
        self.conn.create_log_group(logGroupName=self.log_group_name)
        self.conn.create_log_stream(
            logGroupName=self.log_group_name, logStreamName=self.log_stream_name
        )


@mock_logs
class TestLogFilterParameters(TestLogFilter):
    def setUp(self) -> None:
        super().setUp()

    def test_filter_logs_interleaved(self):
        messages = [
            {"timestamp": 0, "message": "hello"},
            {"timestamp": 0, "message": "world"},
        ]
        self.conn.put_log_events(
            logGroupName=self.log_group_name,
            logStreamName=self.log_stream_name,
            logEvents=messages,
        )
        res = self.conn.filter_log_events(
            logGroupName=self.log_group_name,
            logStreamNames=[self.log_stream_name],
            interleaved=True,
        )
        events = res["events"]
        for original_message, resulting_event in zip(messages, events):
            assert resulting_event["eventId"] == str(resulting_event["eventId"])
            assert resulting_event["timestamp"] == original_message["timestamp"]
            assert resulting_event["message"] == original_message["message"]

    def test_put_log_events_now(self):
        ts_1 = int(unix_time_millis())
        ts_2 = int(unix_time_millis(utcnow() + timedelta(minutes=5)))
        ts_3 = int(unix_time_millis(utcnow() + timedelta(days=1)))

        messages = [
            {"message": f"Message {idx}", "timestamp": ts}
            for idx, ts in enumerate([ts_1, ts_2, ts_3])
        ]

        resp = self.conn.put_log_events(
            logGroupName=self.log_group_name,
            logStreamName=self.log_stream_name,
            logEvents=messages,
            sequenceToken="49599396607703531511419593985621160512859251095480828066",
        )

        # Message 2 was too new
        assert resp["rejectedLogEventsInfo"] == {"tooNewLogEventStartIndex": 2}
        # Message 0 and 1 were persisted though
        events = self.conn.filter_log_events(
            logGroupName=self.log_group_name,
            logStreamNames=[self.log_stream_name],
            limit=20,
        )["events"]
        messages = [e["message"] for e in events]
        assert "Message 0" in messages
        assert "Message 1" in messages
        assert "Message 2" not in messages

    def test_filter_logs_paging(self):
        timestamp = int(unix_time_millis())
        messages = []
        for i in range(25):
            messages.append({"message": f"Message number {i}", "timestamp": timestamp})
            timestamp += 100

        self.conn.put_log_events(
            logGroupName=self.log_group_name,
            logStreamName=self.log_stream_name,
            logEvents=messages,
        )
        res = self.conn.filter_log_events(
            logGroupName=self.log_group_name,
            logStreamNames=[self.log_stream_name],
            limit=20,
        )
        events = res["events"]
        assert len(events) == 20
        assert res["nextToken"] == "dummy@stream@" + events[-1]["eventId"]

        res = self.conn.filter_log_events(
            logGroupName=self.log_group_name,
            logStreamNames=[self.log_stream_name],
            limit=20,
            nextToken=res["nextToken"],
        )
        events += res["events"]
        assert len(events) == 25
        assert "nextToken" not in res

        for original_message, resulting_event in zip(messages, events):
            assert resulting_event["eventId"] == str(resulting_event["eventId"])
            assert resulting_event["timestamp"] == original_message["timestamp"]
            assert resulting_event["message"] == original_message["message"]

        res = self.conn.filter_log_events(
            logGroupName=self.log_group_name,
            logStreamNames=[self.log_stream_name],
            limit=20,
            nextToken="wrong-group@stream@999",
        )
        assert len(res["events"]) == 0
        assert "nextToken" not in res

    def test_filter_logs_paging__unknown_token(self):
        res = self.conn.filter_log_events(
            logGroupName=self.log_group_name,
            logStreamNames=[self.log_stream_name],
            limit=20,
            nextToken="invalid-token",
        )
        assert len(res["events"]) == 0
        assert "nextToken" not in res


@mock_logs
class TestLogsFilterPattern(TestLogFilter):
    def setUp(self) -> None:
        super().setUp()
        now = int(unix_time_millis())
        messages = [
            {"timestamp": now, "message": "hello"},
            {"timestamp": now, "message": "world"},
            {"timestamp": now, "message": "hello world"},
            {"timestamp": now, "message": "goodbye world"},
            {"timestamp": now, "message": "hello cruela"},
            {"timestamp": now, "message": "goodbye cruel world"},
        ]
        self.conn.put_log_events(
            logGroupName=self.log_group_name,
            logStreamName=self.log_stream_name,
            logEvents=messages,
        )

    def test_unknown_pattern(self):
        events = self.conn.filter_log_events(
            logGroupName=self.log_group_name,
            logStreamNames=[self.log_stream_name],
            filterPattern='{$.message = "hello"}',
        )["events"]
        assert len(events) == 6

    def test_simple_word_pattern(self):
        events = self.conn.filter_log_events(
            logGroupName=self.log_group_name,
            logStreamNames=[self.log_stream_name],
            filterPattern="hello",
        )["events"]
        messages = [e["message"] for e in events]
        assert set(messages) == {"hello", "hello cruela", "hello world"}

    def test_multiple_words_pattern(self):
        events = self.conn.filter_log_events(
            logGroupName=self.log_group_name,
            logStreamNames=[self.log_stream_name],
            filterPattern="goodbye world",
        )["events"]
        messages = [e["message"] for e in events]
        assert set(messages) == {"goodbye world", "goodbye cruel world"}

    def test_quoted_pattern(self):
        events = self.conn.filter_log_events(
            logGroupName=self.log_group_name,
            logStreamNames=[self.log_stream_name],
            filterPattern='"hello cruel"',
        )["events"]
        messages = [e["message"] for e in events]
        assert set(messages) == {"hello cruela"}
