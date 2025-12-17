import random
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.utilities.paginator import paginate
from moto.utilities.tagging_service import TaggingService
from moto.vpclattice.exceptions import (
    ResourceNotFoundException,
    ValidationException,
)


class VPCLatticeService(BaseModel):
    def __init__(
        self,
        region: str,
        account_id: str,
        auth_type: str,
        certificate_arn: Optional[str],
        client_token: str,
        custom_domain_name: Optional[str],
        name: str,
        tags: Optional[dict[str, str]],
    ) -> None:
        self.id: str = f"svc-{str(uuid.uuid4())[:17]}"
        self.auth_type: str = auth_type
        self.certificate_arn: str = certificate_arn or ""
        self.client_token: str = client_token
        self.custom_domain_name: str = custom_domain_name or ""
        self.dns_entry: VPCLatticeDNSEntry = VPCLatticeDNSEntry(
            region, self.id, self.custom_domain_name
        )
        self.name: str = name
        self.arn: str = f"arn:aws:vpc-lattice:{region}:{account_id}:service/{self.id}"
        self.status: str = "ACTIVE"
        self.tags: dict[str, str] = tags or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "arn": self.arn,
            "authType": self.auth_type,
            "certificateArn": self.certificate_arn,
            "customDomainName": self.custom_domain_name,
            "dnsEntry": self.dns_entry.to_dict(),
            "id": self.id,
            "name": self.name,
            "status": self.status,
        }


class VPCLatticeServiceNetwork(BaseModel):
    def __init__(
        self,
        region: str,
        account_id: str,
        auth_type: str,
        client_token: str,
        name: str,
        sharing_config: Optional[dict[str, Any]],
        tags: Optional[dict[str, str]],
    ) -> None:
        self.auth_type: str = auth_type
        self.client_token: str = client_token
        self.id: str = f"sn-{str(uuid.uuid4())[:17]}"
        self.name: str = name
        self.arn: str = (
            f"arn:aws:vpc-lattice:{region}:{account_id}:servicenetwork/{self.id}"
        )
        self.sharing_config: dict[str, Any] = sharing_config or {}
        self.tags: dict[str, str] = tags or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "arn": self.arn,
            "authType": self.auth_type,
            "id": self.id,
            "name": self.name,
            "sharingConfig": self.sharing_config,
        }


class VPCLatticeServiceNetworkVpcAssociation(BaseModel):
    def __init__(
        self,
        region: str,
        account_id: str,
        client_token: str,
        security_group_ids: Optional[list[str]],
        service_network_identifier: str,
        tags: Optional[dict[str, str]],
        vpc_identifier: str,
    ) -> None:
        self.id: str = f"snva-{service_network_identifier[:4]}-{vpc_identifier[:4]}"
        self.arn: str = f"arn:aws:vpc-lattice:{region}:{account_id}:servicenetworkvpcassociation/{self.id}"
        self.created_by: str = "user"
        self.security_group_ids: list[str] = security_group_ids or []
        self.status: str = "ACTIVE"
        self.tags: dict[str, str] = tags or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "arn": self.arn,
            "createdBy": self.created_by,
            "id": self.id,
            "securityGroupIds": self.security_group_ids,
            "status": self.status,
            "tags": self.tags,
        }


class VPCLatticeRule(BaseModel):
    def __init__(
        self,
        region: str,
        account_id: str,
        action: dict[str, Any],
        client_token: str,
        listener_identifier: str,
        match: dict[str, Any],
        name: str,
        priority: int,
        service_identifier: str,
        tags: dict[str, str],
    ) -> None:
        self.action: dict[str, Any] = action or {}
        self.id: str = f"rule-[0-9a-z]{17}"
        self.arn: str = (
            f"arn:aws:vpc-lattice:{region}:{account_id}:service/{service_identifier}"
            f"/listener/listener-{listener_identifier}/rule/{self.id}"
        )
        self.client_token: str = client_token
        self.listener_identifier: str = listener_identifier
        self.match: dict[str, Any] = match or {}
        self.name: str = name
        self.priority: int = priority
        self.service_identifier: str = service_identifier
        self.tags: dict[str, str] = tags or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "arn": self.arn,
            "id": self.id,
            "name": self.name,
            "priority": self.priority,
            "action": self.action,
            "match": self.match,
            "serviceIdentifier": self.service_identifier,
            "listenerIdentifier": self.listener_identifier,
            "tags": self.tags,
        }


class VPCLatticeDNSEntry:
    def __init__(
        self,
        region_name: str,
        service_id: str,
        custom_domain_name: Optional[str] = None,
    ) -> None:
        self.domain_name: str = (
            custom_domain_name or f"{service_id}.{region_name}.vpclattice.amazonaws.com"
        )
        self.hosted_zone_id: str = f"Z{random.randint(100000, 999999)}XYZ"

    def to_dict(self) -> dict[str, str]:
        return {"domainName": self.domain_name, "hostedZoneId": self.hosted_zone_id}


class VPCLatticeAccessLogSubscription(BaseModel):
    def __init__(
        self,
        region: str,
        account_id: str,
        destinationArn: str,
        resourceArn: str,
        resourceId: str,  # resourceIdentifier
        serviceNetworkLogType: Optional[str],
        tags: Optional[dict[str, str]],
    ) -> None:
        self.id: str = f"als-{str(uuid.uuid4())[:17]}"
        self.arn: str = (
            f"arn:aws:vpc-lattice:{region}:{account_id}:accesslogsubscription/{self.id}"
        )
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.destinationArn = destinationArn
        self.last_updated_at = datetime.now(timezone.utc).isoformat()
        self.resourceArn = resourceArn
        self.resourceId = resourceId
        self.serviceNetworkLogType = serviceNetworkLogType or "SERVICE"
        self.tags = tags or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "arn": self.arn,
            "createdAt": self.created_at,
            "destinationArn": self.destinationArn,
            "id": self.id,
            "lastUpdatedAt": self.last_updated_at,
            "resourceArn": self.resourceArn,
            "resourceId": self.resourceId,
            "serviceNetworkLogType": self.serviceNetworkLogType,
            "tags": self.tags,
        }


class VPCLatticeBackend(BaseBackend):
    PAGINATION_MODEL = {
        "list_services": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 50,
            "unique_attribute": "id",
        },
        "list_service_networks": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 50,
            "unique_attribute": "id",
        },
    }

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.services: dict[str, VPCLatticeService] = {}
        self.service_networks: dict[str, VPCLatticeServiceNetwork] = {}
        self.service_network_vpc_associations: dict[
            str, VPCLatticeServiceNetworkVpcAssociation
        ] = {}
        self.rules: dict[str, VPCLatticeRule] = {}
        self.tagger: TaggingService = TaggingService()
        self.access_log_subscriptions: dict[str, VPCLatticeAccessLogSubscription] = {}

    def create_service(
        self,
        auth_type: str,
        certificate_arn: Optional[str],
        client_token: str,
        custom_domain_name: Optional[str],
        name: str,
        tags: Optional[dict[str, str]],
    ) -> VPCLatticeService:
        service = VPCLatticeService(
            self.region_name,
            self.account_id,
            auth_type,
            certificate_arn,
            client_token,
            custom_domain_name,
            name,
            tags,
        )
        self.services[service.id] = service
        self.tag_resource(service.arn, tags or {})
        return service

    def get_service(self, service_identifier: str) -> VPCLatticeService:
        service = self.services.get(service_identifier)
        if not service:
            raise ResourceNotFoundException(service_identifier)
        return service

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_services(self) -> list[VPCLatticeService]:
        return list(self.services.values())

    def create_service_network(
        self,
        auth_type: str,
        client_token: str,
        name: str,
        sharing_config: Optional[dict[str, Any]],
        tags: Optional[dict[str, str]],
    ) -> VPCLatticeServiceNetwork:
        """
        WARNING: This method currently does NOT fail if there is a disassociation in progress.
        """
        sn = VPCLatticeServiceNetwork(
            self.region_name,
            self.account_id,
            auth_type,
            client_token,
            name,
            sharing_config,
            tags,
        )
        self.service_networks[sn.id] = sn
        self.tag_resource(sn.arn, tags or {})
        return sn

    def get_service_network(
        self, service_network_identifier: str
    ) -> VPCLatticeServiceNetwork:
        service_network = self.service_networks.get(service_network_identifier)
        if not service_network:
            raise ResourceNotFoundException(service_network_identifier)
        return service_network

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_service_networks(self) -> list[VPCLatticeServiceNetwork]:
        return list(self.service_networks.values())

    def create_service_network_vpc_association(
        self,
        client_token: str,
        security_group_ids: Optional[list[str]],
        service_network_identifier: str,
        tags: Optional[dict[str, str]],
        vpc_identifier: str,
    ) -> VPCLatticeServiceNetworkVpcAssociation:
        assoc = VPCLatticeServiceNetworkVpcAssociation(
            self.region_name,
            self.account_id,
            client_token,
            security_group_ids,
            service_network_identifier,
            tags,
            vpc_identifier,
        )
        self.service_network_vpc_associations[assoc.id] = assoc
        self.tag_resource(assoc.arn, tags or {})
        return assoc

    def create_rule(
        self,
        action: dict[str, Any],
        client_token: str,
        listener_identifier: str,
        match: dict[str, Any],
        name: str,
        priority: int,
        service_identifier: str,
        tags: dict[str, str],
    ) -> VPCLatticeRule:
        rule = VPCLatticeRule(
            self.region_name,
            self.account_id,
            action,
            client_token,
            listener_identifier,
            match,
            name,
            priority,
            service_identifier,
            tags,
        )
        self.rules[rule.id] = rule
        self.tag_resource(rule.arn, tags or {})
        return rule

    def tag_resource(self, resource_arn: str, tags: dict[str, str]) -> None:
        tags_input = self.tagger.convert_dict_to_tags_input(tags or {})
        self.tagger.tag_resource(resource_arn, tags_input)

    def list_tags_for_resource(self, resource_arn: str) -> dict[str, str]:
        return self.tagger.get_tag_dict_for_resource(resource_arn)

    def untag_resource(self, resource_arn: str, tag_keys: list[str]) -> None:
        if not isinstance(tag_keys, list):
            tag_keys = [tag_keys]
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def create_access_log_subscription(
        self,
        resourceIdentifier: str,
        destinationArn: str,
        client_token: Optional[str],
        serviceNetworkLogType: Optional[str],
        tags: Optional[dict[str, str]],
    ) -> VPCLatticeAccessLogSubscription:
        resource: Any = None
        if resourceIdentifier.startswith("sn-"):
            resource = self.service_networks.get(resourceIdentifier)
        elif resourceIdentifier.startswith("svc-"):
            resource = self.services.get(resourceIdentifier)
        else:
            raise ValidationException(
                "Invalid parameter resourceIdentifier, must start with 'sn-' or 'svc-'"
            )

        if not resource:
            raise ResourceNotFoundException(f"Resource {resourceIdentifier} not found")

        sub = VPCLatticeAccessLogSubscription(
            self.region_name,
            self.account_id,
            destinationArn,
            resource.arn,
            resource.id,
            serviceNetworkLogType,
            tags,
        )

        self.access_log_subscriptions[sub.id] = sub
        return sub

    def get_access_log_subscription(
        self, accessLogSubscriptionIdentifier: str
    ) -> VPCLatticeAccessLogSubscription:
        sub = self.access_log_subscriptions.get(accessLogSubscriptionIdentifier)
        if not sub:
            raise ResourceNotFoundException(
                f"Access Log Subscription {accessLogSubscriptionIdentifier} not found"
            )
        return sub

    def list_access_log_subscriptions(
        self,
        resourceIdentifier: str,
        maxResults: Optional[int] = None,
        nextToken: Optional[str] = None,
    ) -> list[VPCLatticeAccessLogSubscription]:
        return [
            sub
            for sub in self.access_log_subscriptions.values()
            if sub.resourceId == resourceIdentifier
        ][:maxResults]

    def update_access_log_subscription(
        self,
        accessLogSubscriptionIdentifier: str,
        destinationArn: str,
    ) -> VPCLatticeAccessLogSubscription:
        sub = self.access_log_subscriptions.get(accessLogSubscriptionIdentifier)
        if not sub:
            raise ResourceNotFoundException(
                f"Access Log Subscription {accessLogSubscriptionIdentifier} not found"
            )

        sub.destinationArn = destinationArn
        sub.last_updated_at = datetime.now(timezone.utc).isoformat()

        return sub

    def delete_access_log_subscription(
        self, accessLogSubscriptionIdentifier: str
    ) -> None:
        sub = self.access_log_subscriptions.get(accessLogSubscriptionIdentifier)
        if not sub:
            raise ResourceNotFoundException(
                f"Access Log Subscription {accessLogSubscriptionIdentifier} not found"
            )
        del self.access_log_subscriptions[accessLogSubscriptionIdentifier]


vpclattice_backends: BackendDict[VPCLatticeBackend] = BackendDict(
    VPCLatticeBackend, "vpc-lattice"
)
