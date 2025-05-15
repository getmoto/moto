"""Unit tests for connectcampaigns-supported APIs."""

import boto3
import pytest

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_campaign():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    response = client.create_campaign(
        name="TestCampaign",
        connectInstanceId="12345678-1234-1234-1234-123456789012",
        dialerConfig={
            "progressiveDialerConfig": {
                "bandwidthAllocation": 1.0,
                "dialingCapacity": 2.0,
            }
        },
        outboundCallConfig={
            "connectContactFlowId": "12345678-1234-1234-1234-123456789012",
            "connectSourcePhoneNumber": "+12065550100",
            "connectQueueId": "12345678-1234-1234-1234-123456789012",
            "answerMachineDetectionConfig": {
                "enableAnswerMachineDetection": True,
                "awaitAnswerMachinePrompt": False,
            },
        },
        tags={"Department": "Marketing", "Project": "Outreach"},
    )

    assert "id" in response
    assert "arn" in response
    assert "tags" in response
    assert response["tags"]["Department"] == "Marketing"
    assert response["tags"]["Project"] == "Outreach"


@mock_aws
def test_delete_campaign():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    create_response = client.create_campaign(
        name="CampaignToDelete",
        connectInstanceId="12345678-1234-1234-1234-123456789012",
        dialerConfig={
            "progressiveDialerConfig": {
                "bandwidthAllocation": 1.0,
                "dialingCapacity": 2.0,
            }
        },
        outboundCallConfig={
            "connectContactFlowId": "12345678-1234-1234-1234-123456789012",
        },
    )

    campaign_id = create_response["id"]

    client.delete_campaign(id=campaign_id)


@mock_aws
def test_describe_campaign():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    create_response = client.create_campaign(
        name="CampaignToDescribe",
        connectInstanceId="12345678-1234-1234-1234-123456789012",
        dialerConfig={
            "progressiveDialerConfig": {
                "bandwidthAllocation": 1.0,
                "dialingCapacity": 2.0,
            }
        },
        outboundCallConfig={
            "connectContactFlowId": "12345678-1234-1234-1234-123456789012",
            "connectSourcePhoneNumber": "+12065550100",
            "connectQueueId": "12345678-1234-1234-1234-123456789012",
        },
    )

    campaign_id = create_response["id"]

    describe_response = client.describe_campaign(id=campaign_id)

    assert "campaign" in describe_response
    campaign = describe_response["campaign"]

    assert campaign["id"] == campaign_id
    assert "arn" in campaign
    assert campaign["name"] == "CampaignToDescribe"
    assert campaign["connectInstanceId"] == "12345678-1234-1234-1234-123456789012"
    assert "progressiveDialerConfig" in campaign["dialerConfig"]
    assert (
        campaign["dialerConfig"]["progressiveDialerConfig"]["bandwidthAllocation"]
        == 1.0
    )
    assert (
        campaign["outboundCallConfig"]["connectContactFlowId"]
        == "12345678-1234-1234-1234-123456789012"
    )

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.describe_campaign(id="non-existent-id")


@mock_aws
def test_get_connect_instance_config():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    connect_instance_id = "12345678-1234-1234-1234-123456789012"

    response = client.get_connect_instance_config(connectInstanceId=connect_instance_id)

    assert "connectInstanceConfig" in response
    config = response["connectInstanceConfig"]

    assert config["connectInstanceId"] == connect_instance_id
    assert "serviceLinkedRoleArn" in config
    assert "encryptionConfig" in config
    assert "enabled" in config["encryptionConfig"]
    assert "encryptionType" in config["encryptionConfig"]
    assert config["encryptionConfig"]["encryptionType"] == "KMS"

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.get_connect_instance_config(connectInstanceId="invalid-id")


@mock_aws
def test_start_instance_onboarding_job():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    connect_instance_id = "12345678-1234-1234-1234-123456789012"

    response = client.start_instance_onboarding_job(
        connectInstanceId=connect_instance_id,
        encryptionConfig={"enabled": False, "encryptionType": "KMS"},
    )

    assert "connectInstanceOnboardingJobStatus" in response
    job_status = response["connectInstanceOnboardingJobStatus"]

    assert job_status["connectInstanceId"] == connect_instance_id
    assert job_status["status"] == "SUCCEEDED"
    assert "failureCode" not in job_status

    response = client.start_instance_onboarding_job(
        connectInstanceId=connect_instance_id,
        encryptionConfig={
            "enabled": True,
            "encryptionType": "KMS",
            "keyArn": "arn:aws:kms:us-east-1:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab",
        },
    )

    assert "connectInstanceOnboardingJobStatus" in response
    job_status = response["connectInstanceOnboardingJobStatus"]

    assert job_status["connectInstanceId"] == connect_instance_id
    assert job_status["status"] == "SUCCEEDED"

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.start_instance_onboarding_job(
            connectInstanceId="invalid-id",
            encryptionConfig={"enabled": False, "encryptionType": "KMS"},
        )

    with pytest.raises(client.exceptions.ValidationException):
        client.start_instance_onboarding_job(
            connectInstanceId=connect_instance_id,
            encryptionConfig={"enabled": True, "encryptionType": "KMS"},
        )
