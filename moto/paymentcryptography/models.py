"""PaymentCryptographyControlPlaneBackend class with methods for supported APIs."""

import random
import string
from moto.core.utils import unix_time
from typing import Any, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel


def _random_key_id() -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=16))


def _key_check_value() -> str:
    # return a fake but plausible key check value based on the algorithm
    kcv = "".join(random.choices("0123456789ABCDEF", k=6))
    return kcv


class Key(BaseModel):
    def __init__(
        self,
        account_id: str,
        region_name: str,
        key_attributes: Optional[dict[str, Any]],
        key_check_value_algorithm: str,
        enabled: bool,
        exportable: bool,
        tags: list[dict[str, str]],
        derive_key_usage: str,
        replication_regions: list[str],
    ):
        self.key_id = _random_key_id()
        self.key_arn = (
            f"arn:aws:payment-cryptography:{region_name}:{account_id}:key/{self.key_id}"
        )
        now = unix_time()
        self.key_attributes = key_attributes

        self.key_check_value = _key_check_value()
        self.key_check_value_algorithm = key_check_value_algorithm

        self.exportable = exportable
        self.enabled = enabled
        self.key_state = "CREATE_COMPLETE"

        # when a key is created, the origin is AWS_PAYMENT_CRYPTOGRAPHY.
        # If a key is imported, the origin is EXTERNAL.
        self.key_origin = "AWS_PAYMENT_CRYPTOGRAPHY"
        self.create_timestamp = now
        self.usage_start_timestamp = now if enabled else None
        self.usage_stop_timestamp = None
        self.delete_pending_timestamp = None
        self.delete_timestamp = None
        self.derive_key_usage = derive_key_usage

        if replication_regions is not None:
            self.multi_region_key_type = "PRIMARY"
            self.primary_region = region_name
            self.replication_status = dict()
            for region in replication_regions:
                self.replication_status[region] = {
                    "replication_status": "SYNCHRONIZED",
                    "status_message": "Key is synchronized across regions.",
                }
            self.using_default_replication_regions = False

        self.tags = tags or []


class PaymentCryptographyControlPlaneBackend(BaseBackend):
    """Implementation of PaymentCryptographyControlPlane APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.keys: dict[str, Key] = {}

    def create_key(
        self,
        key_attributes: Optional[dict[str, Any]],
        key_check_value_algorithm: str,
        enabled: bool,
        exportable: bool,
        tags: list[dict[str, str]],
        derive_key_usage: str,
        replication_regions: list[str],
    ) -> dict[str, Any]:

        key = Key(
            account_id=self.account_id,
            region_name=self.region_name,
            key_attributes=key_attributes,
            key_check_value_algorithm=key_check_value_algorithm, # TODO: match kcv to key_check_value_algorithm
            exportable=exportable,
            enabled=enabled,
            tags=tags,
            derive_key_usage=derive_key_usage,
            replication_regions=replication_regions,
        )

        self.keys[key.key_arn] = key

        if tags:
            self.tag_resource(resource_arn=key.key_arn, tags=tags)

        return {
            "KeyArn": key.key_arn,
            "KeyAttributes": key.key_attributes,
            "KeyCheckValue": key.key_check_value,
            "KeyCheckValueAlgorithm": key.key_check_value_algorithm,
            "Enabled": key.enabled,
            "Exportable": key.exportable,
            "KeyState": key.key_state,
            "KeyOrigin": key.key_origin,
            "CreateTimestamp": key.create_timestamp,
            "DeriveKeyUsage": key.derive_key_usage
        }
        return key_arn

    def list_keys(self, key_state, next_token, max_results):
        # implement here
        return keys, next_token

    def list_tags_for_resource(self, resource_arn, next_token, max_results):
        # implement here
        return tags, next_token

    def tag_resource(self, resource_arn, tags: list[dict[str, str]]):
        self.tagger.tag_resource(resource_arn, tags)


paymentcryptography_backends = BackendDict(
    PaymentCryptographyControlPlaneBackend,
    "payment-cryptography",
    additional_regions=[
        "us-east-1",
        "us-east-2",
        "us-west-2",
        "ca-central-1",
        "sa-east-1",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "eu-central-1",
        "ap-southeast-1",
        "ap-southeast-2",
        "ap-northeast-1",
        "ap-northeast-3",
        "ap-south-1",
        "ap-south-2",
        "af-south-1"
    ],
)
