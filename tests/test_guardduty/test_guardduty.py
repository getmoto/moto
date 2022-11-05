import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_guardduty


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
    response.should.have.key("DetectorId")
    response["DetectorId"].shouldnt.equal(None)


@mock_guardduty
def test_create_detector_with_minimal_params():
    client = boto3.client("guardduty", region_name="us-east-1")
    response = client.create_detector(Enable=True)
    response.should.have.key("DetectorId")
    response["DetectorId"].shouldnt.equal(None)


@mock_guardduty
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
    resp.should.have.key("FindingPublishingFrequency").equals("ONE_HOUR")
    resp.should.have.key("DataSources")
    resp["DataSources"].should.have.key("S3Logs").equals({"Status": "ENABLED"})
    resp.should.have.key("CreatedAt")


@mock_guardduty
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
    resp.should.have.key("FindingPublishingFrequency").equals("ONE_HOUR")
    resp.should.have.key("DataSources")
    resp["DataSources"].should.have.key("S3Logs").equals({"Status": "ENABLED"})
    resp["DataSources"].should.have.key("Kubernetes")
    resp["DataSources"]["Kubernetes"].should.have.key("AuditLogs").equals(
        {"Status": "ENABLED"}
    )
    resp.should.have.key("CreatedAt")


@mock_guardduty
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
    resp.should.have.key("FindingPublishingFrequency").equals("SIX_HOURS")
    resp.should.have.key("DataSources")
    resp["DataSources"].should.have.key("S3Logs").equals({"Status": "ENABLED"})
    resp["DataSources"].should.have.key("Kubernetes")
    resp["DataSources"]["Kubernetes"].should.have.key("AuditLogs").equals(
        {"Status": "DISABLED"}
    )


@mock_guardduty
def test_list_detectors_initial():
    client = boto3.client("guardduty", region_name="us-east-1")

    response = client.list_detectors()
    response.should.have.key("DetectorIds").equals([])


@mock_guardduty
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
    response.should.have.key("DetectorIds")
    set(response["DetectorIds"]).should.equal({d1, d2})


@mock_guardduty
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
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.equal(
        "The request is rejected because the input detectorId is not owned by the current account."
    )

    client.list_detectors().should.have.key("DetectorIds").equals([])
