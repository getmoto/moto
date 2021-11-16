"""Handles incoming route53resolver requests/responses."""
import json

from moto.core.exceptions import InvalidToken
from moto.core.responses import BaseResponse
from moto.route53resolver.exceptions import InvalidNextTokenException
from moto.route53resolver.models import route53resolver_backends
from moto.route53resolver.validations import validate_args


class Route53ResolverResponse(BaseResponse):
    """Handler for Route53Resolver requests and responses."""

    @property
    def route53resolver_backend(self):
        """Return backend instance specific for this region."""
        return route53resolver_backends[self.region]

    def create_resolver_endpoint(self):
        """Create an inbound or outbound Resolver endpoint."""
        creator_request_id = self._get_param("CreatorRequestId")
        name = self._get_param("Name")
        security_group_ids = self._get_param("SecurityGroupIds")
        direction = self._get_param("Direction")
        ip_addresses = self._get_param("IpAddresses")
        tags = self._get_param("Tags", [])
        resolver_endpoint = self.route53resolver_backend.create_resolver_endpoint(
            region=self.region,
            creator_request_id=creator_request_id,
            name=name,
            security_group_ids=security_group_ids,
            direction=direction,
            ip_addresses=ip_addresses,
            tags=tags,
        )
        return json.dumps({"ResolverEndpoint": resolver_endpoint.description()})

    def delete_resolver_endpoint(self):
        """Delete a Resolver endpoint."""
        resolver_endpoint_id = self._get_param("ResolverEndpointId")
        resolver_endpoint = self.route53resolver_backend.delete_resolver_endpoint(
            resolver_endpoint_id=resolver_endpoint_id,
        )
        return json.dumps({"ResolverEndpoint": resolver_endpoint.description()})

    def get_resolver_endpoint(self):
        """Return info about a specific Resolver endpoint."""
        resolver_endpoint_id = self._get_param("ResolverEndpointId")
        resolver_endpoint = self.route53resolver_backend.get_resolver_endpoint(
            resolver_endpoint_id=resolver_endpoint_id,
        )
        return json.dumps({"ResolverEndpoint": resolver_endpoint.description()})

    def list_resolver_endpoint_ip_addresses(self):
        """Returns list of IP addresses for specified Resolver endpoint."""
        resolver_endpoint_id = self._get_param("ResolverEndpointId")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults", 10)
        validate_args([("maxResults", max_results)])
        try:
            (
                ip_addresses,
                next_token,
            ) = self.route53resolver_backend.list_resolver_endpoint_ip_addresses(
                resolver_endpoint_id=resolver_endpoint_id,
                next_token=next_token,
                max_results=max_results,
            )
        except InvalidToken as exc:
            raise InvalidNextTokenException() from exc

        response = {
            "IpAddresses": ip_addresses,
            "MaxResults": max_results,
        }
        if next_token:
            response["NextToken"] = next_token
        return json.dumps(response)

    def list_resolver_endpoints(self):
        """Returns list of all Resolver endpoints, filtered if specified."""
        filters = self._get_param("Filters")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults", 10)
        validate_args([("maxResults", max_results)])
        try:
            (
                endpoints,
                next_token,
            ) = self.route53resolver_backend.list_resolver_endpoints(
                filters=filters, next_token=next_token, max_results=max_results
            )
        except InvalidToken as exc:
            raise InvalidNextTokenException() from exc

        response = {
            "ResolverEndpoints": [x.description() for x in endpoints],
            "MaxResults": max_results,
        }
        if next_token:
            response["NextToken"] = next_token
        return json.dumps(response)

    def list_tags_for_resource(self):
        """Lists all tags for the given resource."""
        resource_arn = self._get_param("ResourceArn")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")
        try:
            (tags, next_token) = self.route53resolver_backend.list_tags_for_resource(
                resource_arn=resource_arn,
                next_token=next_token,
                max_results=max_results,
            )
        except InvalidToken as exc:
            raise InvalidNextTokenException() from exc

        response = {"Tags": tags}
        if next_token:
            response["NextToken"] = next_token
        return json.dumps(response)

    def tag_resource(self):
        """Add one or more tags to a specified resource."""
        resource_arn = self._get_param("ResourceArn")
        tags = self._get_param("Tags")
        self.route53resolver_backend.tag_resource(resource_arn=resource_arn, tags=tags)
        return ""

    def untag_resource(self):
        """Removes one or more tags from the specified resource."""
        resource_arn = self._get_param("ResourceArn")
        tag_keys = self._get_param("TagKeys")
        self.route53resolver_backend.untag_resource(
            resource_arn=resource_arn, tag_keys=tag_keys
        )
        return ""

    def update_resolver_endpoint(self):
        """Update name of Resolver endpoint."""
        resolver_endpoint_id = self._get_param("ResolverEndpointId")
        name = self._get_param("Name")
        resolver_endpoint = self.route53resolver_backend.update_resolver_endpoint(
            resolver_endpoint_id=resolver_endpoint_id, name=name,
        )
        return json.dumps({"ResolverEndpoint": resolver_endpoint.description()})
