from .account_attributes import AccountAttributes
from .amis import AmisResponse
from .availability_zones_and_regions import AvailabilityZonesAndRegions
from .customer_gateways import CustomerGateways
from .dhcp_options import DHCPOptions
from .elastic_block_store import ElasticBlockStore
from .elastic_ip_addresses import ElasticIPAddresses
from .elastic_network_interfaces import ElasticNetworkInterfaces
from .fleets import Fleets
from .general import General
from .hosts import HostsResponse
from .instances import InstanceResponse
from .internet_gateways import InternetGateways
from .egress_only_internet_gateways import EgressOnlyInternetGateway
from .ip_addresses import IPAddresses
from .key_pairs import KeyPairs
from .launch_templates import LaunchTemplates
from .monitoring import Monitoring
from .network_acls import NetworkACLs
from .reserved_instances import ReservedInstances
from .route_tables import RouteTables
from .security_groups import SecurityGroups
from .settings import Settings
from .spot_fleets import SpotFleets
from .spot_instances import SpotInstances
from .subnets import Subnets
from .flow_logs import FlowLogs
from .tags import TagResponse
from .virtual_private_gateways import VirtualPrivateGateways
from .vpcs import VPCs
from .vpc_service_configuration import VPCEndpointServiceConfiguration
from .vpc_peering_connections import VPCPeeringConnections
from .vpn_connections import VPNConnections
from .windows import Windows
from .nat_gateways import NatGateways
from .transit_gateways import TransitGateways
from .transit_gateway_route_tables import TransitGatewayRouteTable
from .transit_gateway_attachments import TransitGatewayAttachment
from .iam_instance_profiles import IamInstanceProfiles
from .carrier_gateways import CarrierGateway


class EC2Response(
    AccountAttributes,
    AmisResponse,
    AvailabilityZonesAndRegions,
    CustomerGateways,
    DHCPOptions,
    ElasticBlockStore,
    ElasticIPAddresses,
    ElasticNetworkInterfaces,
    Fleets,
    General,
    HostsResponse,
    InstanceResponse,
    InternetGateways,
    EgressOnlyInternetGateway,
    IPAddresses,
    KeyPairs,
    LaunchTemplates,
    Monitoring,
    NetworkACLs,
    ReservedInstances,
    RouteTables,
    SecurityGroups,
    Settings,
    SpotFleets,
    SpotInstances,
    Subnets,
    FlowLogs,
    TagResponse,
    VirtualPrivateGateways,
    VPCs,
    VPCEndpointServiceConfiguration,
    VPCPeeringConnections,
    VPNConnections,
    Windows,
    NatGateways,
    TransitGateways,
    TransitGatewayRouteTable,
    TransitGatewayAttachment,
    IamInstanceProfiles,
    CarrierGateway,
):
    def __init__(self) -> None:
        super().__init__(service_name="ec2")

    @property
    def should_autoescape(self) -> bool:
        return True
