"""PaymentCryptographyControlPlaneBackend class with methods for supported APIs."""

import random
import string
from moto.core.utils import unix_time
from typing import Any, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.utilities.tagging_service import TaggingService

from .exceptions import ResourceNotFoundException


def _random_key_id() -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=16))


def _key_check_value() -> str:
    # return a fake but plausible key check value based on the algorithm
    kcv = "".join(random.choices("0123456789ABCDEF", k=6))
    return kcv

def _key_check_value_algorithm(key_algorithm: str) -> str:
    # TDES keys use ANSI X9.24, AES keys use CMAC, HMAC keys use the HMAC hash,
    # and asymmetric (RSA/ECC) keys use SHA-1.
    if key_algorithm.startswith("TDES"):
        return "ANSI_X9_24"
    if key_algorithm.startswith("AES"):
        return "CMAC"
    if key_algorithm.startswith("HMAC"):
        return "HMAC"
    return "SHA_1"


class Key(BaseModel):
    def __init__(
        self,
        account_id: str,
        region_name: str,
        key_attributes: Optional[dict[str, Any]],
        key_check_value_algorithm: Optional[str],
        enabled: bool,
        exportable: bool,
        tags: list[dict[str, str]],
        derive_key_usage: str,
        replication_regions: Optional[list[str]],
    ):
        self.key_id = _random_key_id()
        self.key_arn = (
            f"arn:aws:payment-cryptography:{region_name}:{account_id}:key/{self.key_id}"
        )
        now = unix_time()
        self.key_attributes = key_attributes
        key_attributes_key_algorithm = key_attributes.get("KeyAlgorithm")

        self.key_check_value = _key_check_value()
        if key_check_value_algorithm:
            self.key_check_value_algorithm = key_check_value_algorithm
        else:
            self.key_check_value_algorithm = _key_check_value_algorithm(key_attributes_key_algorithm)

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

        self.multi_region_key_type: Optional[str] = None
        self.primary_region: Optional[str] = None
        self.replication_status: Optional[dict] = None
        self.using_default_replication_regions: Optional[bool] = None

        if replication_regions is not None:
            self.primary_region = region_name
            self.multi_region_key_type = "PRIMARY"
            self.replication_status = {
                region: {"Status": "SYNCHRONIZED"} for region in replication_regions
            }
            self.using_default_replication_regions = False

        # TODO: add missing mpa details

        self.tags = tags or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "KeyArn": self.key_arn,
            "KeyAttributes": self.key_attributes,
            "KeyCheckValue": self.key_check_value,
            "KeyCheckValueAlgorithm": self.key_check_value_algorithm,
            "Enabled": self.enabled,
            "Exportable": self.exportable,
            "KeyState": self.key_state,
            "KeyOrigin": self.key_origin,
            "CreateTimestamp": self.create_timestamp,
            "DeriveKeyUsage": self.derive_key_usage,
            "MultiRegionKeyType": self.multi_region_key_type,
            "PrimaryRegion": self.primary_region,
            "ReplicationStatus": self.replication_status,
            "UsingDefaultReplicationRegions": self.using_default_replication_regions
        }


class PaymentCryptographyControlPlaneBackend(BaseBackend):
    """Implementation of PaymentCryptographyControlPlane APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.keys: dict[str, Key] = {}
        self.tagger = TaggingService(
            tag_name="Tags", key_name="Key", value_name="Value"
        )

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

        return key.to_dict()

    def list_keys(self, key_state, next_token, max_results):
        keys = list(self.keys.values())
        if key_state:
            keys = [key for key in keys if key.key_state == key_state]
        return [key.to_dict() for key in keys], next_token

    def list_tags_for_resource(self, resource_arn, next_token, max_results):
        tags = self.tagger.list_tags_for_resource(resource_arn)["Tags"]
        return tags, next_token

    def tag_resource(self, resource_arn, tags: list[dict[str, str]]):
        self.tagger.tag_resource(resource_arn, tags)

    def get_key(self, key_identifier):
        if key_identifier not in self.keys:
            raise ResourceNotFoundException(key_identifier)

        key = self.keys.get(key_identifier)
        return key.to_dict()


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
