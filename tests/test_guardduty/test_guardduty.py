import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_detector():
    client = boto3.client("guardduty", region_name="us-east-1")
    response = client.create_detector(
        Enable=True,
        ClientToken="745645734574758463758",
        FindingPublishingFrequency="ONE_HOUR",
        DataSources={"S3Logs": {"Enable": True}},
        Tags={},
    )
    assert "DetectorId" in response
    assert response["DetectorId"] is not None


@mock_aws
def test_create_detector_with_minimal_params():
    client = boto3.client("guardduty", region_name="us-east-1")
    response = client.create_detector(Enable=True)
    assert "DetectorId" in response
    assert response["DetectorId"] is not None


@mock_aws
def test_get_detector_with_s3():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(
        Enable=True,
        ClientToken="745645734574758463758",
        FindingPublishingFrequency="ONE_HOUR",
        DataSources={"S3Logs": {"Enable": True}},
        Tags={},
    )["DetectorId"]

    resp = client.get_detector(DetectorId=detector_id)
    assert resp["FindingPublishingFrequency"] == "ONE_HOUR"
    assert resp["DataSources"]["S3Logs"] == {"Status": "ENABLED"}
    assert "CreatedAt" in resp


@mock_aws
def test_get_detector_with_all_data_sources():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(
        Enable=True,
        ClientToken="745645734574758463758",
        FindingPublishingFrequency="ONE_HOUR",
        DataSources={
            "S3Logs": {"Enable": True},
            "Kubernetes": {"AuditLogs": {"Enable": True}},
        },
        Tags={},
    )["DetectorId"]

    resp = client.get_detector(DetectorId=detector_id)
    assert resp["FindingPublishingFrequency"] == "ONE_HOUR"
    assert resp["DataSources"]["S3Logs"] == {"Status": "ENABLED"}
    assert resp["DataSources"]["Kubernetes"]["AuditLogs"] == {"Status": "ENABLED"}
    assert "CreatedAt" in resp


@mock_aws
def test_update_detector():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(
        Enable=True,
        ClientToken="745645734574758463758",
        FindingPublishingFrequency="ONE_HOUR",
        Tags={},
    )["DetectorId"]

    client.update_detector(
        DetectorId=detector_id,
        Enable=False,
        FindingPublishingFrequency="SIX_HOURS",
        DataSources={
            "S3Logs": {"Enable": True},
            "Kubernetes": {"AuditLogs": {"Enable": False}},
        },
    )

    resp = client.get_detector(DetectorId=detector_id)
    assert resp["FindingPublishingFrequency"] == "SIX_HOURS"
    assert resp["DataSources"]["S3Logs"] == {"Status": "ENABLED"}
    assert resp["DataSources"]["Kubernetes"]["AuditLogs"] == {"Status": "DISABLED"}


@mock_aws
def test_list_detectors_initial():
    client = boto3.client("guardduty", region_name="us-east-1")

    response = client.list_detectors()
    assert response["DetectorIds"] == []


@mock_aws
def test_list_detectors():
    client = boto3.client("guardduty", region_name="us-east-1")
    d1 = client.create_detector(
        Enable=True,
        ClientToken="745645734574758463758",
        FindingPublishingFrequency="ONE_HOUR",
        DataSources={"S3Logs": {"Enable": True}},
        Tags={},
    )["DetectorId"]
    d2 = client.create_detector(Enable=False)["DetectorId"]

    response = client.list_detectors()
    assert set(response["DetectorIds"]) == {d1, d2}


@mock_aws
def test_delete_detector():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(
        Enable=True,
        ClientToken="745645734574758463758",
        FindingPublishingFrequency="ONE_HOUR",
        DataSources={
            "S3Logs": {"Enable": True},
            "Kubernetes": {"AuditLogs": {"Enable": True}},
        },
        Tags={},
    )["DetectorId"]

    client.get_detector(DetectorId=detector_id)

    client.delete_detector(DetectorId=detector_id)

    with pytest.raises(ClientError) as exc:
        client.get_detector(DetectorId=detector_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert (
        err["Message"]
        == "The request is rejected because the input detectorId is not owned by the current account."
    )

    assert client.list_detectors()["DetectorIds"] == []
