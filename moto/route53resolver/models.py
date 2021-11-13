"""Route53ResolverBackend class with methods for supported APIs."""
from datetime import datetime, timezone
from ipaddress import ip_address, ip_network

from boto3 import Session

from moto.core import ACCOUNT_ID
from moto.core import BaseBackend, BaseModel
from moto.core.utils import get_random_hex
from moto.ec2 import ec2_backends
from moto.ec2.exceptions import InvalidSubnetIdError
from moto.ec2.exceptions import InvalidSecurityGroupNotFoundError
from moto.route53resolver.exceptions import (
    InvalidParameterException,
    InvalidRequestException,
    # TODO LimitExceededException,
    ResourceExistsException,
    ResourceNotFoundException,
    TagValidationException,
)
from moto.route53resolver.utils import PAGINATION_MODEL
from moto.route53resolver.validations import (
    validate_args,
    validate_creator_request_id,
    validate_direction,
    validate_endpoint_id,
    validate_ip_addresses,
    validate_name,
    validate_security_group_ids,
    validate_subnets,
)

from moto.utilities.paginator import paginate
from moto.utilities.tagging_service import TaggingService


class ResolverEndpoint(BaseModel):  # pylint: disable=too-many-instance-attributes
    """Representation of a fake Route53 Resolver Endpoint."""

    MAX_TAGS_PER_RESOLVER_ENDPOINT = 200

    def __init__(
        self,
        region,
        endpoint_id,
        creator_request_id,
        security_group_ids,
        direction,
        ip_addresses,
        name=None,
    ):  # pylint: disable=too-many-arguments
        self.region = region
        self.creator_request_id = creator_request_id
        self.name = name
        self.security_group_ids = security_group_ids
        self.direction = direction
        self.ip_addresses = ip_addresses

        # Constructed members.
        self.id = endpoint_id  # pylint: disable=invalid-name

        # NOTE; This currently doesn't reflect IPv6 addresses and will
        # include reserved addresses.
        self.ip_address_count = len(ip_addresses)

        self.host_vpc_id = self._vpc_id_from_subnet()
        self.status = "OPERATIONAL"

        # The status message should contain a trace Id which is the value
        # of X-Amzn-Trace-Id.  We don't have that info, so a random number
        # of similar format and length will be used.
        self.status_message = (
            f"[Trace id: 1-{get_random_hex(8)}-{get_random_hex(24)}] "
            f"Creating the Resolver Endpoint"
        )

        self.creation_time = datetime.now(timezone.utc).isoformat()
        self.modification_time = datetime.now(timezone.utc).isoformat()

    @property
    def arn(self):
        """Return ARN for this resolver endpoint."""
        return f"arn:aws:route53resolver:{self.region}:{ACCOUNT_ID}:resolver-endpoint/{self.id}"

    def _vpc_id_from_subnet(self):
        """Return VPC Id associated with the subnet.

        The assumption is that all of the subnets are associated with the
        same VPC.  We don't check that assumption, but otherwise the existence
        of the subnets has already been checked.
        """
        first_subnet_id = self.ip_addresses[0]["SubnetId"]
        subnet_info = ec2_backends[self.region].get_all_subnets(
            subnet_ids=[first_subnet_id]
        )[0]
        return subnet_info.vpc_id

    def description(self):
        """Return a dictionary of relevant info for this resolver endpoint."""
        return {
            "Id": self.id,
            "CreatorRequestId": self.creator_request_id,
            "Arn": self.arn,
            "Name": self.name,
            "SecurityGroupIds": self.security_group_ids,
            "Direction": self.direction,
            "IpAddressCount": self.ip_address_count,
            "HostVPCId": self.host_vpc_id,
            "Status": self.status,
            "StatusMessage": self.status_message,
            "CreationTime": self.creation_time,
            "ModificationTime": self.modification_time,
        }

    def update_name(self, name):
        """Replace existing name with new name."""
        self.name = name
        self.modification_time = datetime.now(timezone.utc).isoformat()


class Route53ResolverBackend(BaseBackend):
    """Implementation of Route53Resolver APIs."""

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.resolver_endpoints = {}  # Key is self-generated ID (endpoint_id)
        self.tagger = TaggingService()

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """List of dicts representing default VPC endpoints for this service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "route53resolver"
        )

    @staticmethod
    def _verify_subnet_ips(region, ip_addresses):
        """Perform additional checks on the IPAddresses.

        NOTE: This does not check if the IP is reserved and doesn't include
        IPv6 addresses.
        """
        if len(ip_addresses) < 2:
            raise InvalidRequestException(
                "Resolver endpoint needs to have at least 2 IP addresses"
            )

        for subnet_id, ip_addr in [(x["SubnetId"], x["Ip"]) for x in ip_addresses]:
            try:
                subnet_info = ec2_backends[region].get_all_subnets(
                    subnet_ids=[subnet_id]
                )[0]
            except InvalidSubnetIdError as exc:
                raise InvalidParameterException(
                    f"The subnet ID '{subnet_id}' does not exist"
                ) from exc

            # IP in IPv4 CIDR range?
            if not ip_address(ip_addr) in ip_network(subnet_info.cidr_block):
                raise InvalidRequestException(
                    f"IP address '{ip_addr}' is either not in subnet "
                    f"'{subnet_id}' CIDR range or is reserved"
                )

            # NOTE:  IPv6 and reserved IPs are currently not being filtered.
            # Not sure if this is the correct way or the best way to check
            # if the IP is within an IPv6 CIDR.
            # ipv6_cidr_info = subnet_info.ipv6_cidr_block_associations
            # if not ipv6_cidr_info:
            #     continue
            #
            # for ipv6_cidr in ipv6_cidr_info:
            #     if ipv6_cidr_info.ipv6_cidr_block_state == "associated" and ip_address(
            #         ip_addr
            #     ) in ip_network(ipv6_cidr_info.cidr_block):
            #         break
            # else:
            #     raise InvalidRequestException(
            #         f'IP address "{ip_addr}" is either not in subnet '
            #         f'"{subnet_id}" CIDR range or is reserved.'
            #     )

    @staticmethod
    def _verify_security_group_ids(region, security_group_ids):
        """Perform additional checks on the security groups."""
        if len(security_group_ids) > 10:
            raise InvalidParameterException("Maximum of 10 security groups are allowed")

        for group_id in security_group_ids:
            if not group_id.startswith("sg-"):
                raise InvalidParameterException(
                    f"Malformed security group ID: Invalid id: '{group_id}' "
                    f"(expecting 'sg-...')"
                )
            try:
                ec2_backends[region].describe_security_groups(group_ids=[group_id])
            except InvalidSecurityGroupNotFoundError as exc:
                raise ResourceNotFoundException(
                    f"The security group '{group_id}' does not exist"
                ) from exc

    def create_resolver_endpoint(
        self,
        region,
        creator_request_id,
        name,
        security_group_ids,
        direction,
        ip_addresses,
        tags,
    ):  # pylint: disable=too-many-arguments
        """Return description for a newly created resolver endpoint.

        NOTE:  IPv6 and reserved IPs are currently not being filtered when
        calculating the create_resolver_endpoint() IpAddresses.
        """
        validate_args(
            [
                (validate_creator_request_id, "creatorRequestId", creator_request_id),
                (validate_direction, "direction", direction),
                (validate_ip_addresses, "ipAddresses", ip_addresses),
                (validate_name, "name", name),
                (validate_security_group_ids, "securityGroupIds", security_group_ids),
                (validate_subnets, "ipAddresses.subnetId", ip_addresses),
            ]
        )
        errmsg = self.tagger.validate_tags(
            tags or [], limit=ResolverEndpoint.MAX_TAGS_PER_RESOLVER_ENDPOINT,
        )
        if errmsg:
            raise TagValidationException(errmsg)
        self._verify_subnet_ips(region, ip_addresses)
        self._verify_security_group_ids(region, security_group_ids)

        if creator_request_id in [
            x.creator_request_id for x in self.resolver_endpoints.values()
        ]:
            raise ResourceExistsException(
                f"Resolver endpoint with creator request ID "
                f"'{creator_request_id}' already exists"
            )

        endpoint_id = (
            f"rslvr-{'in' if direction == 'INBOUND' else 'out'}-{get_random_hex(17)}"
        )
        resolver_endpoint = ResolverEndpoint(
            region,
            endpoint_id,
            creator_request_id,
            security_group_ids,
            direction,
            ip_addresses,
            name,
        )
        self.resolver_endpoints[endpoint_id] = resolver_endpoint
        self.tagger.tag_resource(resolver_endpoint.arn, tags or [])
        return resolver_endpoint

    def _validate_resolver_endpoint_id(self, resolver_endpoint_id):
        """Raise an exception if the id is invalid or unknown."""
        validate_args(
            [(validate_endpoint_id, "resolverEndpointId", resolver_endpoint_id)]
        )
        if resolver_endpoint_id not in self.resolver_endpoints:
            raise ResourceNotFoundException(
                f"Resolver endpoint with ID '{resolver_endpoint_id}' does not exist"
            )

    def delete_resolver_endpoint(self, resolver_endpoint_id):
        """Delete a resolver endpoint."""
        self._validate_resolver_endpoint_id(resolver_endpoint_id)
        self.tagger.delete_all_tags_for_resource(resolver_endpoint_id)
        resolver_endpoint = self.resolver_endpoints.pop(resolver_endpoint_id)
        resolver_endpoint.status = "DELETING"
        resolver_endpoint.status_message = resolver_endpoint.status_message.replace(
            "Creating", "Deleting"
        )
        return resolver_endpoint

    def get_resolver_endpoint(self, resolver_endpoint_id):
        """Return info for specified resolver endpoint."""
        self._validate_resolver_endpoint_id(resolver_endpoint_id)
        return self.resolver_endpoints[resolver_endpoint_id]

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_tags_for_resource(
        self, resource_arn, next_token=None, max_results=None,
    ):  # pylint: disable=unused-argument
        """List all tags for the given resource."""
        self._matched_arn(resource_arn)
        return self.tagger.list_tags_for_resource(resource_arn).get("Tags")

    def _matched_arn(self, resource_arn):
        """Given ARN, raise exception if there is no corresponding resource."""
        for resolver_endpoint in self.resolver_endpoints.values():
            if resolver_endpoint.arn == resource_arn:
                return
        raise ResourceNotFoundException(
            f"Resolver endpoint with ID '{resource_arn}' does not exist"
        )

    def tag_resource(self, resource_arn, tags):
        """Add or overwrite one or more tags for specified resource."""
        self._matched_arn(resource_arn)
        errmsg = self.tagger.validate_tags(
            tags, limit=ResolverEndpoint.MAX_TAGS_PER_RESOLVER_ENDPOINT,
        )
        if errmsg:
            raise TagValidationException(errmsg)
        self.tagger.tag_resource(resource_arn, tags)

    def untag_resource(self, resource_arn, tag_keys):
        """Removes tags from a resource."""
        self._matched_arn(resource_arn)
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def update_resolver_endpoint(self, resolver_endpoint_id, name):
        """Update name of Resolver endpoint."""
        self._validate_resolver_endpoint_id(resolver_endpoint_id)
        validate_args([(validate_name, "name", name)])
        resolver_endpoint = self.resolver_endpoints[resolver_endpoint_id]
        resolver_endpoint.update_name(name)
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
