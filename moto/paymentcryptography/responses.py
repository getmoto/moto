"""Responses for the AWS Payment Cryptography control plane."""

from typing import Any

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import (
    PaymentCryptographyControlPlaneBackend,
    paymentcryptography_backends,
)


class PaymentCryptographyControlPlaneResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="payment-cryptography")
        self.automated_parameter_parsing = True

    @property
    def backend(self) -> PaymentCryptographyControlPlaneBackend:
        return paymentcryptography_backends[self.current_account][self.region]

    def create_key(self) -> ActionResult:
        p = self._get_params()
        return ActionResult(
            {
                "Key": self.backend.create_key(
                    key_attributes=p["KeyAttributes"],
                    exportable=p["Exportable"],
                    enabled=p.get("Enabled", True),
                    key_check_value_algorithm=p.get("KeyCheckValueAlgorithm"),
                    tags=p.get("Tags"),
                    derive_key_usage=p.get("DeriveKeyUsage"),
                    replication_regions=p.get("ReplicationRegions"),
                )
            }
        )

    def get_key(self) -> ActionResult:
        return ActionResult(
            {"Key": self.backend.get_key(self._get_param("KeyIdentifier"))}
        )

    def list_keys(self) -> ActionResult:
        p = self._get_params()
        values, token = self.backend.list_keys(
            p.get("KeyState"), p.get("NextToken"), p.get("MaxResults")
        )
        result: dict[str, Any] = {"Keys": values}
        if token:
            result["NextToken"] = token
        return ActionResult(result)

    def delete_key(self) -> ActionResult:
        return ActionResult(
            {
                "Key": self.backend.delete_key(
                    self._get_param("KeyIdentifier"), self._get_param("DeleteKeyInDays")
                )
            }
        )

    def restore_key(self) -> ActionResult:
        return ActionResult(
            {"Key": self.backend.restore_key(self._get_param("KeyIdentifier"))}
        )

    def start_key_usage(self) -> ActionResult:
        return ActionResult(
            {"Key": self.backend.start_key_usage(self._get_param("KeyIdentifier"))}
        )

    def stop_key_usage(self) -> ActionResult:
        return ActionResult(
            {"Key": self.backend.stop_key_usage(self._get_param("KeyIdentifier"))}
        )

    def create_alias(self) -> ActionResult:
        return ActionResult(
            {
                "Alias": self.backend.create_alias(
                    self._get_param("AliasName"), self._get_param("KeyArn")
                )
            }
        )

    def get_alias(self) -> ActionResult:
        return ActionResult(
            {"Alias": self.backend.get_alias(self._get_param("AliasName"))}
        )

    def list_aliases(self) -> ActionResult:
        p = self._get_params()
        values, token = self.backend.list_aliases(
            p.get("KeyArn"), p.get("NextToken"), p.get("MaxResults")
        )
        result: dict[str, Any] = {"Aliases": values}
        if token:
            result["NextToken"] = token
        return ActionResult(result)

    def update_alias(self) -> ActionResult:
        return ActionResult(
            {
                "Alias": self.backend.update_alias(
                    self._get_param("AliasName"), self._get_param("KeyArn")
                )
            }
        )

    def delete_alias(self) -> EmptyResult:
        self.backend.delete_alias(self._get_param("AliasName"))
        return EmptyResult()

    def tag_resource(self) -> EmptyResult:
        self.backend.tag_resource(
            self._get_param("ResourceArn"), self._get_param("Tags")
        )
        return EmptyResult()

    def untag_resource(self) -> EmptyResult:
        self.backend.untag_resource(
            self._get_param("ResourceArn"), self._get_param("TagKeys")
        )
        return EmptyResult()

    def list_tags_for_resource(self) -> ActionResult:
        p = self._get_params()
        values, token = self.backend.list_tags_for_resource(
            p["ResourceArn"], p.get("NextToken"), p.get("MaxResults")
        )
        result: dict[str, Any] = {"Tags": values}
        if token:
            result["NextToken"] = token
        return ActionResult(result)

    def put_resource_policy(self) -> ActionResult:
        return ActionResult(
            self.backend.put_resource_policy(
                self._get_param("ResourceArn"), self._get_param("Policy")
            )
        )

    def get_resource_policy(self) -> ActionResult:
        return ActionResult(
            self.backend.get_resource_policy(self._get_param("ResourceArn"))
        )

    def delete_resource_policy(self) -> EmptyResult:
        self.backend.delete_resource_policy(self._get_param("ResourceArn"))
        return EmptyResult()

    def enable_default_key_replication_regions(self) -> ActionResult:
        return ActionResult(
            {
                "EnabledReplicationRegions": self.backend.enable_default_key_replication_regions(
                    self._get_param("ReplicationRegions")
                )
            }
        )

    def disable_default_key_replication_regions(self) -> ActionResult:
        return ActionResult(
            {
                "EnabledReplicationRegions": self.backend.disable_default_key_replication_regions(
                    self._get_param("ReplicationRegions")
                )
            }
        )

    def get_default_key_replication_regions(self) -> ActionResult:
        return ActionResult(
            {
                "EnabledReplicationRegions": self.backend.get_default_key_replication_regions()
            }
        )

    def add_key_replication_regions(self) -> ActionResult:
        return ActionResult(
            {
                "Key": self.backend.add_key_replication_regions(
                    self._get_param("KeyIdentifier"),
                    self._get_param("ReplicationRegions"),
                )
            }
        )

    def remove_key_replication_regions(self) -> ActionResult:
        return ActionResult(
            {
                "Key": self.backend.remove_key_replication_regions(
                    self._get_param("KeyIdentifier"),
                    self._get_param("ReplicationRegions"),
                )
            }
        )

    def get_parameters_for_import(self) -> ActionResult:
        p = self._get_params()
        return ActionResult(
            self.backend.get_parameters_for_import(
                p["KeyMaterialType"],
                p["WrappingKeyAlgorithm"],
                p.get("ReuseLastGeneratedToken", False),
            )
        )

    def get_parameters_for_export(self) -> ActionResult:
        p = self._get_params()
        return ActionResult(
            self.backend.get_parameters_for_export(
                p["KeyMaterialType"],
                p["SigningKeyAlgorithm"],
                p.get("ReuseLastGeneratedToken", False),
            )
        )

    def import_key(self) -> ActionResult:
        p = self._get_params()
        return ActionResult(
            {
                "Key": self.backend.import_key(
                    p["KeyMaterial"],
                    key_check_value_algorithm=p.get("KeyCheckValueAlgorithm"),
                    enabled=p.get("Enabled", True),
                    tags=p.get("Tags"),
                    replication_regions=p.get("ReplicationRegions"),
                    requester_comment=p.get("RequesterComment"),
                )
            }
        )

    def export_key(self) -> ActionResult:
        p = self._get_params()
        return ActionResult(
            {
                "WrappedKey": self.backend.export_key(
                    p["KeyMaterial"],
                    p["ExportKeyIdentifier"],
                    p.get("ExportAttributes"),
                )
            }
        )

    def get_public_key_certificate(self) -> ActionResult:
        return ActionResult(
            self.backend.get_public_key_certificate(self._get_param("KeyIdentifier"))
        )

    def get_certificate_signing_request(self) -> ActionResult:
        p = self._get_params()
        return ActionResult(
            {
                "CertificateSigningRequest": self.backend.get_certificate_signing_request(
                    p["KeyIdentifier"], p["SigningAlgorithm"], p["CertificateSubject"]
                )
            }
        )

    def associate_mpa_team(self) -> ActionResult:
        p = self._get_params()
        return ActionResult(
            {
                "MpaTeamAssociation": self.backend.associate_mpa_team(
                    p["Action"], p["MpaTeamArn"], p.get("RequesterComment")
                )
            }
        )

    def get_mpa_team_association(self) -> ActionResult:
        return ActionResult(
            {
                "MpaTeamAssociation": self.backend.get_mpa_team_association(
                    self._get_param("Action")
                )
            }
        )

    def disassociate_mpa_team(self) -> ActionResult:
        p = self._get_params()
        return ActionResult(
            {
                "MpaTeamAssociation": self.backend.disassociate_mpa_team(
                    p["Action"], p.get("RequesterComment")
                )
            }
        )
