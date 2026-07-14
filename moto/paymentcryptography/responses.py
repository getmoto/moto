"""Handles incoming paymentcryptography requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import PaymentCryptographyControlPlaneBackend, paymentcryptography_backends


class PaymentCryptographyControlPlaneResponse(BaseResponse):
    """Handler for PaymentCryptographyControlPlane requests and responses."""

    def __init__(self):
        super().__init__(service_name="paymentcryptography")

    @property
    def paymentcryptography_backend(self) -> PaymentCryptographyControlPlaneBackend:
        """Return backend instance specific for this region."""
        return paymentcryptography_backends[self.current_account][self.region]


    def create_key(self) -> str:
        params = self._get_params()
        key_attributes = params.get("KeyAttributes")
        key_check_value_algorithm = params.get("KeyCheckValueAlgorithm")
        exportable = params.get("Exportable")
        enabled = params.get("Enabled")
        tags = params.get("Tags")
        derive_key_usage = params.get("DeriveKeyUsage")
        replication_regions = params.get("ReplicationRegions")
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
        params = self._get_params()
        key_state = params.get("KeyState")
        next_token = params.get("NextToken")
        max_results = params.get("MaxResults")
        keys, next_token = self.paymentcryptography_backend.list_keys(
            key_state=key_state,
            next_token=next_token,
            max_results=max_results,
        )
        # TODO: adjust response
        return json.dumps(dict(keys=keys, nextToken=next_token))

    # add templates from here

    def list_tags_for_resource(self):
        params = self._get_params()
        resource_arn = params.get("ResourceArn")
        next_token = params.get("NextToken")
        max_results = params.get("MaxResults")
        tags, next_token = self.paymentcryptography_backend.list_tags_for_resource(
            resource_arn=resource_arn,
            next_token=next_token,
            max_results=max_results,
        )
        # TODO: adjust response
        return json.dumps(dict(tags=tags, nextToken=next_token))

    def tag_resource(self):
        params = self._get_params()
        resource_arn = params.get("ResourceArn")
        tags = params.get("Tags")
        self.paymentcryptography_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict())
