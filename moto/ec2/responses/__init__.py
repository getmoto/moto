from __future__ import unicode_literals

from .account_attributes import AccountAttributes
from .amazon_dev_pay import AmazonDevPay
from .amis import AmisResponse
from .availability_zones_and_regions import AvailabilityZonesAndRegions
from .customer_gateways import CustomerGateways
from .dhcp_options import DHCPOptions
from .elastic_block_store import ElasticBlockStore
from .elastic_ip_addresses import ElasticIPAddresses
from .elastic_network_interfaces import ElasticNetworkInterfaces
from .general import General
from .instances import InstanceResponse
from .internet_gateways import InternetGateways
from .ip_addresses import IPAddresses
from .key_pairs import KeyPairs
from .launch_templates import LaunchTemplates
from .monitoring import Monitoring
from .network_acls import NetworkACLs
from .placement_groups import PlacementGroups
from .reserved_instances import ReservedInstances
from .route_tables import RouteTables
from .security_groups import SecurityGroups
from .spot_fleets import SpotFleets
from .spot_instances import SpotInstances
from .subnets import Subnets
from .tags import TagResponse
from .virtual_private_gateways import VirtualPrivateGateways
from .vm_export import VMExport
from .vm_import import VMImport
from .vpcs import VPCs
from .vpc_peering_connections import VPCPeeringConnections
from .vpn_connections import VPNConnections
from .windows import Windows
from .nat_gateways import NatGateways


class EC2Response(
    AccountAttributes,
    AmazonDevPay,
    AmisResponse,
    AvailabilityZonesAndRegions,
    CustomerGateways,
    DHCPOptions,
    ElasticBlockStore,
    ElasticIPAddresses,
    ElasticNetworkInterfaces,
    General,
    InstanceResponse,
    InternetGateways,
    IPAddresses,
    KeyPairs,
    LaunchTemplates,
    Monitoring,
    NetworkACLs,
    PlacementGroups,
    ReservedInstances,
    RouteTables,
    SecurityGroups,
    SpotFleets,
    SpotInstances,
    Subnets,
    TagResponse,
    VirtualPrivateGateways,
    VMExport,
    VMImport,
    VPCs,
    VPCPeeringConnections,
    VPNConnections,
    Windows,
    NatGateways,
):

    @property
    def ec2_backend(self):
        from moto.ec2.models import ec2_backends
        return ec2_backends[self.region]

    @property
    def should_autoescape(self):
        return True
