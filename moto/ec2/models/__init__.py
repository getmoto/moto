from moto.core import BaseBackend
from moto.core.utils import BackendDict
from ..exceptions import (
    EC2ClientError,
    InvalidID,
    MissingParameterError,
    MotoNotImplementedError,
)
from .amis import AmiBackend
from .carrier_gateways import CarrierGatewayBackend
from .customer_gateways import CustomerGatewayBackend
from .dhcp_options import DHCPOptionsSetBackend
from .elastic_block_store import EBSBackend
from .elastic_ip_addresses import ElasticAddressBackend
from .elastic_network_interfaces import NetworkInterfaceBackend
from .fleets import FleetsBackend
from .flow_logs import FlowLogsBackend
from .key_pairs import KeyPairBackend
from .launch_templates import LaunchTemplateBackend
from .managed_prefixes import ManagedPrefixListBackend
from .iam_instance_profile import IamInstanceProfileAssociationBackend
from .internet_gateways import (
    InternetGatewayBackend,
    EgressOnlyInternetGatewayBackend,
)
from .instances import InstanceBackend
from .instance_types import InstanceTypeBackend, InstanceTypeOfferingBackend
from .nat_gateways import NatGatewayBackend
from .network_acls import NetworkAclBackend
from .availability_zones_and_regions import RegionsAndZonesBackend
from .route_tables import RouteBackend, RouteTableBackend
from .security_groups import SecurityGroupBackend
from .spot_requests import (
    SpotRequestBackend,
    SpotPriceBackend,
    SpotFleetBackend,
)
from .subnets import SubnetBackend, SubnetRouteTableAssociationBackend
from .tags import TagBackend
from .transit_gateway import TransitGatewayBackend
from .transit_gateway_route_tables import (
    TransitGatewayRelationsBackend,
    TransitGatewayRouteTableBackend,
)
from .transit_gateway_attachments import TransitGatewayAttachmentBackend
from .vpn_gateway import VpnGatewayBackend
from .vpn_connections import VPNConnectionBackend
from .vpcs import VPCBackend
from .vpc_peering_connections import VPCPeeringConnectionBackend
from .vpc_service_configuration import VPCServiceConfigurationBackend
from ..utils import (
    EC2_RESOURCE_TO_PREFIX,
    is_valid_resource_id,
    get_prefix,
)


def validate_resource_ids(resource_ids):
    if not resource_ids:
        raise MissingParameterError(parameter="resourceIdSet")
    for resource_id in resource_ids:
        if not is_valid_resource_id(resource_id):
            raise InvalidID(resource_id=resource_id)
    return True


class SettingsBackend:
    def __init__(self):
        self.ebs_encryption_by_default = False

    def disable_ebs_encryption_by_default(self):
        ec2_backend = ec2_backends[self.account_id][self.region_name]
        ec2_backend.ebs_encryption_by_default = False

    def enable_ebs_encryption_by_default(self):
        ec2_backend = ec2_backends[self.account_id][self.region_name]
        ec2_backend.ebs_encryption_by_default = True

    def get_ebs_encryption_by_default(self):
        ec2_backend = ec2_backends[self.account_id][self.region_name]
        return ec2_backend.ebs_encryption_by_default


class EC2Backend(
    BaseBackend,
    InstanceBackend,
    InstanceTypeBackend,
    InstanceTypeOfferingBackend,
    TagBackend,
    EBSBackend,
    RegionsAndZonesBackend,
    AmiBackend,
    SecurityGroupBackend,
    VPCBackend,
    ManagedPrefixListBackend,
    SubnetBackend,
    SubnetRouteTableAssociationBackend,
    FlowLogsBackend,
    NetworkInterfaceBackend,
    VPNConnectionBackend,
    VPCServiceConfigurationBackend,
    VPCPeeringConnectionBackend,
    RouteTableBackend,
    RouteBackend,
    InternetGatewayBackend,
    EgressOnlyInternetGatewayBackend,
    SpotFleetBackend,
    SpotRequestBackend,
    SpotPriceBackend,
    ElasticAddressBackend,
    KeyPairBackend,
    SettingsBackend,
    DHCPOptionsSetBackend,
    NetworkAclBackend,
    VpnGatewayBackend,
    CustomerGatewayBackend,
    NatGatewayBackend,
    TransitGatewayBackend,
    TransitGatewayRouteTableBackend,
    TransitGatewayAttachmentBackend,
    TransitGatewayRelationsBackend,
    LaunchTemplateBackend,
    IamInstanceProfileAssociationBackend,
    CarrierGatewayBackend,
    FleetsBackend,
):
    """
    Implementation of the AWS EC2 endpoint.

    moto includes a limited set of AMIs in `moto/ec2/resources/amis.json`.  If you require specific
    AMIs to be available during your tests, you can provide your own AMI definitions by setting the
    environment variable `MOTO_AMIS_PATH` to point to a JSON file containing definitions of the
    required AMIs.

    To create such a file, refer to `scripts/get_amis.py`

    .. note:: You must set `MOTO_AMIS_PATH` before importing moto.

    """

    def __init__(self, region_name, account_id):
        BaseBackend.__init__(self, region_name, account_id)
        for backend in EC2Backend.__mro__:
            if backend not in [EC2Backend, BaseBackend, object]:
                backend.__init__(self)

        # Default VPC exists by default, which is the current behavior
        # of EC2-VPC. See for detail:
        #
        #   docs.aws.amazon.com/AmazonVPC/latest/UserGuide/default-vpc.html
        #
        if not self.vpcs:
            vpc = self.create_default_vpc()
        else:
            # For now this is included for potential
            # backward-compatibility issues
            vpc = self.vpcs.values()[0]

        self.default_vpc = vpc

        # Create default subnet for each availability zone
        ip, _ = vpc.cidr_block.split("/")
        ip = ip.split(".")
        ip[2] = 0

        for zone in self.describe_availability_zones():
            az_name = zone.name
            cidr_block = ".".join(str(i) for i in ip) + "/20"
            self.create_subnet(vpc.id, cidr_block, availability_zone=az_name)
            ip[2] += 16

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "ec2"
        ) + BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "ec2messages"
        )

    # Use this to generate a proper error template response when in a response
    # handler.
    def raise_error(self, code, message):
        raise EC2ClientError(code, message)

    def raise_not_implemented_error(self, blurb):
        raise MotoNotImplementedError(blurb)

    def do_resources_exist(self, resource_ids):
        for resource_id in resource_ids:
            resource_prefix = get_prefix(resource_id)
            if resource_prefix == EC2_RESOURCE_TO_PREFIX["customer-gateway"]:
                self.get_customer_gateway(customer_gateway_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["dhcp-options"]:
                self.describe_dhcp_options(dhcp_options_ids=[resource_id])
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["image"]:
                self.describe_images(ami_ids=[resource_id])
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["instance"]:
                self.get_instance_by_id(instance_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["internet-gateway"]:
                self.describe_internet_gateways(internet_gateway_ids=[resource_id])
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["launch-template"]:
                self.get_launch_template(resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["network-acl"]:
                self.get_all_network_acls()
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["network-interface"]:
                self.describe_network_interfaces(
                    filters={"network-interface-id": resource_id}
                )
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["reserved-instance"]:
                self.raise_not_implemented_error("DescribeReservedInstances")
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["route-table"]:
                self.get_route_table(route_table_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["security-group"]:
                self.describe_security_groups(group_ids=[resource_id])
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["snapshot"]:
                self.get_snapshot(snapshot_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["spot-instance-request"]:
                self.describe_spot_instance_requests(
                    filters={"spot-instance-request-id": resource_id}
                )
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["subnet"]:
                self.get_subnet(subnet_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["volume"]:
                self.get_volume(volume_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["vpc"]:
                self.get_vpc(vpc_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["vpc-endpoint-service"]:
                self.get_vpc_endpoint_service(resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["vpc-peering-connection"]:
                self.get_vpc_peering_connection(vpc_pcx_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["vpn-connection"]:
                self.describe_vpn_connections(vpn_connection_ids=[resource_id])
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX["vpn-gateway"]:
                self.get_vpn_gateway(vpn_gateway_id=resource_id)
            elif (
                resource_prefix
                == EC2_RESOURCE_TO_PREFIX["iam-instance-profile-association"]
            ):
                self.describe_iam_instance_profile_associations(
                    association_ids=[resource_id]
                )
        return True


ec2_backends = BackendDict(EC2Backend, "ec2")
