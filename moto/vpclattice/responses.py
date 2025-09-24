"""Handles incoming vpclattice requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import VPCLatticeBackend, VPCLatticeService, vpclattice_backends
from typing import Optional


class VPCLatticeResponse(BaseResponse):
    """Handler for VPCLattice requests and responses."""

    def __init__(self):
        super().__init__(service_name="vpc-lattice")

    @property
    def vpclattice_backend(self) -> "VPCLatticeBackend":
        """Return backend instance specific for this region."""
        return vpclattice_backends[self.current_account][self.region]

    
    def create_service(self):
        auth_type: Optional[str] = self._get_param("authType")
        certificate_arn: Optional[str] = self._get_param("certificateArn")
        client_token: Optional[str] = self._get_param("clientToken")
        custom_domain_name: Optional[str] = self._get_param("customDomainName")
        name: str = self._get_param("name")
        tags: Optional[dict] = self._get_param("tags")
        service: VPCLatticeService = self.vpclattice_backend.create_service(
            auth_type=auth_type,
            certificate_arn=certificate_arn,
            client_token=client_token,
            custom_domain_name=custom_domain_name,
            name=name,
            tags=tags,
        )
        return json.dumps(service)

    
    def create_service_network(self):
        params = self._get_params()
        auth_type = params.get("authType")
        client_token = params.get("clientToken")
        name = params.get("name")
        sharing_config = params.get("sharingConfig")
        tags = params.get("tags")
        arn, auth_type, id, name, sharing_config = self.vpclattice_backend.create_service_network(
            auth_type=auth_type,
            client_token=client_token,
            name=name,
            sharing_config=sharing_config,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict(arn=arn, authType=auth_type, id=id, name=name, sharingConfig=sharing_config))
# add templates from here
    
    def create_service_network_vpc_association(self):
        params = self._get_params()
        client_token = params.get("clientToken")
        security_group_ids = params.get("securityGroupIds")
        service_network_identifier = params.get("serviceNetworkIdentifier")
        tags = params.get("tags")
        vpc_identifier = params.get("vpcIdentifier")
        arn, created_by, id, security_group_ids, status = self.vpclattice_backend.create_service_network_vpc_association(
            client_token=client_token,
            security_group_ids=security_group_ids,
            service_network_identifier=service_network_identifier,
            tags=tags,
            vpc_identifier=vpc_identifier,
        )
        # TODO: adjust response
        return json.dumps(dict(arn=arn, createdBy=created_by, id=id, securityGroupIds=security_group_ids, status=status))
    
    def create_rule(self):
        params = self._get_params()
        action = params.get("action")
        client_token = params.get("clientToken")
        listener_identifier = params.get("listenerIdentifier")
        match = params.get("match")
        name = params.get("name")
        priority = params.get("priority")
        service_identifier = params.get("serviceIdentifier")
        tags = params.get("tags")
        action, arn, id, match, name, priority = self.vpclattice_backend.create_rule(
            action=action,
            client_token=client_token,
            listener_identifier=listener_identifier,
            match=match,
            name=name,
            priority=priority,
            service_identifier=service_identifier,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict(action=action, arn=arn, id=id, match=match, name=name, priority=priority))
    
    def tag_resource(self):
        params = self._get_params()
        resource_arn = params.get("resourceArn")
        tags = params.get("tags")
        self.vpclattice_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict())
    
    def list_tags_for_resource(self):
        params = self._get_params()
        resource_arn = params.get("resourceArn")
        tags = self.vpclattice_backend.list_tags_for_resource(
            resource_arn=resource_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(tags=tags))
