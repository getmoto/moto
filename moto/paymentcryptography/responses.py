"""Handles incoming paymentcryptography requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import PaymentCryptographyControlPlaneBackend, paymentcryptography_backends


class PaymentCryptographyControlPlaneResponse(BaseResponse):
    """Handler for PaymentCryptographyControlPlane requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="payment-cryptography")

    @property
    def paymentcryptography_backend(self) -> PaymentCryptographyControlPlaneBackend:
        """Return backend instance specific for this region."""
        return paymentcryptography_backends[self.current_account][self.region]

    def create_key(self) -> str:
        key_attributes = self._get_param("KeyAttributes")
        key_check_value_algorithm = self._get_param("KeyCheckValueAlgorithm")
        exportable = self._get_param("Exportable")
        enabled = self._get_param("Enabled")
        tags = self._get_param("Tags")
        derive_key_usage = self._get_param("DeriveKeyUsage")
        replication_regions = self._get_param("ReplicationRegions")
        key = self.paymentcryptography_backend.create_key(
            key_attributes=key_attributes,
            key_check_value_algorithm=key_check_value_algorithm,
            exportable=exportable,
            enabled=enabled,
            tags=tags,
            derive_key_usage=derive_key_usage,
            replication_regions=replication_regions,
        )

        return json.dumps({"Key": key})

    def list_keys(self) -> str:
        key_state = self._get_param("KeyState")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")
        keys, next_token = self.paymentcryptography_backend.list_keys(
            key_state=key_state,
            next_token=next_token,
            max_results=max_results,
        )

        return json.dumps({"Keys": keys, "NextToken": next_token})

    # add templates from here

    def list_tags_for_resource(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")
        tags, next_token = self.paymentcryptography_backend.list_tags_for_resource(
            resource_arn=resource_arn,
            next_token=next_token,
            max_results=max_results,
        )
        return json.dumps({"Tags": tags, "NextToken": next_token})

    def tag_resource(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        tags = self._get_param("Tags")
        self.paymentcryptography_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        return json.dumps({})

    def get_key(self) -> str:
        key_identifier = self._get_param("KeyIdentifier")
        key = self.paymentcryptography_backend.get_key(
            key_identifier=key_identifier,
        )
        return json.dumps({"Key": key})

    def untag_resource(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        tag_keys = self._get_param("TagKeys")
        self.paymentcryptography_backend.untag_resource(
            resource_arn=resource_arn,
            tag_keys=tag_keys,
        )

        return json.dumps({})

    def delete_key(self) -> str:
        key_identifier = self._get_param("KeyIdentifier")
        delete_key_in_days = self._get_param("DeleteKeyInDays")
        key = self.paymentcryptography_backend.delete_key(
            key_identifier=key_identifier,
            delete_key_in_days=delete_key_in_days,
        )
        return json.dumps({"Key": key})

    def put_resource_policy(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        policy = self._get_param("Policy")
        result = self.paymentcryptography_backend.put_resource_policy(
            resource_arn=resource_arn,
            policy=policy,
        )
        return json.dumps(result)

    def get_resource_policy(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        policy = self.paymentcryptography_backend.get_resource_policy(
            resource_arn=resource_arn,
        )
        return json.dumps(policy)

    def delete_resource_policy(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        self.paymentcryptography_backend.delete_resource_policy(
            resource_arn=resource_arn,
        )
        return json.dumps({})

    def add_key_replication_regions(self) -> str:
        key_identifier = self._get_param("KeyIdentifier")
        replication_regions = self._get_param("ReplicationRegions")
        key = self.paymentcryptography_backend.add_key_replication_regions(
            key_identifier=key_identifier,
            replication_regions=replication_regions,
        )

        return json.dumps({"Key": key})

    def enable_default_key_replication_regions(self) -> str:
        replication_regions = self._get_param("ReplicationRegions")
        enabled_replication_regions = (
            self.paymentcryptography_backend.enable_default_key_replication_regions(
                replication_regions=replication_regions,
            )
        )
        return json.dumps({"EnabledReplicationRegions": enabled_replication_regions})

    def get_default_key_replication_regions(self) -> str:
        get_replication_regions = (
            self.paymentcryptography_backend.get_default_key_replication_regions()
        )
        return json.dumps({"EnabledReplicationRegions": get_replication_regions})

    def disable_default_key_replication_regions(self) -> str:
        replication_regions = self._get_param("ReplicationRegions")
        enabled_replication_regions = (
            self.paymentcryptography_backend.disable_default_key_replication_regions(
                replication_regions=replication_regions,
            )
        )
        return json.dumps({"EnabledReplicationRegions": enabled_replication_regions})

    def create_alias(self) -> str:
        alias_name = self._get_param("AliasName")
        key_arn = self._get_param("KeyArn")
        alias = self.paymentcryptography_backend.create_alias(
            alias_name=alias_name,
            key_arn=key_arn,
        )
        return json.dumps({"Alias": alias})

    def get_alias(self) -> str:
        alias_name = self._get_param("AliasName")
        alias = self.paymentcryptography_backend.get_alias(
            alias_name=alias_name,
        )

        return json.dumps({"Alias": alias})

    def list_aliases(self) -> str:
        key_arn = self._get_param("KeyArn")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")
        aliases, next_token = self.paymentcryptography_backend.list_aliases(
            key_arn=key_arn,
            next_token=next_token,
            max_results=max_results,
        )

        return json.dumps({"Aliases": aliases, "NextToken": next_token})

    def update_alias(self) -> str:
        alias_name = self._get_param("AliasName")
        key_arn = self._get_param("KeyArn")
        alias = self.paymentcryptography_backend.update_alias(
            alias_name=alias_name,
            key_arn=key_arn,
        )

        return json.dumps({"Alias": alias})

    def delete_alias(self) -> str:
        alias_name = self._get_param("AliasName")
        self.paymentcryptography_backend.delete_alias(
            alias_name=alias_name,
        )
        return json.dumps({})

    def start_key_usage(self) -> str:
        key_identifier = self._get_param("KeyIdentifier")
        key = self.paymentcryptography_backend.start_key_usage(
            key_identifier=key_identifier,
        )
        return json.dumps({"Key": key})

    def stop_key_usage(self) -> str:
        key_identifier = self._get_param("KeyIdentifier")
        key = self.paymentcryptography_backend.stop_key_usage(
            key_identifier=key_identifier,
        )
        return json.dumps({"Key": key})
