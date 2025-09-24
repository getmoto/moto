"""VPCLatticeBackend class with methods for supported APIs."""
import random
import uuid

from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel
from moto.utilities.tagging_service import TaggingService

from typing import Optional


class VPCLatticeService(BaseModel):
    def __init__(self, region: str, account_id: str, auth_type:str, certificate_arn:str, client_token:str, custom_domain_name:str, name: str, tags) -> None:
        self.id: str = f"srv-{str(uuid.uuid4())[:18]}"
        self.auth_type: str = auth_type
        self.certificate_arn: Optional[str] = certificate_arn
        self.client_token: str = client_token
        self.custom_domain_name: Optional[str] = custom_domain_name
        self.dns_entry: VPCLatticeDNSEntry = VPCLatticeDNSEntry(region, self.id, custom_domain_name)
        self.name: str = name
        self.arn: str = f"arn:aws:vpc-lattice:{region}:{account_id}:service/{name}"
        self.status: str = "ACTIVE"
        self.tags: dict = tags or {}

    def to_dict(self) -> dict:
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
    def __init__(self, region, account_id, auth_type, client_token, name, sharing_config, tags) -> None:
        self.arn = f"arn:aws:vpc-lattice:{region}:{account_id}:servicenetwork/{name}"
        self.auth_type = auth_type
        self.client_token = client_token
        self.id = f"snet-{name[:8]}"
        self.name = name
        self.sharing_config = sharing_config
        self.tags = tags or {}

    def to_dict(self) -> dict:
        return {
            "arn": self.arn,
            "auth_type": self.auth_type,
            "id": self.id,
            "name": self.name,
            "sharing_config": self.sharing_config,
            "tags": self.tags,
        }
    
class VPCLatticeServiceNetworkVpcAssociation(BaseModel):
    def __init__(self, region, account_id, client_token, security_group_ids, service_network_identifier, tags, vpc_identifier) -> None:
        self.arn = f"arn:aws:vpc-lattice:{region}:{account_id}:servicenetworkvpcassociation/{service_network_identifier}/{vpc_identifier}"
        self.created_by = "user"
        self.id = f"snva-{service_network_identifier[:4]}-{vpc_identifier[:4]}"
        self.security_group_ids = security_group_ids
        self.status = "ACTIVE"
        self.tags = tags or {}

    def to_dict(self) -> dict:
        return {
            "arn": self.arn,
            "created_by": self.created_by,
            "id": self.id,
            "security_group_ids": self.security_group_ids,
            "status": self.status,
            "tags": self.tags,
        }
    
class VPCLatticeRule(BaseModel):
    def __init__(self, region, account_id, action, client_token, listener_identifier, match, name, priority, service_identifier, tags) -> None:
        self.action = action
        self.arn = f"arn:aws:vpc-lattice:{region}:{account_id}:rule/{name}"
        self.id = f"rule-{name[:8]}"
        self.match = match
        self.name = name
        self.priority = priority
        self.service_identifier = service_identifier
        self.tags = tags or {}

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "arn": self.arn,
            "id": self.id,
            "match": self.match,
            "name": self.name,
            "priority": self.priority,
            "service_identifier": self.service_identifier,
            "tags": self.tags,
        }

class VPCLatticeDNSEntry:
    """Encapsulates the DNS entry for a VPC Lattice Service."""

    def __init__(self, region_name: str, service_id: str, custom_domain_name: str = None) -> None:
        if custom_domain_name:
            self.domain_name: str = custom_domain_name
        else:
            self.domain_name: str = f"{service_id}.{region_name}.vpclattice.amazonaws.com"

        # simulating HostedZoneId
        self.hosted_zone_id: str = f"Z{random.randint(100000, 999999)}XYZ"

    def to_dict(self) -> dict[str, str]:
        return {
            "domainName": self.domain_name,
            "hostedZoneId": self.hosted_zone_id,
        }

class VPCLatticeBackend(BaseBackend):
    """Implementation of VPCLattice APIs."""

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.services: dict = {}
        self.service_networks: dict = {}
        self.service_network_vpc_associations: dict = {}
        self.rules: dict = {}
        self.tagger = TaggingService()

    # add methods from here

    def create_service(self, auth_type: str, certificate_arn: str, client_token: str, custom_domain_name: str, name: str, tags: dict) -> VPCLatticeService:
        service = VPCLatticeService(
            region=self.region_name,
            account_id=self.account_id,
            auth_type=auth_type,
            certificate_arn=certificate_arn if certificate_arn else "",
            client_token=client_token,
            custom_domain_name=custom_domain_name if custom_domain_name else "",
            name=name,
            tags=tags,
        )
        self.services[service.id] = service
        service = service.to_dict()
        return service
    # def create_service_network(self, auth_type, client_token, name, sharing_config, tags):
    #     # implement here
    #     return arn, auth_type, id, name, sharing_config
    
    # def create_service_network_vpc_association(self, client_token, security_group_ids, service_network_identifier, tags, vpc_identifier):
    #     # implement here
    #     return arn, created_by, id, security_group_ids, status
    
    # def create_rule(self, action, client_token, listener_identifier, match, name, priority, service_identifier, tags):
    #     # implement here
    #     return action, arn, id, match, name, priority
    
    # def tag_resource(self, resource_arn, tags):
    #     # implement here
    #     return 
    
    # def list_tags_for_resource(self, resource_arn):
    #     # implement here
    #     return tags
    

vpclattice_backends: BackendDict[VPCLatticeBackend] = BackendDict(VPCLatticeBackend, "vpc-lattice")
