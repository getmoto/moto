import random
import uuid
from typing import Any, Dict, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.utilities.paginator import paginate
from moto.utilities.tagging_service import TaggingService

from .exceptions import ResourceNotFoundException


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
        self.id: str = f"srv-{str(uuid.uuid4())[:18]}"
        self.auth_type: str = auth_type
        self.certificate_arn: str = certificate_arn or ""
        self.client_token: str = client_token
        self.custom_domain_name: str = custom_domain_name or ""
        self.dns_entry: VPCLatticeDNSEntry = VPCLatticeDNSEntry(
            region, self.id, self.custom_domain_name
        )
        self.name: str = name
        self.arn: str = f"arn:aws:vpc-lattice:{region}:{account_id}:service/{name}"
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
        self.arn: str = (
            f"arn:aws:vpc-lattice:{region}:{account_id}:servicenetwork/{name}"
        )
        self.auth_type: str = auth_type
        self.client_token: str = client_token
        self.id: str = f"snet-{name[:8]}"
        self.name: str = name
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
        self.arn: str = (
            f"arn:aws:vpc-lattice:{region}:{account_id}:servicenetworkvpcassociation/"
            f"{service_network_identifier}/{vpc_identifier}"
        )
        self.created_by: str = "user"
        self.id: str = f"snva-{service_network_identifier[:4]}-{vpc_identifier[:4]}"
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
        self.arn: str = (
            f"arn:aws:vpc-lattice:{region}:{account_id}:service/{service_identifier}"
            f"/listener/{listener_identifier}/rule/{name}"
        )
        self.id: str = f"rule-{str(uuid.uuid4())[:8]}"
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
        self.services: Dict[str, VPCLatticeService] = {}
        self.service_networks: Dict[str, VPCLatticeServiceNetwork] = {}
        self.service_network_vpc_associations: Dict[
            str, VPCLatticeServiceNetworkVpcAssociation
        ] = {}
        self.rules: Dict[str, VPCLatticeRule] = {}
        self.tagger: TaggingService = TaggingService()

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
        self.tag_resource(service.arn, tags)
        return service

    def get_service(self, service_identifier: str) -> VPCLatticeService:
        service = self._get_service_by_arn(service_identifier)
        if service:
            return service

        service = self._get_service_by_id(service_identifier)
        if service:
            return service

        raise ResourceNotFoundException(service_identifier)

    def _get_service_by_id(self, service_id: str) -> Optional[VPCLatticeService]:
        return self.services.get(service_id)

    def _get_service_by_arn(self, service_arn: str) -> Optional[VPCLatticeService]:
        for service in self.services.values():
            if service.arn == service_arn:
                return service
        return None

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_services(self) -> List[VPCLatticeService]:
        return [service for service in self.services.values()]

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
        self.tag_resource(sn.arn, tags)
        return sn

    def get_service_network(
        self, service_network_identifier: str
    ) -> VPCLatticeServiceNetwork:
        service = self._get_service_network_by_arn(service_network_identifier)
        if service:
            return service

        service = self._get_service_network_by_id(service_network_identifier)
        if service:
            return service

        raise ResourceNotFoundException(service_network_identifier)

    def _get_service_network_by_id(
        self, service_network_id: str
    ) -> Optional[VPCLatticeServiceNetwork]:
        return self.service_networks.get(service_network_id)

    def _get_service_network_by_arn(
        self, service_network_arn: str
    ) -> Optional[VPCLatticeServiceNetwork]:
        for service_network in self.service_networks.values():
            if service_network.arn == service_network_arn:
                return service_network
        return None

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_service_networks(self) -> List[VPCLatticeServiceNetwork]:
        return [service_network for service_network in self.service_networks.values()]

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
        self.tag_resource(assoc.arn, tags)
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
        self.tag_resource(rule.arn, tags)
        return rule

    def tag_resource(self, resource_arn: str, tags: Optional[Dict[str, str]]) -> None:
        tags_input = self.tagger.convert_dict_to_tags_input(tags or {})
        self.tagger.tag_resource(resource_arn, tags_input)

    def list_tags_for_resource(self, resource_arn: str) -> Optional[Dict[str, Any]]:
        if self.tagger.has_tags(resource_arn):
            return self.tagger.get_tag_dict_for_resource(resource_arn)
        return None

    def untag_resource(self, resource_arn: str, tag_keys: List[str]) -> None:
        if not isinstance(tag_keys, list):
            tag_keys = [tag_keys]
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)


vpclattice_backends: BackendDict[VPCLatticeBackend] = BackendDict(
    VPCLatticeBackend, "vpc-lattice"
)
