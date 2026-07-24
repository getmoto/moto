"""PaymentCryptographyControlPlaneBackend class with methods for supported APIs."""

import random
import string
from typing import Any, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.utils import unix_time
from moto.utilities.tagging_service import TaggingService

from .exceptions import ConflictException, ResourceNotFoundException


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
        tags: Optional[list[dict[str, str]]],
        derive_key_usage: Optional[str],
        replication_regions: Optional[list[str]],
    ) -> None:
        self.key_id = _random_key_id()
        self.key_arn = (
            f"arn:aws:payment-cryptography:{region_name}:{account_id}:key/{self.key_id}"
        )
        now = unix_time()
        self.key_attributes: Optional[dict[str, Any]] = key_attributes
        key_attributes_key_algorithm = (
            key_attributes.get("KeyAlgorithm") if key_attributes else None
        )

        self.key_check_value: str = _key_check_value()
        if key_check_value_algorithm:
            self.key_check_value_algorithm = key_check_value_algorithm
        else:
            self.key_check_value_algorithm = _key_check_value_algorithm(
                key_attributes_key_algorithm or ""
            )

        self.exportable = exportable
        self.enabled = enabled
        self.key_state = "CREATE_COMPLETE"

        # when a key is created, the origin is AWS_PAYMENT_CRYPTOGRAPHY.
        # If a key is imported, the origin is EXTERNAL.
        self.key_origin = "AWS_PAYMENT_CRYPTOGRAPHY"
        self.create_timestamp = now
        self.usage_start_timestamp: Optional[float] = now if enabled else None
        self.usage_stop_timestamp: Optional[float] = now if not enabled else None
        self.delete_pending_timestamp: Optional[float] = None
        self.delete_timestamp: Optional[float] = None
        self.derive_key_usage: Optional[str] = derive_key_usage

        self.multi_region_key_type: Optional[str] = None
        self.primary_region: Optional[str] = None
        self.replication_status: Optional[dict[str, dict[str, str]]] = None
        self.using_default_replication_regions: Optional[bool] = None

        if replication_regions is not None:
            self.primary_region = region_name
            self.multi_region_key_type = "PRIMARY"
            self.replication_status = {
                region: {"Status": "SYNCHRONIZED"} for region in replication_regions
            }
            self.using_default_replication_regions = False

        self.tags: list[dict[str, str]] = tags or []

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "KeyArn": self.key_arn,
            "KeyAttributes": self.key_attributes,
            "KeyCheckValue": self.key_check_value,
            "KeyCheckValueAlgorithm": self.key_check_value_algorithm,
            "Enabled": self.enabled,
            "Exportable": self.exportable,
            "KeyState": self.key_state,
            "KeyOrigin": self.key_origin,
            "CreateTimestamp": self.create_timestamp,
            "UsingDefaultReplicationRegions": self.using_default_replication_regions,
        }
        if self.derive_key_usage:
            result["DeriveKeyUsage"] = self.derive_key_usage
        if self.multi_region_key_type:
            result["MultiRegionKeyType"] = self.multi_region_key_type
        if self.primary_region:
            result["PrimaryRegion"] = self.primary_region
        if self.replication_status:
            result["ReplicationStatus"] = self.replication_status
        if self.usage_start_timestamp is not None:
            result["UsageStartTimestamp"] = self.usage_start_timestamp
        if self.usage_stop_timestamp is not None:
            result["UsageStopTimestamp"] = self.usage_stop_timestamp
        if self.delete_pending_timestamp is not None:
            result["DeletePendingTimestamp"] = self.delete_pending_timestamp
        if self.delete_timestamp is not None:
            result["DeleteTimestamp"] = self.delete_timestamp
        return result


class Alias(BaseModel):
    def __init__(self, alias_name: str, key_arn: Optional[str]):
        self.alias_name = alias_name
        self.key_arn = key_arn

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"AliasName": self.alias_name}
        if self.key_arn is not None:
            result["KeyArn"] = self.key_arn
        return result


class PaymentCryptographyControlPlaneBackend(BaseBackend):
    """Implementation of PaymentCryptographyControlPlane APIs."""

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.aliases: dict[str, Alias] = {}
        self.default_key_replication_regions: list[str] = []
        self.keys: dict[str, Key] = {}
        self.resource_policies: dict[str, str] = {}
        self.tagger = TaggingService(
            tag_name="Tags", key_name="Key", value_name="Value"
        )

    def create_key(
        self,
        key_attributes: Optional[dict[str, Any]],
        key_check_value_algorithm: Optional[str],
        enabled: bool,
        exportable: bool,
        tags: Optional[list[dict[str, str]]],
        derive_key_usage: Optional[str],
        replication_regions: Optional[list[str]],
    ) -> dict[str, Any]:
        tags = tags or []
        derive_key_usage = derive_key_usage or ""
        key = Key(
            account_id=self.account_id,
            region_name=self.region_name,
            key_attributes=key_attributes,
            key_check_value_algorithm=key_check_value_algorithm,  # TODO: match kcv to key_check_value_algorithm
            exportable=exportable,
            enabled=enabled,
            tags=tags,
            derive_key_usage=derive_key_usage,
            replication_regions=replication_regions,
        )

        self.keys[key.key_arn] = key

        if tags:
            self.tag_resource(resource_arn=key.key_arn, tags=tags)

        if replication_regions:
            self._create_replicas(key, replication_regions)

        return key.to_dict()

    def list_keys(
        self,
        key_state: Optional[str],
        next_token: Optional[str],
        max_results: Optional[int],
    ) -> tuple[list[dict[str, Any]], Optional[str]]:
        keys = list(self.keys.values())
        if key_state:
            keys = [key for key in keys if key.key_state == key_state]
        return [key.to_dict() for key in keys], next_token

    def list_tags_for_resource(
        self, resource_arn: str, next_token: Optional[str], max_results: Optional[int]
    ) -> tuple[list[dict[str, str]], Optional[str]]:
        tags = self.tagger.list_tags_for_resource(resource_arn)["Tags"]
        return tags, next_token

    def tag_resource(self, resource_arn: str, tags: list[dict[str, str]]) -> None:
        self.tagger.tag_resource(resource_arn, tags)

    def get_key(self, key_identifier: str) -> dict[str, Any]:
        if key_identifier not in self.keys:
            raise ResourceNotFoundException(key_identifier)

        key = self.keys.get(key_identifier)
        if key is None:
            raise ResourceNotFoundException(key_identifier)
        return key.to_dict()

    def untag_resource(self, resource_arn: str, tag_keys: list[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def delete_key(
        self, key_identifier: str, delete_key_in_days: Optional[int]
    ) -> dict[str, Any]:
        if key_identifier not in self.keys:
            raise ResourceNotFoundException(key_identifier)

        key = self.keys[key_identifier]
        days = delete_key_in_days if delete_key_in_days is not None else 7
        key.key_state = "DELETE_PENDING"
        key.enabled = False
        key.usage_stop_timestamp = unix_time()
        key.delete_pending_timestamp = unix_time() + days * 86400
        return key.to_dict()

    def put_resource_policy(self, resource_arn: str, policy: str) -> dict[str, Any]:
        if resource_arn not in self.keys:
            raise ResourceNotFoundException(resource_arn)
        self.resource_policies[resource_arn] = policy
        return {
            "Policy": policy,
            "ResourceArn": resource_arn,
        }

    def get_resource_policy(self, resource_arn: str) -> dict[str, Any]:
        if resource_arn not in self.keys:
            raise ResourceNotFoundException(resource_arn)
        return {
            "Policy": self.resource_policies.get(resource_arn, "{}"),
            "ResourceArn": resource_arn,
        }

    def delete_resource_policy(self, resource_arn: str) -> None:
        if resource_arn not in self.keys:
            raise ResourceNotFoundException(resource_arn)
        self.resource_policies.pop(resource_arn, None)

    def _create_replicas(self, key: "Key", replication_regions: list[str]) -> None:
        if key.replication_status is None:
            key.replication_status = {}

        for region in replication_regions:
            if key.replication_status is None:
                key.replication_status = {}
            if region not in key.replication_status:
                key.replication_status[region] = {"Status": "SYNCHRONIZED"}

            replica_backend = paymentcryptography_backends[self.account_id][region]
            replica_key = Key(
                account_id=self.account_id,
                region_name=region,
                key_attributes=key.key_attributes,
                key_check_value_algorithm=key.key_check_value_algorithm,
                exportable=key.exportable,
                enabled=key.enabled,
                tags=key.tags,
                derive_key_usage=key.derive_key_usage,
                replication_regions=None,
            )
            replica_key.key_id = key.key_id
            replica_key.key_arn = f"arn:aws:payment-cryptography:{region}:{self.account_id}:key/{key.key_id}"
            replica_key.key_check_value = key.key_check_value
            replica_key.multi_region_key_type = "REPLICA"
            replica_key.primary_region = key.primary_region
            replica_key.replication_status = None
            replica_key.using_default_replication_regions = None
            replica_backend.keys[replica_key.key_arn] = replica_key

    def add_key_replication_regions(
        self, key_identifier: str, replication_regions: list[str]
    ) -> dict[str, Any]:
        if key_identifier not in self.keys:
            raise ResourceNotFoundException(key_identifier)

        key = self.keys[key_identifier]

        if key.multi_region_key_type is None:
            key.multi_region_key_type = "PRIMARY"
            key.primary_region = self.region_name
            key.replication_status = {}
            key.using_default_replication_regions = False

        self._create_replicas(key, replication_regions)
        return key.to_dict()

    def remove_key_replication_regions(
        self, key_identifier: str, replication_regions: list[str]
    ) -> dict[str, Any]:
        if key_identifier not in self.keys:
            raise ResourceNotFoundException(key_identifier)

        key = self.keys[key_identifier]

        for region in replication_regions:
            if key.replication_status:
                key.replication_status.pop(region, None)
            replica_backend = paymentcryptography_backends[self.account_id][region]
            replica_arn = f"arn:aws:payment-cryptography:{region}:{self.account_id}:key/{key.key_id}"
            replica_backend.keys.pop(replica_arn, None)

        if not key.replication_status:
            key.multi_region_key_type = None
            key.primary_region = None
            key.replication_status = None
            key.using_default_replication_regions = None

        return key.to_dict()

    def enable_default_key_replication_regions(
        self, replication_regions: list[str]
    ) -> list[str]:
        for region in replication_regions:
            if region not in self.default_key_replication_regions:
                self.default_key_replication_regions.append(region)

        return self.default_key_replication_regions

    def get_default_key_replication_regions(self) -> list[str]:
        return self.default_key_replication_regions

    def disable_default_key_replication_regions(
        self, replication_regions: list[str]
    ) -> list[str]:
        for region in replication_regions:
            if region in self.default_key_replication_regions:
                self.default_key_replication_regions.remove(region)
        return self.default_key_replication_regions

    def create_alias(self, alias_name: str, key_arn: Optional[str]) -> dict[str, Any]:
        if alias_name in self.aliases:
            raise ConflictException(f"Alias {alias_name} already exists")
        if key_arn is not None and key_arn not in self.keys:
            raise ResourceNotFoundException(key_arn)
        alias = Alias(alias_name=alias_name, key_arn=key_arn)
        self.aliases[alias_name] = alias
        return alias.to_dict()

    def get_alias(self, alias_name: str) -> dict[str, Any]:
        if alias_name not in self.aliases:
            raise ResourceNotFoundException(alias_name)
        return self.aliases[alias_name].to_dict()

    def list_aliases(
        self,
        key_arn: Optional[str],
        next_token: Optional[str],
        max_results: Optional[int],
    ) -> tuple[list[dict[str, Any]], Optional[str]]:
        aliases = list(self.aliases.values())
        if key_arn is not None:
            aliases = [alias for alias in aliases if alias.key_arn == key_arn]
        return [alias.to_dict() for alias in aliases], next_token

    def update_alias(self, alias_name: str, key_arn: Optional[str]) -> dict[str, Any]:
        if alias_name not in self.aliases:
            raise ResourceNotFoundException(alias_name)
        if key_arn is not None and key_arn not in self.keys:
            raise ResourceNotFoundException(key_arn)
        self.aliases[alias_name].key_arn = key_arn
        return self.aliases[alias_name].to_dict()

    def delete_alias(self, alias_name: str) -> None:
        if alias_name not in self.aliases:
            raise ResourceNotFoundException(alias_name)
        del self.aliases[alias_name]

    def start_key_usage(self, key_identifier: str) -> dict[str, Any]:
        if key_identifier not in self.keys:
            raise ResourceNotFoundException(key_identifier)
        key = self.keys[key_identifier]
        if not key.enabled:
            key.enabled = True
            key.usage_start_timestamp = unix_time()
        return key.to_dict()

    def stop_key_usage(self, key_identifier: str) -> dict[str, Any]:
        if key_identifier not in self.keys:
            raise ResourceNotFoundException(key_identifier)
        key = self.keys[key_identifier]
        if key.enabled:
            key.enabled = False
            key.usage_stop_timestamp = unix_time()
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
        "af-south-1",
    ],
)
