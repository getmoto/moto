import ipaddress
import json
import weakref
from collections import defaultdict
from operator import itemgetter

from moto.core import CloudFormationModel
from .core import TaggedEC2Resource
from ..exceptions import (
    CidrLimitExceeded,
    UnsupportedTenancy,
    DefaultVpcAlreadyExists,
    DependencyViolationError,
    InvalidCIDRBlockParameterError,
    InvalidServiceName,
    InvalidFilter,
    InvalidNextToken,
    InvalidParameterValueError,
    InvalidVpcCidrBlockAssociationIdError,
    InvalidVPCIdError,
    InvalidVPCRangeError,
    OperationNotPermitted,
    InvalidVpcEndPointIdError,
)
from .availability_zones_and_regions import RegionsAndZonesBackend
from ..utils import (
    random_ipv6_cidr,
    random_vpc_ep_id,
    random_private_ip,
    create_dns_entries,
    random_vpc_id,
    random_vpc_cidr_association_id,
    generic_filter,
    utc_date_and_time,
)

MAX_NUMBER_OF_ENDPOINT_SERVICES_RESULTS = 1000
DEFAULT_VPC_ENDPOINT_SERVICES = []


class VPCEndPoint(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        endpoint_id,
        vpc_id,
        service_name,
        endpoint_type=None,
        policy_document=False,
        route_table_ids=None,
        subnet_ids=None,
        network_interface_ids=None,
        dns_entries=None,
        client_token=None,
        security_group_ids=None,
        tags=None,
        private_dns_enabled=None,
        destination_prefix_list_id=None,
    ):
        self.ec2_backend = ec2_backend
        self.id = endpoint_id
        self.vpc_id = vpc_id
        self.service_name = service_name
        self.endpoint_type = endpoint_type
        self.state = "available"
        self.policy_document = policy_document
        self.route_table_ids = route_table_ids
        self.network_interface_ids = network_interface_ids or []
        self.subnet_ids = subnet_ids
        self.client_token = client_token
        self.security_group_ids = security_group_ids
        self.private_dns_enabled = private_dns_enabled
        self.dns_entries = dns_entries
        self.add_tags(tags or {})
        self.destination_prefix_list_id = destination_prefix_list_id

        self.created_at = utc_date_and_time()

    def get_filter_value(self, filter_name):
        if filter_name in ("vpc-endpoint-type", "vpc_endpoint_type"):
            return self.endpoint_type
        else:
            return super().get_filter_value(filter_name, "DescribeVpcs")

    @property
    def owner_id(self):
        return self.ec2_backend.account_id

    @property
    def physical_resource_id(self):
        return self.id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        return "AWS::EC2::VPCEndpoint"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        from ..models import ec2_backends

        properties = cloudformation_json["Properties"]

        service_name = properties.get("ServiceName")
        subnet_ids = properties.get("SubnetIds")
        vpc_endpoint_type = properties.get("VpcEndpointType")
        vpc_id = properties.get("VpcId")
        policy_document = properties.get("PolicyDocument")
        private_dns_enabled = properties.get("PrivateDnsEnabled")
        route_table_ids = properties.get("RouteTableIds")
        security_group_ids = properties.get("SecurityGroupIds")

        ec2_backend = ec2_backends[account_id][region_name]
        vpc_endpoint = ec2_backend.create_vpc_endpoint(
            vpc_id=vpc_id,
            service_name=service_name,
            endpoint_type=vpc_endpoint_type,
            subnet_ids=subnet_ids,
            policy_document=policy_document,
            private_dns_enabled=private_dns_enabled,
            route_table_ids=route_table_ids,
            security_group_ids=security_group_ids,
        )
        return vpc_endpoint


class VPC(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        vpc_id,
        cidr_block,
        is_default,
        instance_tenancy="default",
        amazon_provided_ipv6_cidr_block=False,
        ipv6_cidr_block_network_border_group=None,
    ):

        self.ec2_backend = ec2_backend
        self.id = vpc_id
        self.cidr_block = cidr_block
        self.cidr_block_association_set = {}
        self.dhcp_options = None
        self.state = "available"
        self.instance_tenancy = instance_tenancy
        self.is_default = "true" if is_default else "false"
        self.enable_dns_support = "true"
        self.classic_link_enabled = "false"
        self.classic_link_dns_supported = "false"
        # This attribute is set to 'true' only for default VPCs
        # or VPCs created using the wizard of the VPC console
        self.enable_dns_hostnames = "true" if is_default else "false"

        self.associate_vpc_cidr_block(cidr_block)
        if amazon_provided_ipv6_cidr_block:
            self.associate_vpc_cidr_block(
                cidr_block,
                amazon_provided_ipv6_cidr_block=amazon_provided_ipv6_cidr_block,
                ipv6_cidr_block_network_border_group=ipv6_cidr_block_network_border_group,
            )

    @property
    def owner_id(self):
        return self.ec2_backend.account_id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-vpc.html
        return "AWS::EC2::VPC"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        from ..models import ec2_backends

        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[account_id][region_name]
        vpc = ec2_backend.create_vpc(
            cidr_block=properties["CidrBlock"],
            instance_tenancy=properties.get("InstanceTenancy", "default"),
        )
        for tag in properties.get("Tags", []):
            tag_key = tag["Key"]
            tag_value = tag["Value"]
            vpc.add_tag(tag_key, tag_value)

        return vpc

    @property
    def physical_resource_id(self):
        return self.id

    def get_filter_value(self, filter_name):
        if filter_name in ("vpc-id", "vpcId"):
            return self.id
        elif filter_name in ("cidr", "cidr-block", "cidrBlock"):
            return self.cidr_block
        elif filter_name in (
            "cidr-block-association.cidr-block",
            "ipv6-cidr-block-association.ipv6-cidr-block",
        ):
            return [
                c["cidr_block"]
                for c in self.get_cidr_block_association_set(ipv6="ipv6" in filter_name)
            ]
        elif filter_name in (
            "cidr-block-association.association-id",
            "ipv6-cidr-block-association.association-id",
        ):
            return self.cidr_block_association_set.keys()
        elif filter_name in (
            "cidr-block-association.state",
            "ipv6-cidr-block-association.state",
        ):
            return [
                c["cidr_block_state"]["state"]
                for c in self.get_cidr_block_association_set(ipv6="ipv6" in filter_name)
            ]
        elif filter_name in ("instance_tenancy", "InstanceTenancy"):
            return self.instance_tenancy
        elif filter_name in ("is-default", "isDefault"):
            return self.is_default
        elif filter_name == "state":
            return self.state
        elif filter_name in ("dhcp-options-id", "dhcpOptionsId"):
            if not self.dhcp_options:
                return None
            return self.dhcp_options.id
        else:
            return super().get_filter_value(filter_name, "DescribeVpcs")

    def modify_vpc_tenancy(self, tenancy):
        if tenancy != "default":
            raise UnsupportedTenancy(tenancy)
        self.instance_tenancy = tenancy
        return True

    def associate_vpc_cidr_block(
        self,
        cidr_block,
        amazon_provided_ipv6_cidr_block=False,
        ipv6_cidr_block_network_border_group=None,
    ):
        max_associations = 5 if not amazon_provided_ipv6_cidr_block else 1

        for cidr in self.cidr_block_association_set.copy():
            if (
                self.cidr_block_association_set.get(cidr)
                .get("cidr_block_state")
                .get("state")
                == "disassociated"
            ):
                self.cidr_block_association_set.pop(cidr)
        if (
            len(self.get_cidr_block_association_set(amazon_provided_ipv6_cidr_block))
            >= max_associations
        ):
            raise CidrLimitExceeded(self.id, max_associations)

        association_id = random_vpc_cidr_association_id()

        association_set = {
            "association_id": association_id,
            "cidr_block_state": {"state": "associated", "StatusMessage": ""},
        }

        association_set["cidr_block"] = (
            random_ipv6_cidr() if amazon_provided_ipv6_cidr_block else cidr_block
        )
        if amazon_provided_ipv6_cidr_block:
            association_set["ipv6_pool"] = "Amazon"
            association_set[
                "ipv6_cidr_block_network_border_group"
            ] = ipv6_cidr_block_network_border_group
        self.cidr_block_association_set[association_id] = association_set
        return association_set

    def enable_vpc_classic_link(self):
        # Check if current cidr block doesn't fall within the 10.0.0.0/8 block, excluding 10.0.0.0/16 and 10.1.0.0/16.
        # Doesn't check any route tables, maybe something for in the future?
        # See https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/vpc-classiclink.html#classiclink-limitations
        network_address = ipaddress.ip_network(self.cidr_block).network_address
        if (
            network_address not in ipaddress.ip_network("10.0.0.0/8")
            or network_address in ipaddress.ip_network("10.0.0.0/16")
            or network_address in ipaddress.ip_network("10.1.0.0/16")
        ):
            self.classic_link_enabled = "true"

        return self.classic_link_enabled

    def disable_vpc_classic_link(self):
        self.classic_link_enabled = "false"
        return self.classic_link_enabled

    def enable_vpc_classic_link_dns_support(self):
        self.classic_link_dns_supported = "true"
        return self.classic_link_dns_supported

    def disable_vpc_classic_link_dns_support(self):
        self.classic_link_dns_supported = "false"
        return self.classic_link_dns_supported

    def disassociate_vpc_cidr_block(self, association_id):
        if self.cidr_block == self.cidr_block_association_set.get(
            association_id, {}
        ).get("cidr_block"):
            raise OperationNotPermitted(association_id)

        entry = response = self.cidr_block_association_set.get(association_id, {})
        if entry:
            response = json.loads(json.dumps(entry))
            response["vpc_id"] = self.id
            response["cidr_block_state"]["state"] = "disassociating"
            entry["cidr_block_state"]["state"] = "disassociated"
        return response

    def get_cidr_block_association_set(self, ipv6=False):
        return [
            c
            for c in self.cidr_block_association_set.values()
            if ("::/" if ipv6 else ".") in c.get("cidr_block")
        ]


class VPCBackend:
    vpc_refs = defaultdict(set)

    def __init__(self):
        self.vpcs = {}
        self.vpc_end_points = {}
        self.vpc_refs[self.__class__].add(weakref.ref(self))

    def create_default_vpc(self):
        default_vpc = self.describe_vpcs(filters={"is-default": "true"})
        if default_vpc:
            raise DefaultVpcAlreadyExists
        cidr_block = "172.31.0.0/16"
        return self.create_vpc(cidr_block=cidr_block, is_default=True)

    def create_vpc(
        self,
        cidr_block,
        instance_tenancy="default",
        amazon_provided_ipv6_cidr_block=False,
        ipv6_cidr_block_network_border_group=None,
        tags=None,
        is_default=False,
    ):
        vpc_id = random_vpc_id()
        try:
            vpc_cidr_block = ipaddress.IPv4Network(str(cidr_block), strict=False)
        except ValueError:
            raise InvalidCIDRBlockParameterError(cidr_block)
        if vpc_cidr_block.prefixlen < 16 or vpc_cidr_block.prefixlen > 28:
            raise InvalidVPCRangeError(cidr_block)
        vpc = VPC(
            self,
            vpc_id,
            cidr_block,
            is_default=is_default,
            instance_tenancy=instance_tenancy,
            amazon_provided_ipv6_cidr_block=amazon_provided_ipv6_cidr_block,
            ipv6_cidr_block_network_border_group=ipv6_cidr_block_network_border_group,
        )

        for tag in tags or []:
            tag_key = tag.get("Key")
            tag_value = tag.get("Value")
            vpc.add_tag(tag_key, tag_value)

        self.vpcs[vpc_id] = vpc

        # AWS creates a default main route table and security group.
        self.create_route_table(vpc_id, main=True)

        # AWS creates a default Network ACL
        self.create_network_acl(vpc_id, default=True)

        default = self.get_security_group_from_name("default", vpc_id=vpc_id)
        if not default:
            self.create_security_group(
                "default", "default VPC security group", vpc_id=vpc_id, is_default=True
            )

        return vpc

    def get_vpc(self, vpc_id):
        if vpc_id not in self.vpcs:
            raise InvalidVPCIdError(vpc_id)
        return self.vpcs.get(vpc_id)

    def describe_vpcs(self, vpc_ids=None, filters=None):
        matches = self.vpcs.copy().values()
        if vpc_ids:
            matches = [vpc for vpc in matches if vpc.id in vpc_ids]
            if len(vpc_ids) > len(matches):
                unknown_ids = set(vpc_ids) - set(matches)
                raise InvalidVPCIdError(unknown_ids)
        if filters:
            matches = generic_filter(filters, matches)
        return matches

    def delete_vpc(self, vpc_id):
        # Do not delete if any VPN Gateway is attached
        vpn_gateways = self.describe_vpn_gateways(filters={"attachment.vpc-id": vpc_id})
        vpn_gateways = [
            item
            for item in vpn_gateways
            if item.attachments.get(vpc_id).state == "attached"
        ]
        if vpn_gateways:
            raise DependencyViolationError(
                "The vpc {0} has dependencies and cannot be deleted.".format(vpc_id)
            )

        # Delete route table if only main route table remains.
        route_tables = self.describe_route_tables(filters={"vpc-id": vpc_id})
        if len(route_tables) > 1:
            raise DependencyViolationError(
                "The vpc {0} has dependencies and cannot be deleted.".format(vpc_id)
            )
        for route_table in route_tables:
            self.delete_route_table(route_table.id)

        # Delete default security group if exists.
        default = self.get_security_group_by_name_or_id("default", vpc_id=vpc_id)
        if default:
            self.delete_security_group(group_id=default.id)

        # Now delete VPC.
        vpc = self.vpcs.pop(vpc_id, None)
        if not vpc:
            raise InvalidVPCIdError(vpc_id)

        if vpc.dhcp_options:
            vpc.dhcp_options.vpc = None
            self.delete_dhcp_options_set(vpc.dhcp_options.id)
            vpc.dhcp_options = None
        return vpc

    def describe_vpc_attribute(self, vpc_id, attr_name):
        vpc = self.get_vpc(vpc_id)
        if attr_name in ("enable_dns_support", "enable_dns_hostnames"):
            return getattr(vpc, attr_name)
        else:
            raise InvalidParameterValueError(attr_name)

    def modify_vpc_tenancy(self, vpc_id, tenancy):
        vpc = self.get_vpc(vpc_id)
        return vpc.modify_vpc_tenancy(tenancy)

    def enable_vpc_classic_link(self, vpc_id):
        vpc = self.get_vpc(vpc_id)
        return vpc.enable_vpc_classic_link()

    def disable_vpc_classic_link(self, vpc_id):
        vpc = self.get_vpc(vpc_id)
        return vpc.disable_vpc_classic_link()

    def enable_vpc_classic_link_dns_support(self, vpc_id):
        vpc = self.get_vpc(vpc_id)
        return vpc.enable_vpc_classic_link_dns_support()

    def disable_vpc_classic_link_dns_support(self, vpc_id):
        vpc = self.get_vpc(vpc_id)
        return vpc.disable_vpc_classic_link_dns_support()

    def modify_vpc_attribute(self, vpc_id, attr_name, attr_value):
        vpc = self.get_vpc(vpc_id)
        if attr_name in ("enable_dns_support", "enable_dns_hostnames"):
            setattr(vpc, attr_name, attr_value)
        else:
            raise InvalidParameterValueError(attr_name)

    def disassociate_vpc_cidr_block(self, association_id):
        for vpc in self.vpcs.copy().values():
            response = vpc.disassociate_vpc_cidr_block(association_id)
            for route_table in self.route_tables.copy().values():
                if route_table.vpc_id == response.get("vpc_id"):
                    if "::/" in response.get("cidr_block"):
                        self.delete_route(
                            route_table.id, None, response.get("cidr_block")
                        )
                    else:
                        self.delete_route(route_table.id, response.get("cidr_block"))
            if response:
                return response
        raise InvalidVpcCidrBlockAssociationIdError(association_id)

    def associate_vpc_cidr_block(
        self, vpc_id, cidr_block, amazon_provided_ipv6_cidr_block
    ):
        vpc = self.get_vpc(vpc_id)
        association_set = vpc.associate_vpc_cidr_block(
            cidr_block, amazon_provided_ipv6_cidr_block
        )
        for route_table in self.route_tables.copy().values():
            if route_table.vpc_id == vpc_id:
                if amazon_provided_ipv6_cidr_block:
                    self.create_route(
                        route_table.id,
                        None,
                        destination_ipv6_cidr_block=association_set["cidr_block"],
                        local=True,
                    )
                else:
                    self.create_route(
                        route_table.id, association_set["cidr_block"], local=True
                    )
        return association_set

    def create_vpc_endpoint(
        self,
        vpc_id,
        service_name,
        endpoint_type=None,
        policy_document=False,
        route_table_ids=None,
        subnet_ids=None,
        network_interface_ids=None,
        dns_entries=None,
        client_token=None,
        security_group_ids=None,
        tags=None,
        private_dns_enabled=None,
    ):

        vpc_endpoint_id = random_vpc_ep_id()

        # validates if vpc is present or not.
        self.get_vpc(vpc_id)
        destination_prefix_list_id = None

        if endpoint_type and endpoint_type.lower() == "interface":

            network_interface_ids = []
            for subnet_id in subnet_ids or []:
                self.get_subnet(subnet_id)
                eni = self.create_network_interface(subnet_id, random_private_ip())
                network_interface_ids.append(eni.id)

            dns_entries = create_dns_entries(service_name, vpc_endpoint_id)

        else:
            # considering gateway if type is not mentioned.
            for prefix_list in self.managed_prefix_lists.values():
                if prefix_list.prefix_list_name == service_name:
                    destination_prefix_list_id = prefix_list.id

        if dns_entries:
            dns_entries = [dns_entries]

        vpc_end_point = VPCEndPoint(
            self,
            vpc_endpoint_id,
            vpc_id,
            service_name,
            endpoint_type,
            policy_document,
            route_table_ids,
            subnet_ids,
            network_interface_ids,
            dns_entries,
            client_token,
            security_group_ids,
            tags,
            private_dns_enabled,
            destination_prefix_list_id,
        )

        self.vpc_end_points[vpc_endpoint_id] = vpc_end_point

        if destination_prefix_list_id:
            for route_table_id in route_table_ids:
                self.create_route(
                    route_table_id,
                    None,
                    gateway_id=vpc_endpoint_id,
                    destination_prefix_list_id=destination_prefix_list_id,
                )

        return vpc_end_point

    def delete_vpc_endpoints(self, vpce_ids=None):
        for vpce_id in vpce_ids or []:
            vpc_endpoint = self.vpc_end_points.get(vpce_id, None)
            if vpc_endpoint:
                if vpc_endpoint.endpoint_type.lower() == "interface":
                    for eni_id in vpc_endpoint.network_interface_ids:
                        self.enis.pop(eni_id, None)
                else:
                    for route_table_id in vpc_endpoint.route_table_ids:
                        self.delete_route(
                            route_table_id, vpc_endpoint.destination_prefix_list_id
                        )
                vpc_endpoint.state = "deleted"
        return True

    def describe_vpc_endpoints(self, vpc_end_point_ids, filters=None):
        vpc_end_points = self.vpc_end_points.values()

        if vpc_end_point_ids:
            vpc_end_points = [
                vpc_end_point
                for vpc_end_point in vpc_end_points
                if vpc_end_point.id in vpc_end_point_ids
            ]
            if len(vpc_end_points) != len(vpc_end_point_ids):
                invalid_id = list(
                    set(vpc_end_point_ids).difference(
                        set([vpc_end_point.id for vpc_end_point in vpc_end_points])
                    )
                )[0]
                raise InvalidVpcEndPointIdError(invalid_id)

        return generic_filter(filters, vpc_end_points)

    @staticmethod
    def _collect_default_endpoint_services(account_id, region):
        """Return list of default services using list of backends."""
        if DEFAULT_VPC_ENDPOINT_SERVICES:
            return DEFAULT_VPC_ENDPOINT_SERVICES

        zones = [
            zone.name
            for zones in RegionsAndZonesBackend.zones.values()
            for zone in zones
            if zone.name.startswith(region)
        ]

        from moto import backends  # pylint: disable=import-outside-toplevel

        for _backends in backends.service_backends():
            _backends = _backends[account_id]
            if region in _backends:
                service = _backends[region].default_vpc_endpoint_service(region, zones)
                if service:
                    DEFAULT_VPC_ENDPOINT_SERVICES.extend(service)

            if "global" in _backends:
                service = _backends["global"].default_vpc_endpoint_service(
                    region, zones
                )
                if service:
                    DEFAULT_VPC_ENDPOINT_SERVICES.extend(service)
        return DEFAULT_VPC_ENDPOINT_SERVICES

    @staticmethod
    def _matches_service_by_tags(service, filter_item):
        """Return True if service tags are not filtered by their tags.

        Note that the API specifies a key of "Values" for a filter, but
        the botocore library returns "Value" instead.
        """
        # For convenience, collect the tags for this service.
        service_tag_keys = {x["Key"] for x in service["Tags"]}
        if not service_tag_keys:
            return False

        matched = True  # assume the best
        if filter_item["Name"] == "tag-key":
            # Filters=[{"Name":"tag-key", "Values":["Name"]}],
            # Any tag with this name, regardless of the tag value.
            if not service_tag_keys & set(filter_item["Value"]):
                matched = False

        elif filter_item["Name"].startswith("tag:"):
            # Filters=[{"Name":"tag:Name", "Values":["my-load-balancer"]}],
            tag_name = filter_item["Name"].split(":")[1]
            if not service_tag_keys & {tag_name}:
                matched = False
            else:
                for tag in service["Tags"]:
                    if tag["Key"] == tag_name and tag["Value"] in filter_item["Value"]:
                        break
                else:
                    matched = False
        return matched

    @staticmethod
    def _filter_endpoint_services(service_names_filters, filters, services):
        """Return filtered list of VPC endpoint services."""
        if not service_names_filters and not filters:
            return services

        # Verify the filters are valid.
        for filter_item in filters:
            if filter_item["Name"] not in [
                "service-name",
                "service-type",
                "tag-key",
            ] and not filter_item["Name"].startswith("tag:"):
                raise InvalidFilter(filter_item["Name"])

        # Apply both the service_names filter and the filters themselves.
        filtered_services = []
        for service in services:
            if (
                service_names_filters
                and service["ServiceName"] not in service_names_filters
            ):
                continue

            # Note that the API specifies a key of "Values" for a filter, but
            # the botocore library returns "Value" instead.
            matched = True
            for filter_item in filters:
                if filter_item["Name"] == "service-name":
                    if service["ServiceName"] not in filter_item["Value"]:
                        matched = False

                elif filter_item["Name"] == "service-type":
                    service_types = {x["ServiceType"] for x in service["ServiceType"]}
                    if not service_types & set(filter_item["Value"]):
                        matched = False

                elif filter_item["Name"] == "tag-key" or filter_item["Name"].startswith(
                    "tag:"
                ):
                    if not VPCBackend._matches_service_by_tags(service, filter_item):
                        matched = False

                # Exit early -- don't bother checking the remaining filters
                # as a non-match was found.
                if not matched:
                    break

            # Does the service have a matching service name or does it match
            # a filter?
            if matched:
                filtered_services.append(service)

        return filtered_services

    def describe_vpc_endpoint_services(
        self, dry_run, service_names, filters, max_results, next_token, region
    ):  # pylint: disable=unused-argument,too-many-arguments
        """Return info on services to which you can create a VPC endpoint.

        Currently only the default endpoing services are returned.  When
        create_vpc_endpoint_service_configuration() is implemented, a
        list of those private endpoints would be kept and when this API
        is invoked, those private endpoints would be added to the list of
        default endpoint services.

        The DryRun parameter is ignored.
        """
        default_services = self._collect_default_endpoint_services(
            self.account_id, region
        )
        for service_name in service_names:
            if service_name not in [x["ServiceName"] for x in default_services]:
                raise InvalidServiceName(service_name)

        # Apply filters specified in the service_names and filters arguments.
        filtered_services = sorted(
            self._filter_endpoint_services(service_names, filters, default_services),
            key=itemgetter("ServiceName"),
        )

        # Determine the start index into list of services based on the
        # next_token argument.
        start = 0
        vpce_ids = [x["ServiceId"] for x in filtered_services]
        if next_token:
            if next_token not in vpce_ids:
                raise InvalidNextToken(next_token)
            start = vpce_ids.index(next_token)

        # Determine the stop index into the list of services based on the
        # max_results argument.
        if not max_results or max_results > MAX_NUMBER_OF_ENDPOINT_SERVICES_RESULTS:
            max_results = MAX_NUMBER_OF_ENDPOINT_SERVICES_RESULTS

        # If necessary, set the value of the next_token.
        next_token = ""
        if len(filtered_services) > (start + max_results):
            service = filtered_services[start + max_results]
            next_token = service["ServiceId"]

        return {
            "servicesDetails": filtered_services[start : start + max_results],
            "serviceNames": [
                x["ServiceName"] for x in filtered_services[start : start + max_results]
            ],
            "nextToken": next_token,
        }

    def get_vpc_end_point(self, vpc_end_point_id):
        vpc_end_point = self.vpc_end_points.get(vpc_end_point_id)
        if not vpc_end_point:
            raise InvalidVpcEndPointIdError(vpc_end_point_id)
        return vpc_end_point
