import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_filter():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    resp = client.create_filter(
        DetectorId=detector_id,
        Name="my first filter",
        FindingCriteria={"Criterion": {"x": {"Eq": ["y"]}}},
    )
    assert resp["Name"] == "my first filter"


@mock_aws
def test_create_filter__defaults():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    client.create_filter(
        DetectorId=detector_id,
        Name="my first filter",
        FindingCriteria={"Criterion": {"x": {"Eq": ["y"]}}},
    )

    resp = client.get_filter(DetectorId=detector_id, FilterName="my first filter")
    assert resp["Rank"] == 1


@mock_aws
def test_get_filter():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(Enable=True)["DetectorId"]

    client.create_filter(
        DetectorId=detector_id,
        Name="my first filter",
        FindingCriteria={"Criterion": {"x": {"Eq": ["y"]}}},
    )

    resp = client.get_filter(DetectorId=detector_id, FilterName="my first filter")
    assert resp["Name"] == "my first filter"
    assert resp["FindingCriteria"] == {"Criterion": {"x": {"Eq": ["y"]}}}


@mock_aws
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
    assert resp["Name"] == "my first filter"

    resp = client.get_filter(DetectorId=detector_id, FilterName="my first filter")
    assert resp["Name"] == "my first filter"
    assert resp["Description"] == "with desc"
    assert resp["Rank"] == 21
    assert resp["Action"] == "NOOP"
    assert resp["FindingCriteria"] == {"Criterion": {"x": {"Eq": ["y"]}}}


@mock_aws
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
    assert err["Code"] == "BadRequestException"
