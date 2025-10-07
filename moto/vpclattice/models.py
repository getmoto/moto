import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
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
        tags: Optional[Dict[str, str]],
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
        self.tags: Dict[str, str] = tags or {}

    def to_dict(self) -> Dict[str, Any]:
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
        sharing_config: Optional[Dict[str, Any]],
        tags: Optional[Dict[str, str]],
    ) -> None:
        self.auth_type: str = auth_type
        self.client_token: str = client_token
        self.id: str = f"sn-{str(uuid.uuid4())[:17]}"
        self.name: str = name
        self.arn: str = (
            f"arn:aws:vpc-lattice:{region}:{account_id}:servicenetwork/{self.id}"
        )
        self.sharing_config: Dict[str, Any] = sharing_config or {}
        self.tags: Dict[str, str] = tags or {}

    def to_dict(self) -> Dict[str, Any]:
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
        security_group_ids: Optional[List[str]],
        service_network_identifier: str,
        tags: Optional[Dict[str, str]],
        vpc_identifier: str,
    ) -> None:
        self.id: str = f"snva-{service_network_identifier[:4]}-{vpc_identifier[:4]}"
        self.arn: str = f"arn:aws:vpc-lattice:{region}:{account_id}:servicenetworkvpcassociation/{self.id}"
        self.created_by: str = "user"
        self.security_group_ids: List[str] = security_group_ids or []
        self.status: str = "ACTIVE"
        self.tags: Dict[str, str] = tags or {}

    def to_dict(self) -> Dict[str, Any]:
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
        action: Dict[str, Any],
        client_token: str,
        listener_identifier: str,
        match: Dict[str, Any],
        name: str,
        priority: int,
        service_identifier: str,
        tags: Dict[str, str],
    ) -> None:
        self.action: Dict[str, Any] = action or {}
        self.id: str = f"rule-[0-9a-z]{17}"
        self.arn: str = (
            f"arn:aws:vpc-lattice:{region}:{account_id}:service/{service_identifier}"
            f"/listener/listener-{listener_identifier}/rule/{self.id}"
        )
        self.client_token: str = client_token
        self.listener_identifier: str = listener_identifier
        self.match: Dict[str, Any] = match or {}
        self.name: str = name
        self.priority: int = priority
        self.service_identifier: str = service_identifier
        self.tags: Dict[str, str] = tags or {}

    def to_dict(self) -> Dict[str, Any]:
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

    def to_dict(self) -> Dict[str, str]:
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
        tags: Optional[Dict[str, str]],
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

    def to_dict(self) -> Dict[str, Any]:
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
    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.services: Dict[str, VPCLatticeService] = {}
        self.service_networks: Dict[str, VPCLatticeServiceNetwork] = {}
        self.service_network_vpc_associations: Dict[
            str, VPCLatticeServiceNetworkVpcAssociation
        ] = {}
        self.rules: Dict[str, VPCLatticeRule] = {}
        self.tagger: TaggingService = TaggingService()
        self.access_log_subscriptions: Dict[str, VPCLatticeAccessLogSubscription] = {}

    def create_service(
        self,
        auth_type: str,
        certificate_arn: Optional[str],
        client_token: str,
        custom_domain_name: Optional[str],
        name: str,
        tags: Optional[Dict[str, str]],
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
        return service

    def create_service_network(
        self,
        auth_type: str,
        client_token: str,
        name: str,
        sharing_config: Optional[Dict[str, Any]],
        tags: Optional[Dict[str, str]],
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
        return sn

    def create_service_network_vpc_association(
        self,
        client_token: str,
        security_group_ids: Optional[List[str]],
        service_network_identifier: str,
        tags: Optional[Dict[str, str]],
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
        return assoc

    def create_rule(
        self,
        action: Dict[str, Any],
        client_token: str,
        listener_identifier: str,
        match: Dict[str, Any],
        name: str,
        priority: int,
        service_identifier: str,
        tags: Dict[str, str],
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
        return rule

    def create_access_log_subscription(
        self,
        resourceIdentifier: str,
        destinationArn: str,
        client_token: Optional[str],
        serviceNetworkLogType: Optional[str],
        tags: Optional[Dict[str, str]],
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
    ) -> List[VPCLatticeAccessLogSubscription]:
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
