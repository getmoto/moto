from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_guardduty
import pytest


@mock_guardduty
def test_create_detector():
    client = boto3.client("guardduty", region_name="us-east-1")
    response = client.create_detector(
        Enable=True,
        ClientToken="745645734574758463758",
        FindingPublishingFrequency="ONE_HOUR",
        DataSources={"S3Logs": {"Enable": True}},
        Tags={},
    )
    assert response["DetectorId"] != None


@mock_guardduty
def test_list_detectors():
    client = boto3.client("guardduty", region_name="us-east-1")
    response = client.create_detector(
        Enable=True,
        ClientToken="745645734574758463758",
        FindingPublishingFrequency="ONE_HOUR",
        DataSources={"S3Logs": {"Enable": True}},
        Tags={},
    )
    response = client.list_detectors(MaxResults=1, NextToken="")
    assert response != None
