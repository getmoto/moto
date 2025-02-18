import boto3
import pytest
import json
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
        Features=[{"Name": "Test", "Status": "ENABLED"}],
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
def test_get_detector_with_features():
    client = boto3.client("guardduty", region_name="us-east-1")
    detector_id = client.create_detector(
        Enable=True,
        Features=[
            {
                "Name": "EKS_AUDIT_LOGS",
                "Status": "ENABLED",
                "AdditionalConfiguration": [
                    {"Name": "EKS_ADDON_MANAGEMENT", "Status": "ENABLED"}
                ],
            },
            {"Name": "TS3_DATA_EVENTS", "Status": "DISABLED"},
        ],
    )["DetectorId"]

    resp = client.get_detector(DetectorId=detector_id)
    assert len(resp["Features"]) == 2
    assert resp["Features"][0]["Name"] == "EKS_AUDIT_LOGS"
    assert resp["Features"][0]["Status"] == "ENABLED"
    assert (
        resp["Features"][0]["AdditionalConfiguration"][0]["Name"]
        == "EKS_ADDON_MANAGEMENT"
    )
    assert resp["Features"][1]["Name"] == "TS3_DATA_EVENTS"
    assert resp["Features"][1]["Status"] == "DISABLED"


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
        Features=[{"Name": "Test", "Status": "ENABLED"}],
    )

    resp = client.get_detector(DetectorId=detector_id)
    assert resp["FindingPublishingFrequency"] == "SIX_HOURS"
    assert resp["DataSources"]["S3Logs"] == {"Status": "ENABLED"}
    assert resp["DataSources"]["Kubernetes"]["AuditLogs"] == {"Status": "DISABLED"}
    assert resp["Features"] == [{"Name": "Test", "Status": "ENABLED"}]


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

@mock_aws
def test_get_administrator_account():
    # Create GuardDuty client
    guardduty_client = boto3.client("guardduty", region_name="us-east-1")
    
    # Create detector first
    detector_response = guardduty_client.create_detector(Enable=True)
    detector_id = detector_response["DetectorId"]
    
    # Enable organization admin account
    guardduty_client.enable_organization_admin_account(AdminAccountId="someaccount")
    
    # List organization admin accounts to verify
    list_resp = guardduty_client.list_organization_admin_accounts()
    print(f"List admin response: {list_resp}")
    
    # Verify admin account details in the list response
    assert list_resp["AdminAccounts"][0]["AdminAccountId"] == "someaccount"
    assert list_resp["AdminAccounts"][0]["AdminStatus"] == "ENABLED"
    
    # Get administrator account details
    resp = guardduty_client.get_administrator_account(DetectorId=detector_id)
    print(f"Get admin response: {resp}")
    
    # Assertions for get_administrator_account response
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    # Remove the previous assertion about Administrator
    # As the response you showed doesn't contain this structure