import boto3
import sure  # noqa # pylint: disable=unused-import

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
