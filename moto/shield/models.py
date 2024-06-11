"""ShieldBackend class with methods for supported APIs."""

from typing import Any, Dict, List

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.moto_api._internal import mock_random
from moto.shield.exceptions import (
    InvalidParameterException,
    InvalidResourceException,
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    ValidationException,
)
from moto.utilities.tagging_service import TaggingService


class Protection(BaseModel):
    def __init__(
        self, account_id: str, name: str, resource_arn: str, tags: List[Dict[str, str]]
    ):
        self.name = name
        self.resource_arn = resource_arn
        self.protection_id = str(mock_random.uuid4())
        self.tags = tags
        self.health_check_ids: list[
            str
        ] = []  # value is returned in associate_health_check method.
        # value is returned in enable_application_layer_automatic_response and disable_application_layer_automatic_response methods.
        self.application_layer_automatic_response_configuration: dict[str, Any] = {}
        self.protection_arn = (
            f"arn:aws:shield::{account_id}:protection/{self.protection_id}"
        )

        resource_types = {
            "cloudfront": "CLOUDFRONT_DISTRIBUTION",
            "globalaccelerator": "GLOBAL_ACCELERATOR",
            "route53": "ROUTE_53_HOSTED_ZONE",
            "ec2": "ELASTIC_IP_ALLOCATION",
        }
        res_type = resource_arn.split(":")[2]
        if res_type == "elasticloadbalancing":
            if resource_arn.split(":")[-1][1] == "app":
                self.resource_type = "APPLICATION_LOAD_BALANCER"
            else:
                self.resource_type = "CLASSIC_LOAD_BALANCER"
        else:
            self.resource_type = resource_types[res_type]

    def to_dict(self) -> Dict[str, Any]:
        dct = {
            "Id": self.protection_id,
            "Name": self.name,
            "ResourceArn": self.resource_arn,
            "HealthCheckIds": self.health_check_ids,
            "ProtectionArn": self.protection_arn,
            "ApplicationLayerAutomaticResponseConfiguration": self.application_layer_automatic_response_configuration,
        }
        return {k: v for k, v in dct.items() if v}


class ShieldBackend(BaseBackend):
    """Implementation of Shield APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.protections: Dict[str, Protection] = dict()
        self.tagger = TaggingService()

    def validate_resource_arn(self, resource_arn: str) -> None:
        """Raise exception if the resource arn is invalid."""

        # Shield offers protection to only certain services.
        self.valid_resource_types = [
            "elasticloadbalancing",
            "cloudfront",
            "globalaccelerator",
            "route53",
            "ec2",
        ]
        resource_type = resource_arn.split(":")[2]
        if resource_type not in self.valid_resource_types:
            resource = resource_arn.split(":")[-1]
            if "/" in resource:
                msg = f"Unrecognized resource '{resource.split('/')[0]}' of service '{resource_type}'."
            else:
                msg = "Relative ID must be in the form '<resource>/<id>'."
            raise InvalidResourceException(msg)

    def create_protection(
        self, name: str, resource_arn: str, tags: List[Dict[str, str]]
    ) -> str:
        for protection in self.protections.values():
            if protection.resource_arn == resource_arn:
                raise ResourceAlreadyExistsException(
                    "The referenced protection already exists."
                )
        self.validate_resource_arn(resource_arn)
        protection = Protection(
            account_id=self.account_id, name=name, resource_arn=resource_arn, tags=tags
        )
        self.protections[protection.protection_id] = protection
        self.tag_resource(protection.protection_arn, tags)
        return protection.protection_id

    def describe_protection(self, protection_id: str, resource_arn: str) -> Protection:  # type: ignore[return]
        if protection_id and resource_arn:
            msg = "Invalid parameter. You must provide one value, either protectionId or resourceArn, but not both."
            raise InvalidParameterException(msg)

        if resource_arn:
            for protection in self.protections.values():
                if protection.resource_arn == resource_arn:
                    return protection
            raise ResourceNotFoundException("The referenced protection does not exist.")

        if protection_id:
            if protection_id not in self.protections:
                raise ResourceNotFoundException(
                    "The referenced protection does not exist."
                )
            return self.protections[protection_id]

    def list_protections(self, inclusion_filters: Dict[str, str]) -> List[Protection]:
        """
        Pagination has not yet been implemented
        """
        resource_protections = []
        name_protections = []
        type_protections = []

        if inclusion_filters:
            resource_arns = inclusion_filters.get("ResourceArns")
            if resource_arns:
                if len(resource_arns) > 1:
                    raise ValidationException(
                        "Error validating the following inputs: inclusionFilters.resourceArns"
                    )
                resource_protections = [
                    protection
                    for protection in self.protections.values()
                    if protection.resource_arn == resource_arns[0]
                ]
            protection_names = inclusion_filters.get("ProtectionNames")
            if protection_names:
                if len(protection_names) > 1:
                    raise ValidationException(
                        "Error validating the following inputs: inclusionFilters.protectionNames"
                    )
                name_protections = [
                    protection
                    for protection in self.protections.values()
                    if protection.name == protection_names[0]
                ]
            resource_types = inclusion_filters.get("ResourceTypes")
            if resource_types:
                if len(resource_types) > 1:
                    raise ValidationException(
                        "Error validating the following inputs: inclusionFilters.resourceTypes"
                    )
                type_protections = [
                    protection
                    for protection in self.protections.values()
                    if protection.resource_type == resource_types[0]
                ]
            try:
                protections = list(
                    set.intersection(
                        *(
                            set(x)
                            for x in [
                                resource_protections,
                                name_protections,
                                type_protections,
                            ]
                            if x
                        )
                    )
                )
            except TypeError:
                protections = []
        else:
            protections = list(self.protections.values())
        return protections

    def delete_protection(self, protection_id: str) -> None:
        if protection_id in self.protections:
            del self.protections[protection_id]
            return
        raise ResourceNotFoundException("The referenced protection does not exist.")

    def list_tags_for_resource(self, resource_arn: str) -> List[Dict[str, str]]:
        return self.tagger.list_tags_for_resource(resource_arn)["Tags"]

    def tag_resource(self, resource_arn: str, tags: List[Dict[str, str]]) -> None:
        self.tagger.tag_resource(resource_arn, tags)

    def untag_resource(self, resource_arn: str, tag_keys: List[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)


shield_backends = BackendDict(ShieldBackend, "ec2")
