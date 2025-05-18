"""Handles incoming connectcampaigns requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import ConnectCampaignServiceBackend, connectcampaigns_backends


class ConnectCampaignServiceResponse(BaseResponse):
    """Handler for ConnectCampaignService requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="connectcampaigns")

    @property
    def connectcampaigns_backend(self) -> ConnectCampaignServiceBackend:
        """Return backend instance specific for this region."""
        return connectcampaigns_backends[self.current_account][self.region]

    def create_campaign(self) -> str:
        params = json.loads(self.body)
        name = params.get("name")
        connect_instance_id = params.get("connectInstanceId")
        dialer_config = params.get("dialerConfig")
        outbound_call_config = params.get("outboundCallConfig")
        tags = params.get("tags", {})

        id, arn, tags = self.connectcampaigns_backend.create_campaign(
            name=name,
            connect_instance_id=connect_instance_id,
            dialer_config=dialer_config,
            outbound_call_config=outbound_call_config,
            tags=tags,
        )

        response = {"id": id, "arn": arn, "tags": tags}

        return json.dumps(response)

    def delete_campaign(self) -> str:
        id = self.path.split("/")[-1]

        self.connectcampaigns_backend.delete_campaign(
            id=id,
        )

        return "{}"

    def describe_campaign(self) -> str:
        id = self.path.split("/")[-1]

        campaign_details = self.connectcampaigns_backend.describe_campaign(
            id=id,
        )

        response = {"campaign": campaign_details}

        return json.dumps(response)

    def get_connect_instance_config(self) -> str:
        connect_instance_id = self.path.split("/")[-2]

        connect_instance_config = (
            self.connectcampaigns_backend.get_connect_instance_config(
                connect_instance_id=connect_instance_id,
            )
        )

        response = {"connectInstanceConfig": connect_instance_config}

        return json.dumps(response)

    def start_instance_onboarding_job(self) -> str:
        connect_instance_id = self.path.split("/")[-2]

        params = json.loads(self.body) if self.body else {}
        encryption_config = params.get("encryptionConfig", {})

        job_status = self.connectcampaigns_backend.start_instance_onboarding_job(
            connect_instance_id=connect_instance_id,
            encryption_config=encryption_config,
        )

        response = {"connectInstanceOnboardingJobStatus": job_status}

        return json.dumps(response)
