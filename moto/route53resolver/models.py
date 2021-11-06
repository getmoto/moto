"""Route53ResolverBackend class with methods for supported APIs."""
from boto3 import Session

from moto.core import BaseBackend, BaseModel


class Route53ResolverBackend(BaseBackend):
    """Implementation of Route53Resolver APIs."""

    def __init__(self, region_name=None):
        self.region_name = region_name

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_resolver_endpoint(
        self,
        creator_request_id,
        name,
        security_group_ids,
        direction,
        ip_addresses,
        tags,
    ):
        # implement here
        return resolver_endpoint

    def get_resolver_endpoint(self, resolver_endpoint_id):
        # implement here
        return resolver_endpoint

    def delete_resolver_endpoint(self, resolver_endpoint_id):
        # implement here
        return resolver_endpoint


route53resolver_backends = {}
for available_region in Session().get_available_regions("route53resolver"):
    route53resolver_backends[available_region] = Route53ResolverBackend(
        available_region
    )
for available_region in Session().get_available_regions(
    "route53resolver", partition_name="aws-us-gov"
):
    route53resolver_backends[available_region] = Route53ResolverBackend(
        available_region
    )
for available_region in Session().get_available_regions(
    "route53resolver", partition_name="aws-cn"
):
    route53resolver_backends[available_region] = Route53ResolverBackend(
        available_region
    )
