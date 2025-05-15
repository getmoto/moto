"""Handles incoming connectcampaigns requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .exceptions import ValidationException
from .models import connectcampaigns_backends


class ConnectCampaignServiceResponse(BaseResponse):
    """Handler for ConnectCampaignService requests and responses."""

    def __init__(self):
        super().__init__(service_name="connectcampaigns")

    @property
    def connectcampaigns_backend(self):
        return connectcampaigns_backends[self.current_account][self.region]

    def create_campaign(self):
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

    def delete_campaign(self):
        id = self.path.split("/")[-1]

        if not id:
            raise ValidationException("id is a required parameter")

        self.connectcampaigns_backend.delete_campaign(
            id=id,
        )

        return "{}"

    def describe_campaign(self):
        id = self.path.split("/")[-1]

        if not id:
            raise ValidationException("id is a required parameter")

        campaign_details = self.connectcampaigns_backend.describe_campaign(
            id=id,
        )

        response = {"campaign": campaign_details}

        return json.dumps(response)

    def get_connect_instance_config(self):
        connect_instance_id = self.path.split("/")[
            -2
        ]  # Format: /connect-instance/{connectInstanceId}/config

        if not connect_instance_id:
            raise ValidationException("connectInstanceId is a required parameter")

        connect_instance_config = (
            self.connectcampaigns_backend.get_connect_instance_config(
                connect_instance_id=connect_instance_id,
            )
        )

        response = {"connectInstanceConfig": connect_instance_config}

        return json.dumps(response)

    def start_instance_onboarding_job(self):
        connect_instance_id = self.path.split("/")[-2]

        params = json.loads(self.body) if self.body else {}
        encryption_config = params.get("encryptionConfig", {})

        if not connect_instance_id:
            raise ValidationException("connectInstanceId is a required parameter")

        job_status = self.connectcampaigns_backend.start_instance_onboarding_job(
            connect_instance_id=connect_instance_id,
            encryption_config=encryption_config,
        )

        response = {"connectInstanceOnboardingJobStatus": job_status}

        return json.dumps(response)
