"""Handles incoming route53resolver requests/responses."""
import json

from moto.core.responses import BaseResponse
from .models import route53resolver_backends


class Route53ResolverResponse(BaseResponse):
    """Handler for Route53Resolver requests and responses."""

    @property
    def route53resolver_backend(self):
        """Return backend instance specific for this region."""
        return route53resolver_backends[self.region]

    def create_resolver_endpoint(self):
        creator_request_id = self._get_param("CreatorRequestId")
        name = self._get_param("Name")
        security_group_ids = self._get_list_prefix("SecurityGroupIds.member")
        direction = self._get_param("Direction")
        ip_addresses = self._get_list_prefix("IpAddresses.member")
        tags = self._get_list_prefix("Tags.member")
        resolver_endpoint = self.route53resolver_backend.create_resolver_endpoint(
            creator_request_id=creator_request_id,
            name=name,
            security_group_ids=security_group_ids,
            direction=direction,
            ip_addresses=ip_addresses,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict(resolverEndpoint=resolver_endpoint))

    def get_resolver_endpoint(self):
        resolver_endpoint_id = self._get_param("ResolverEndpointId")
        resolver_endpoint = self.route53resolver_backend.get_resolver_endpoint(
            resolver_endpoint_id=resolver_endpoint_id,
        )
        # TODO: adjust response
        return json.dumps(dict(resolverEndpoint=resolver_endpoint))

    def delete_resolver_endpoint(self):
        resolver_endpoint_id = self._get_param("ResolverEndpointId")
        resolver_endpoint = self.route53resolver_backend.delete_resolver_endpoint(
            resolver_endpoint_id=resolver_endpoint_id,
        )
        # TODO: adjust response
        return json.dumps(dict(resolverEndpoint=resolver_endpoint))
