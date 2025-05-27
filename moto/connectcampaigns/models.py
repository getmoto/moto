"""ConnectCampaignServiceBackend class with methods for supported APIs."""

import uuid
from typing import Any, Dict, Optional, Tuple

from moto.core import DEFAULT_ACCOUNT_ID
from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel

from .exceptions import ResourceNotFoundException, ValidationException


class ConnectCampaign(BaseModel):
    def __init__(
        self,
        name: str,
        connect_instance_id: str,
        dialer_config: Dict[str, Any],
        outbound_call_config: Dict[str, Any],
        region: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.name = name
        self.connect_instance_id = connect_instance_id
        self.dialer_config = dialer_config
        self.outbound_call_config = outbound_call_config
        self.region = region
        self.tags = tags or {}
        self.arn = f"arn:aws:connectcampaigns:{self.region}:{DEFAULT_ACCOUNT_ID}:campaign/{self.id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "arn": self.arn,
            "name": self.name,
            "connectInstanceId": self.connect_instance_id,
            "dialerConfig": self.dialer_config,
            "outboundCallConfig": self.outbound_call_config,
            "tags": self.tags,
        }


class ConnectInstanceConfig(BaseModel):
    def __init__(
        self, connect_instance_id: str, region: str, encryption_enabled: bool = False
    ) -> None:
        self.connect_instance_id = connect_instance_id
        self.region = region
        self.service_linked_role_arn = f"arn:aws:iam::{DEFAULT_ACCOUNT_ID}:role/aws-service-role/connectcampaigns.amazonaws.com/AWSServiceRoleForConnectCampaigns"

        self.encryption_config = {
            "enabled": encryption_enabled,
            "encryptionType": "KMS",
        }

        if encryption_enabled:
            self.encryption_config["keyArn"] = (
                f"arn:aws:kms:{region}:{DEFAULT_ACCOUNT_ID}:key/1234abcd-12ab-34cd-56ef-1234567890ab"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connectInstanceId": self.connect_instance_id,
            "serviceLinkedRoleArn": self.service_linked_role_arn,
            "encryptionConfig": self.encryption_config,
        }


class ConnectInstanceOnboardingJobStatus(BaseModel):
    def __init__(
        self,
        connect_instance_id: str,
        status: str = "SUCCEEDED",
        failure_code: Optional[str] = None,
    ) -> None:
        self.connect_instance_id = connect_instance_id
        self.status = status
        self.failure_code = failure_code

    def to_dict(self) -> Dict[str, Any]:
        result = {"connectInstanceId": self.connect_instance_id, "status": self.status}

        if self.failure_code and self.status == "FAILED":
            result["failureCode"] = self.failure_code

        return result


class ConnectCampaignServiceBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.campaigns: Dict[str, ConnectCampaign] = {}
        self.instance_configs: Dict[str, ConnectInstanceConfig] = {}
        self.onboarding_jobs: Dict[str, ConnectInstanceOnboardingJobStatus] = {}

    def create_campaign(
        self,
        name: str,
        connect_instance_id: str,
        dialer_config: Dict[str, Any],
        outbound_call_config: Dict[str, Any],
        tags: Optional[Dict[str, str]],
    ) -> Tuple[str, str, Dict[str, str]]:
        campaign = ConnectCampaign(
            name=name,
            connect_instance_id=connect_instance_id,
            dialer_config=dialer_config,
            outbound_call_config=outbound_call_config,
            region=self.region_name,
            tags=tags,
        )
        self.campaigns[campaign.id] = campaign
        return campaign.id, campaign.arn, campaign.tags

    def delete_campaign(self, id: str) -> None:
        del self.campaigns[id]

    def describe_campaign(self, id: str) -> Dict[str, Any]:
        if id not in self.campaigns:
            raise ResourceNotFoundException(f"Campaign with id {id} not found")

        campaign = self.campaigns[id]
        return campaign.to_dict()

    def get_connect_instance_config(self, connect_instance_id: str) -> Dict[str, Any]:
        if not connect_instance_id:
            raise ValidationException("connectInstanceId is a required parameter")

        if connect_instance_id == "invalid-id":
            raise ResourceNotFoundException(
                f"Connect instance with id {connect_instance_id} not found"
            )

        if connect_instance_id in self.instance_configs:
            return self.instance_configs[connect_instance_id].to_dict()

        instance_config = ConnectInstanceConfig(
            connect_instance_id=connect_instance_id, region=self.region_name
        )
        self.instance_configs[connect_instance_id] = instance_config

        return instance_config.to_dict()

    def start_instance_onboarding_job(
        self, connect_instance_id: str, encryption_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not connect_instance_id:
            raise ValidationException("connectInstanceId is a required parameter")

        if connect_instance_id == "invalid-id":
            raise ResourceNotFoundException(
                f"Connect instance with id {connect_instance_id} not found"
            )

        if not encryption_config:
            raise ValidationException("encryptionConfig is a required parameter")

        if "enabled" not in encryption_config:
            raise ValidationException(
                "enabled is a required parameter in encryptionConfig"
            )

        if encryption_config.get("enabled") and "keyArn" not in encryption_config:
            raise ValidationException("keyArn is required when encryption is enabled")

        job_status = ConnectInstanceOnboardingJobStatus(
            connect_instance_id=connect_instance_id
        )

        self.onboarding_jobs[connect_instance_id] = job_status

        instance_config = ConnectInstanceConfig(
            connect_instance_id=connect_instance_id,
            region=self.region_name,
            encryption_enabled=encryption_config.get("enabled", False),
        )

        if encryption_config.get("enabled") and "keyArn" in encryption_config:
            instance_config.encryption_config["keyArn"] = encryption_config["keyArn"]

        self.instance_configs[connect_instance_id] = instance_config

        return job_status.to_dict()


connectcampaigns_backends = BackendDict(
    ConnectCampaignServiceBackend, "connectcampaigns"
)
