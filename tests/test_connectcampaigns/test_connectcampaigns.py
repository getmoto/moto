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


@mock_aws
def test_start_campaign():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    create_response = client.create_campaign(
        name="CampaignToStart",
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

    client.start_campaign(id=campaign_id)
    describe_response = client.get_campaign_state(id=campaign_id)

    assert describe_response["state"] == "Running"


@mock_aws
def test_stop_campaign():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    create_response = client.create_campaign(
        name="CampaignToStop",
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

    client.stop_campaign(id=campaign_id)
    describe_response = client.get_campaign_state(id=campaign_id)

    assert describe_response["state"] == "Stopped"


@mock_aws
def test_list_campaigns():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    # Create a couple of campaigns
    client.create_campaign(
        name="Campaign1",
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

    client.create_campaign(
        name="Campaign2",
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

    response = client.list_campaigns()

    assert len(response["campaignSummaryList"]) >= 2
    assert any(c["name"] == "Campaign1" for c in response["campaignSummaryList"])
    assert any(c["name"] == "Campaign2" for c in response["campaignSummaryList"])


@mock_aws
def test_list_campaigns_with_filters():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    # Create a couple of campaigns
    client.create_campaign(
        name="Campaign1",
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

    client.create_campaign(
        name="Campaign2",
        connectInstanceId="12345678-1234-1234-1234-000000000000",
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

    # Filter by name
    response = client.list_campaigns(
        filters={
            "instanceIdFilter": {
                "value": "12345678-1234-1234-1234-123456789012",
                "operator": "Eq",
            }
        }
    )

    assert len(response["campaignSummaryList"]) == 1
    assert response["campaignSummaryList"][0]["name"] == "Campaign1"

    # Filter by connectInstanceId
    response = client.list_campaigns(
        filters={
            "instanceIdFilter": {
                "value": "12345678-1234-1234-1234-12340000012",
                "operator": "Eq",
            }
        }
    )
    assert len(response["campaignSummaryList"]) == 0


@mock_aws
def test_start_campaign_invalid_id():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.start_campaign(id="non-existent-id")


@mock_aws
def test_stop_campaign_invalid_id():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.stop_campaign(id="non-existent-id")


@mock_aws
def test_tag_resource():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    create_response = client.create_campaign(
        name="CampaignToTag",
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
        tags={"Environment": "TestLater", "Owner": "DevTeamLater"},
    )

    client.tag_resource(
        arn=create_response["arn"],
        tags={"Environment": "Test", "Owner": "DevTeam"},
    )

    # assert tag_response is None
    # Verify tags
    describe_tags = client.list_tags_for_resource(arn=create_response["arn"])
    assert "tags" in describe_tags

    tags = describe_tags["tags"]
    assert tags["Environment"] == "Test"
    assert tags["Owner"] == "DevTeam"


@mock_aws
def test_untag_resource():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    create_response = client.create_campaign(
        name="CampaignToUntag",
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
    client.tag_resource(
        arn=create_response["arn"],
        tags={"Environment": "Test", "Owner": "DevTeam"},
    )

    client.untag_resource(
        arn=create_response["arn"],
        tagKeys=["Environment"],
    )
    # Verify tags after untagging
    describe_response = client.describe_campaign(id=campaign_id)
    assert "tags" in describe_response["campaign"]
    tags = describe_response["campaign"]["tags"]
    assert "Environment" not in tags
    assert tags["Owner"] == "DevTeam"


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    create_response = client.create_campaign(
        name="CampaignToListTags",
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

    client.tag_resource(
        arn=create_response["arn"],
        tags={"Environment": "Test", "Owner": "DevTeam"},
    )

    tags_response = client.list_tags_for_resource(arn=create_response["arn"])

    assert len(tags_response) == 2
    assert tags_response["tags"]["Environment"] == "Test"
    assert tags_response["tags"]["Owner"] == "DevTeam"


@mock_aws
def test_get_campaign_state():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    create_response = client.create_campaign(
        name="CampaignStateTest",
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

    # Initially, the campaign state should be 'Initialized'
    state_response = client.get_campaign_state(id=campaign_id)
    assert state_response["state"] == "Initialized"

    # Start the campaign
    client.start_campaign(id=campaign_id)
    state_response = client.get_campaign_state(id=campaign_id)
    assert state_response["state"] == "Running"

    # Stop the campaign
    client.stop_campaign(id=campaign_id)
    state_response = client.get_campaign_state(id=campaign_id)
    assert state_response["state"] == "Stopped"


@mock_aws
def test_get_campaign_state_invalid_id():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.get_campaign_state(id="non-existent-id")


@mock_aws
def test_pause_campaign():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    create_response = client.create_campaign(
        name="CampaignToPause",
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

    # Start the campaign
    client.start_campaign(id=campaign_id)

    # Pause the campaign
    client.pause_campaign(id=campaign_id)
    state_response = client.get_campaign_state(id=campaign_id)

    assert state_response["state"] == "Paused"


@mock_aws
def test_resume_campaign():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    create_response = client.create_campaign(
        name="CampaignToResume",
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

    # Start the campaign
    client.start_campaign(id=campaign_id)

    # Pause the campaign
    client.pause_campaign(id=campaign_id)

    # Resume the campaign
    client.resume_campaign(id=campaign_id)
    state_response = client.get_campaign_state(id=campaign_id)

    assert state_response["state"] == "Running"


@mock_aws
def test_pause_campaign_invalid_id():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.pause_campaign(id="non-existent-id")


@mock_aws
def test_resume_campaign_invalid_id():
    client = boto3.client("connectcampaigns", region_name="us-east-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.resume_campaign(id="non-existent-id")
