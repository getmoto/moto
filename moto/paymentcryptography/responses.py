"""Handles incoming paymentcryptography requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import PaymentCryptographyControlPlaneBackend, paymentcryptography_backends


class PaymentCryptographyControlPlaneResponse(BaseResponse):
    """Handler for PaymentCryptographyControlPlane requests and responses."""

    def __init__(self):
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


        return json.dumps(dict(Key=key))

    def list_keys(self):
        key_state = self._get_param("KeyState")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")
        keys, next_token = self.paymentcryptography_backend.list_keys(
            key_state=key_state,
            next_token=next_token,
            max_results=max_results,
        )

        return json.dumps(dict(Keys=keys, NextToken=next_token))

    # add templates from here

    def list_tags_for_resource(self):
        params = self._get_params()
        resource_arn = self._get_param("ResourceArn")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")
        tags, next_token = self.paymentcryptography_backend.list_tags_for_resource(
            resource_arn=resource_arn,
            next_token=next_token,
            max_results=max_results,
        )
        # TODO: adjust response
        return json.dumps(dict(tags=tags, nextToken=next_token))

    def tag_resource(self):
        params = self._get_params()
        resource_arn = self._get_param("ResourceArn")
        tags = self._get_param("Tags")
        self.paymentcryptography_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict())

    def get_key(self):
        key_identifier = self._get_param("KeyIdentifier")
        key = self.paymentcryptography_backend.get_key(
            key_identifier=key_identifier,
        )
        return json.dumps(dict(Key=key))
