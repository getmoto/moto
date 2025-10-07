import json

from moto.core.responses import BaseResponse
from urllib.parse import unquote

from .models import VPCLatticeBackend, vpclattice_backends
from typing import Dict, Tuple, Union

class VPCLatticeResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="vpc-lattice")

    @property
    def backend(self) -> VPCLatticeBackend:
        return vpclattice_backends[self.current_account][self.region]

    def create_service(self) -> str:
        service = self.backend.create_service(
            auth_type=self._get_param("authType"),
            certificate_arn=self._get_param("certificateArn"),
            client_token=self._get_param("clientToken"),
            custom_domain_name=self._get_param("customDomainName"),
            name=self._get_param("name"),
            tags=self._get_param("tags"),
        )
        return json.dumps(service.to_dict())

    def get_service(self) -> str:
        service = self.backend.get_service(
        service_identifier=unquote(self._get_param("serviceIdentifier"))
        )
        return json.dumps(service.to_dict())
    
    def list_services(self) -> str:
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        services, next_token = self.backend.list_services(max_results=max_results, next_token=next_token)
        return json.dumps({"items": services, "nextToken": next_token})
        
    def create_service_network(self) -> str:
        sn = self.backend.create_service_network(
            auth_type=self._get_param("authType"),
            client_token=self._get_param("clientToken"),
            name=self._get_param("name"),
            sharing_config=self._get_param("sharingConfig"),
            tags=self._get_param("tags"),
        )
        return json.dumps(sn.to_dict())

    def get_service_network(self) -> str:
        service = self.backend.get_service_network(
        service_network_identifier=unquote(self._get_param("serviceNetworkIdentifier"))
        )
        return json.dumps(service.to_dict())

    def list_service_networks(self) -> str:
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        service_networks, next_token = self.backend.list_service_networks(max_results=max_results, next_token=next_token)
        return json.dumps({"items": service_networks, "nextToken": next_token})


    def create_service_network_vpc_association(self) -> str:
        assoc = self.backend.create_service_network_vpc_association(
            client_token=self._get_param("clientToken"),
            security_group_ids=self._get_param("securityGroupIds"),
            service_network_identifier=self._get_param("serviceNetworkIdentifier"),
            tags=self._get_param("tags"),
            vpc_identifier=self._get_param("vpcIdentifier"),
        )
        return json.dumps(assoc.to_dict())

    def create_rule(self) -> str:
        rule = self.backend.create_rule(
            action=self._get_param("action"),
            client_token=self._get_param("clientToken"),
            listener_identifier=self._get_param("listenerIdentifier"),
            match=self._get_param("match"),
            name=self._get_param("name"),
            priority=self._get_param("priority"),
            service_identifier=self._get_param("serviceIdentifier"),
            tags=self._get_param("tags"),
        )
        return json.dumps(rule.to_dict())


    def list_tags_for_resource(self) -> Dict[str, str]:
        resource_arn = unquote(self._get_param("resourceArn"))
        tags = self.backend.list_tags_for_resource(resource_arn)
        return json.dumps({"tags": tags})
    
    def tag_resource(self) -> str:
        resource_arn = unquote(self._get_param("resourceArn"))
        tags = self._get_param("tags")
        self.backend.tag_resource(resource_arn, tags)
        return json.dumps({})
    
    def untag_resource(self) -> str:
        resource_arn = unquote(self._get_param("resourceArn"))
        tag_keys = self._get_param("tagKeys")
        self.backend.untag_resource(resource_arn=resource_arn, tag_keys=tag_keys)
        return json.dumps({})