import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_guardduty


@mock_guardduty
def test_create_filter():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    resp = client.create_filter(
        DetectorId=detector_id,
        Name="my first filter",
        FindingCriteria={"Criterion": {"x": {"Eq": ["y"]}}},
    )
    resp.should.have.key("Name").equals("my first filter")


@mock_guardduty
def test_create_filter__defaults():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    client.create_filter(
        DetectorId=detector_id,
        Name="my first filter",
        FindingCriteria={"Criterion": {"x": {"Eq": ["y"]}}},
    )

    resp = client.get_filter(DetectorId=detector_id, FilterName="my first filter")
    resp.should.have.key("Rank").equals(1)


@mock_guardduty
def test_get_filter():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    client.create_filter(
        DetectorId=detector_id,
        Name="my first filter",
        FindingCriteria={"Criterion": {"x": {"Eq": ["y"]}}},
    )

    resp = client.get_filter(DetectorId=detector_id, FilterName="my first filter")
    resp.should.have.key("Name").equals("my first filter")
    resp.should.have.key("FindingCriteria").equals({"Criterion": {"x": {"Eq": ["y"]}}})


@mock_guardduty
def test_update_filter():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    client.create_filter(
        DetectorId=detector_id,
        Name="my first filter",
        FindingCriteria={"Criterion": {"x": {"Eq": ["y"]}}},
    )

    resp = client.update_filter(
        DetectorId=detector_id,
        FilterName="my first filter",
        Description="with desc",
        Rank=21,
        Action="NOOP",
    )
    resp.should.have.key("Name").equals("my first filter")

    resp = client.get_filter(DetectorId=detector_id, FilterName="my first filter")
    resp.should.have.key("Name").equals("my first filter")
    resp.should.have.key("Description").equals("with desc")
    resp.should.have.key("Rank").equals(21)
    resp.should.have.key("Action").equals("NOOP")
    resp.should.have.key("FindingCriteria").equals({"Criterion": {"x": {"Eq": ["y"]}}})


@mock_guardduty
def test_delete_filter():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    client.create_filter(
        DetectorId=detector_id,
        Name="my first filter",
        FindingCriteria={"Criterion": {"x": {"Eq": ["y"]}}},
    )

    client.delete_filter(DetectorId=detector_id, FilterName="my first filter")

    with pytest.raises(ClientError) as exc:
        client.get_filter(DetectorId=detector_id, FilterName="my first filter")
    err = exc.value.response["Error"]
    err["Code"].should.equal("BadRequestException")
