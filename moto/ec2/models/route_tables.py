import ipaddress

from moto.core import CloudFormationModel
from .core import TaggedEC2Resource
from ..exceptions import (
    DependencyViolationError,
    InvalidRouteError,
    InvalidRouteTableIdError,
    InvalidAssociationIdError,
    InvalidDestinationCIDRBlockParameterError,
    RouteAlreadyExistsError,
)
from ..utils import (
    EC2_RESOURCE_TO_PREFIX,
    generate_route_id,
    generic_filter,
    random_subnet_association_id,
    random_route_table_id,
    split_route_id,
)


class RouteTable(TaggedEC2Resource, CloudFormationModel):
    def __init__(self, ec2_backend, route_table_id, vpc_id, main=False):
        self.ec2_backend = ec2_backend
        self.id = route_table_id
        self.vpc_id = vpc_id
        self.main = main
        self.main_association = random_subnet_association_id()
        self.associations = {}
        self.routes = {}

    @property
    def owner_id(self):
        return self.ec2_backend.account_id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-routetable.html
        return "AWS::EC2::RouteTable"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        from ..models import ec2_backends

        properties = cloudformation_json["Properties"]

        vpc_id = properties["VpcId"]
        ec2_backend = ec2_backends[account_id][region_name]
        route_table = ec2_backend.create_route_table(vpc_id=vpc_id)
        return route_table

    @property
    def physical_resource_id(self):
        return self.id

    def get_filter_value(self, filter_name):
        if filter_name == "association.main":
            # Note: Boto only supports 'true'.
            # https://github.com/boto/boto/issues/1742
            if self.main:
                return "true"
            else:
                return "false"
        elif filter_name == "route-table-id":
            return self.id
        elif filter_name == "vpc-id":
            return self.vpc_id
        elif filter_name == "association.route-table-id":
            return self.id
        elif filter_name == "association.route-table-association-id":
            return self.associations.keys()
        elif filter_name == "association.subnet-id":
            return self.associations.values()
        elif filter_name == "route.gateway-id":
            return [
                route.gateway.id
                for route in self.routes.values()
                if route.gateway is not None
            ]
        else:
            return super().get_filter_value(filter_name, "DescribeRouteTables")


class RouteTableBackend:
    def __init__(self):
        self.route_tables = {}

    def create_route_table(self, vpc_id, tags=None, main=False):
        route_table_id = random_route_table_id()
        vpc = self.get_vpc(vpc_id)  # Validate VPC exists
        route_table = RouteTable(self, route_table_id, vpc_id, main=main)
        for tag in tags or []:
            route_table.add_tag(tag.get("Key"), tag.get("Value"))
        self.route_tables[route_table_id] = route_table

        # creating default routes for ipv4 cirds
        ipv4_cidrs = vpc.get_cidr_block_association_set(ipv6=False)
        for ipv4_cidr in ipv4_cidrs:
            self.create_route(route_table_id, ipv4_cidr.get("cidr_block"), local=True)

        # creating default routes for ipv6 cidrs
        ipv6_cidrs = vpc.get_cidr_block_association_set(ipv6=True)
        for ipv6_cidr in ipv6_cidrs:
            self.create_route(
                route_table_id,
                destination_cidr_block=None,
                local=True,
                destination_ipv6_cidr_block=ipv6_cidr.get("cidr_block"),
            )

        return route_table

    def get_route_table(self, route_table_id):
        route_table = self.route_tables.get(route_table_id, None)
        if not route_table:
            raise InvalidRouteTableIdError(route_table_id)
        return route_table

    def describe_route_tables(self, route_table_ids=None, filters=None):
        route_tables = self.route_tables.copy().values()

        if route_table_ids:
            route_tables = [
                route_table
                for route_table in route_tables
                if route_table.id in route_table_ids
            ]
            if len(route_tables) != len(route_table_ids):
                invalid_id = list(
                    set(route_table_ids).difference(
                        set([route_table.id for route_table in route_tables])
                    )
                )[0]
                raise InvalidRouteTableIdError(invalid_id)

        return generic_filter(filters, route_tables)

    def delete_route_table(self, route_table_id):
        route_table = self.get_route_table(route_table_id)
        if route_table.associations:
            raise DependencyViolationError(
                "The routeTable '{0}' has dependencies and cannot be deleted.".format(
                    route_table_id
                )
            )
        self.route_tables.pop(route_table_id)
        return True

    def associate_route_table(self, route_table_id, gateway_id=None, subnet_id=None):
        # Idempotent if association already exists.
        route_tables_by_subnet = self.describe_route_tables(
            filters={"association.subnet-id": [subnet_id]}
        )
        if route_tables_by_subnet:
            for association_id, check_subnet_id in route_tables_by_subnet[
                0
            ].associations.items():
                if subnet_id == check_subnet_id:
                    return association_id

        # Association does not yet exist, so create it.
        route_table = self.get_route_table(route_table_id)
        if gateway_id is None:
            self.get_subnet(subnet_id)  # Validate subnet exists
            association_id = random_subnet_association_id()
            route_table.associations[association_id] = subnet_id
            return association_id
        if subnet_id is None:
            association_id = random_subnet_association_id()
            route_table.associations[association_id] = gateway_id
            return association_id

    def disassociate_route_table(self, association_id):
        for route_table in self.route_tables.values():
            if association_id in route_table.associations:
                return route_table.associations.pop(association_id, None)
        raise InvalidAssociationIdError(association_id)

    def replace_route_table_association(self, association_id, route_table_id):
        # Idempotent if association already exists.
        new_route_table = self.get_route_table(route_table_id)
        if association_id in new_route_table.associations:
            return association_id

        # Find route table which currently has the association, error if none.
        route_tables_by_association_id = self.describe_route_tables(
            filters={"association.route-table-association-id": [association_id]}
        )
        if not route_tables_by_association_id:
            raise InvalidAssociationIdError(association_id)

        # Remove existing association, create new one.
        previous_route_table = route_tables_by_association_id[0]
        subnet_id = previous_route_table.associations.pop(association_id, None)
        return self.associate_route_table(route_table_id, subnet_id)


# TODO: refractor to isloate class methods from backend logic
class Route(CloudFormationModel):
    def __init__(
        self,
        route_table,
        destination_cidr_block,
        destination_ipv6_cidr_block,
        destination_prefix_list=None,
        local=False,
        gateway=None,
        instance=None,
        nat_gateway=None,
        egress_only_igw=None,
        transit_gateway=None,
        interface=None,
        vpc_pcx=None,
        carrier_gateway=None,
    ):
        self.id = generate_route_id(
            route_table.id,
            destination_cidr_block,
            destination_ipv6_cidr_block,
            destination_prefix_list.id if destination_prefix_list else None,
        )
        self.route_table = route_table
        self.destination_cidr_block = destination_cidr_block
        self.destination_ipv6_cidr_block = destination_ipv6_cidr_block
        self.destination_prefix_list = destination_prefix_list
        self.local = local
        self.gateway = gateway
        self.instance = instance
        self.nat_gateway = nat_gateway
        self.egress_only_igw = egress_only_igw
        self.transit_gateway = transit_gateway
        self.interface = interface
        self.vpc_pcx = vpc_pcx
        self.carrier_gateway = carrier_gateway

    @property
    def physical_resource_id(self):
        return self.id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-route.html
        return "AWS::EC2::Route"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        from ..models import ec2_backends

        properties = cloudformation_json["Properties"]

        gateway_id = properties.get("GatewayId")
        instance_id = properties.get("InstanceId")
        interface_id = properties.get("NetworkInterfaceId")
        nat_gateway_id = properties.get("NatGatewayId")
        egress_only_igw_id = properties.get("EgressOnlyInternetGatewayId")
        transit_gateway_id = properties.get("TransitGatewayId")
        pcx_id = properties.get("VpcPeeringConnectionId")

        route_table_id = properties["RouteTableId"]
        ec2_backend = ec2_backends[account_id][region_name]
        route_table = ec2_backend.create_route(
            route_table_id=route_table_id,
            destination_cidr_block=properties.get("DestinationCidrBlock"),
            gateway_id=gateway_id,
            instance_id=instance_id,
            nat_gateway_id=nat_gateway_id,
            egress_only_igw_id=egress_only_igw_id,
            transit_gateway_id=transit_gateway_id,
            interface_id=interface_id,
            vpc_peering_connection_id=pcx_id,
        )
        return route_table


class RouteBackend:
    def create_route(
        self,
        route_table_id,
        destination_cidr_block,
        destination_ipv6_cidr_block=None,
        destination_prefix_list_id=None,
        local=False,
        gateway_id=None,
        instance_id=None,
        nat_gateway_id=None,
        egress_only_igw_id=None,
        transit_gateway_id=None,
        interface_id=None,
        vpc_peering_connection_id=None,
        carrier_gateway_id=None,
    ):
        gateway = None
        nat_gateway = None
        transit_gateway = None
        egress_only_igw = None
        interface = None
        destination_prefix_list = None
        carrier_gateway = None

        route_table = self.get_route_table(route_table_id)

        if interface_id:
            # for validating interface Id whether it is valid or not.
            interface = self.get_network_interface(interface_id)

        else:
            if gateway_id:
                if EC2_RESOURCE_TO_PREFIX["vpn-gateway"] in gateway_id:
                    gateway = self.get_vpn_gateway(gateway_id)
                elif EC2_RESOURCE_TO_PREFIX["internet-gateway"] in gateway_id:
                    gateway = self.get_internet_gateway(gateway_id)
                elif EC2_RESOURCE_TO_PREFIX["vpc-endpoint"] in gateway_id:
                    gateway = self.get_vpc_end_point(gateway_id)

            if destination_cidr_block:
                self.__validate_destination_cidr_block(
                    destination_cidr_block, route_table
                )

            if nat_gateway_id is not None:
                nat_gateway = self.nat_gateways.get(nat_gateway_id)
            if egress_only_igw_id is not None:
                egress_only_igw = self.get_egress_only_igw(egress_only_igw_id)
            if transit_gateway_id is not None:
                transit_gateway = self.transit_gateways.get(transit_gateway_id)
            if destination_prefix_list_id is not None:
                destination_prefix_list = self.managed_prefix_lists.get(
                    destination_prefix_list_id
                )
            if carrier_gateway_id is not None:
                carrier_gateway = self.carrier_gateways.get(carrier_gateway_id)

        route = Route(
            route_table,
            destination_cidr_block,
            destination_ipv6_cidr_block,
            destination_prefix_list,
            local=local,
            gateway=gateway,
            instance=self.get_instance(instance_id) if instance_id else None,
            nat_gateway=nat_gateway,
            egress_only_igw=egress_only_igw,
            transit_gateway=transit_gateway,
            interface=interface,
            carrier_gateway=carrier_gateway,
            vpc_pcx=self.get_vpc_peering_connection(vpc_peering_connection_id)
            if vpc_peering_connection_id
            else None,
        )
        route_table.routes[route.id] = route
        return route

    def replace_route(
        self,
        route_table_id,
        destination_cidr_block,
        destination_ipv6_cidr_block=None,
        destination_prefix_list_id=None,
        nat_gateway_id=None,
        egress_only_igw_id=None,
        transit_gateway_id=None,
        gateway_id=None,
        instance_id=None,
        interface_id=None,
        vpc_peering_connection_id=None,
    ):
        route_table = self.get_route_table(route_table_id)
        route_id = generate_route_id(
            route_table.id, destination_cidr_block, destination_ipv6_cidr_block
        )
        route = route_table.routes[route_id]

        if interface_id:
            self.raise_not_implemented_error("ReplaceRoute to NetworkInterfaceId")

        route.gateway = None
        route.nat_gateway = None
        route.egress_only_igw = None
        route.transit_gateway = None
        if gateway_id:
            if EC2_RESOURCE_TO_PREFIX["vpn-gateway"] in gateway_id:
                route.gateway = self.get_vpn_gateway(gateway_id)
            elif EC2_RESOURCE_TO_PREFIX["internet-gateway"] in gateway_id:
                route.gateway = self.get_internet_gateway(gateway_id)

        if nat_gateway_id is not None:
            route.nat_gateway = self.nat_gateways.get(nat_gateway_id)
        if egress_only_igw_id is not None:
            route.egress_only_igw = self.get_egress_only_igw(egress_only_igw_id)
        if transit_gateway_id is not None:
            route.transit_gateway = self.transit_gateways.get(transit_gateway_id)
        if destination_prefix_list_id is not None:
            route.prefix_list = self.managed_prefix_lists.get(
                destination_prefix_list_id
            )

        route.instance = self.get_instance(instance_id) if instance_id else None
        route.interface = None
        route.vpc_pcx = (
            self.get_vpc_peering_connection(vpc_peering_connection_id)
            if vpc_peering_connection_id
            else None
        )

        route_table.routes[route.id] = route
        return route

    def get_route(self, route_id):
        route_table_id, _ = split_route_id(route_id)
        route_table = self.get_route_table(route_table_id)
        return route_table.get(route_id)

    def delete_route(
        self,
        route_table_id,
        destination_cidr_block,
        destination_ipv6_cidr_block=None,
        destination_prefix_list_id=None,
    ):
        cidr = destination_cidr_block
        route_table = self.get_route_table(route_table_id)
        if destination_ipv6_cidr_block:
            cidr = destination_ipv6_cidr_block
        if destination_prefix_list_id:
            cidr = destination_prefix_list_id
        route_id = generate_route_id(route_table_id, cidr)
        deleted = route_table.routes.pop(route_id, None)
        if not deleted:
            raise InvalidRouteError(route_table_id, cidr)
        return deleted

    def __validate_destination_cidr_block(self, destination_cidr_block, route_table):
        """
        Utility function to check the destination CIDR block
        Will validate the format and check for overlap with existing routes
        """
        try:
            ip_v4_network = ipaddress.IPv4Network(
                str(destination_cidr_block), strict=False
            )
        except ValueError:
            raise InvalidDestinationCIDRBlockParameterError(destination_cidr_block)

        if not route_table.routes:
            return
        for route in route_table.routes.values():
            if not route.destination_cidr_block:
                continue
            if not route.local and ip_v4_network.overlaps(
                ipaddress.IPv4Network(str(route.destination_cidr_block))
            ):
                raise RouteAlreadyExistsError(destination_cidr_block)
