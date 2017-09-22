from __future__ import unicode_literals

import boto3
import json
import botocore.exceptions
import sure   # noqa

from moto import mock_xray

import datetime


@mock_xray
def test_put_telemetry():
    client = boto3.client('xray', region_name='us-east-1')

    client.put_telemetry_records(
        TelemetryRecords=[
            {
                'Timestamp': datetime.datetime(2015, 1, 1),
                'SegmentsReceivedCount': 123,
                'SegmentsSentCount': 123,
                'SegmentsSpilloverCount': 123,
                'SegmentsRejectedCount': 123,
                'BackendConnectionErrors': {
                    'TimeoutCount': 123,
                    'ConnectionRefusedCount': 123,
                    'HTTPCode4XXCount': 123,
                    'HTTPCode5XXCount': 123,
                    'UnknownHostCount': 123,
                    'OtherCount': 123
                }
            },
        ],
        EC2InstanceId='string',
        Hostname='string',
        ResourceARN='string'
    )


@mock_xray
def test_put_trace_segments():
    client = boto3.client('xray', region_name='us-east-1')

    client.put_trace_segments(
        TraceSegmentDocuments=[
            json.dumps({
                'name': 'example.com',
                'id': '70de5b6f19ff9a0a',
                'start_time': 1.478293361271E9,
                'trace_id': '1-581cf771-a006649127e371903a2de979',
                'end_time': 1.478293361449E9
            })
        ]
    )


@mock_xray
def test_trace_summary():
    client = boto3.client('xray', region_name='us-east-1')

    client.put_trace_segments(
        TraceSegmentDocuments=[
            json.dumps({
                'name': 'example.com',
                'id': '70de5b6f19ff9a0a',
                'start_time': 1.478293361271E9,
                'trace_id': '1-581cf771-a006649127e371903a2de979',
                'in_progress': True
            }),
            json.dumps({
                'name': 'example.com',
                'id': '70de5b6f19ff9a0b',
                'start_time': 1478293365,
                'trace_id': '1-581cf771-a006649127e371903a2de979',
                'end_time': 1478293385
            })
        ]
    )

    client.get_trace_summaries(
        StartTime=datetime.datetime(2014, 1, 1),
        EndTime=datetime.datetime(2017, 1, 1)
    )
