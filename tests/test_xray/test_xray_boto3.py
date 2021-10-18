import boto3
import json
import sure  # noqa # pylint: disable=unused-import

from moto import mock_xray

import datetime


@mock_xray
def test_put_telemetry():
    client = boto3.client("xray", region_name="us-east-1")

    client.put_telemetry_records(
        TelemetryRecords=[
            {
                "Timestamp": datetime.datetime(2015, 1, 1),
                "SegmentsReceivedCount": 123,
                "SegmentsSentCount": 123,
                "SegmentsSpilloverCount": 123,
                "SegmentsRejectedCount": 123,
                "BackendConnectionErrors": {
                    "TimeoutCount": 123,
                    "ConnectionRefusedCount": 123,
                    "HTTPCode4XXCount": 123,
                    "HTTPCode5XXCount": 123,
                    "UnknownHostCount": 123,
                    "OtherCount": 123,
                },
            }
        ],
        EC2InstanceId="string",
        Hostname="string",
        ResourceARN="string",
    )


@mock_xray
def test_put_trace_segments():
    client = boto3.client("xray", region_name="us-east-1")

    client.put_trace_segments(
        TraceSegmentDocuments=[
            json.dumps(
                {
                    "name": "example.com",
                    "id": "70de5b6f19ff9a0a",
                    "start_time": 1.478293361271e9,
                    "trace_id": "1-581cf771-a006649127e371903a2de979",
                    "end_time": 1.478293361449e9,
                }
            )
        ]
    )


@mock_xray
def test_trace_summary():
    client = boto3.client("xray", region_name="us-east-1")

    client.put_trace_segments(
        TraceSegmentDocuments=[
            json.dumps(
                {
                    "name": "example.com",
                    "id": "70de5b6f19ff9a0a",
                    "start_time": 1.478293361271e9,
                    "trace_id": "1-581cf771-a006649127e371903a2de979",
                    "in_progress": True,
                }
            ),
            json.dumps(
                {
                    "name": "example.com",
                    "id": "70de5b6f19ff9a0b",
                    "start_time": 1478293365,
                    "trace_id": "1-581cf771-a006649127e371903a2de979",
                    "end_time": 1478293385,
                }
            ),
        ]
    )

    client.get_trace_summaries(
        StartTime=datetime.datetime(2014, 1, 1), EndTime=datetime.datetime(2017, 1, 1)
    )


@mock_xray
def test_batch_get_trace():
    client = boto3.client("xray", region_name="us-east-1")

    client.put_trace_segments(
        TraceSegmentDocuments=[
            json.dumps(
                {
                    "name": "example.com",
                    "id": "70de5b6f19ff9a0a",
                    "start_time": 1.478293361271e9,
                    "trace_id": "1-581cf771-a006649127e371903a2de979",
                    "in_progress": True,
                }
            ),
            json.dumps(
                {
                    "name": "example.com",
                    "id": "70de5b6f19ff9a0b",
                    "start_time": 1478293365,
                    "trace_id": "1-581cf771-a006649127e371903a2de979",
                    "end_time": 1478293385,
                }
            ),
        ]
    )

    resp = client.batch_get_traces(
        TraceIds=[
            "1-581cf771-a006649127e371903a2de979",
            "1-581cf772-b006649127e371903a2de979",
        ]
    )
    len(resp["UnprocessedTraceIds"]).should.equal(1)
    len(resp["Traces"]).should.equal(1)


# Following are not implemented, just testing it returns what boto expects
@mock_xray
def test_batch_get_service_graph():
    client = boto3.client("xray", region_name="us-east-1")

    client.get_service_graph(
        StartTime=datetime.datetime(2014, 1, 1), EndTime=datetime.datetime(2017, 1, 1)
    )


@mock_xray
def test_batch_get_trace_graph():
    client = boto3.client("xray", region_name="us-east-1")

    client.batch_get_traces(
        TraceIds=[
            "1-581cf771-a006649127e371903a2de979",
            "1-581cf772-b006649127e371903a2de979",
        ]
    )
