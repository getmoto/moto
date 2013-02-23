from urlparse import parse_qs

from moto.ec2.utils import camelcase_to_underscores, method_namess_from_class

from .amazon_dev_pay import AmazonDevPay
from .amis import AmisResponse
from .availability_zones_and_regions import AvailabilityZonesAndRegions
from .customer_gateways import CustomerGateways
from .dhcp_options import DHCPOptions
from .elastic_block_store import ElasticBlockStore
from .elastic_ip_addresses import ElasticIPAddresses
from .elastic_network_interfaces import ElasticNetworkInterfaces
from .general import General
from .internet_gateways import InternetGateways
from .ip_addresses import IPAddresses
from .key_pairs import KeyPairs
from .monitoring import Monitoring
from .network_acls import NetworkACLs
from .placement_groups import PlacementGroups
from .reserved_instances import ReservedInstances
from .route_tables import RouteTables
from .security_groups import SecurityGroups
from .spot_instances import SpotInstances
from .subnets import Subnets
from .virtual_private_gateways import VirtualPrivateGateways
from .vm_export import VMExport
from .vm_import import VMImport
from .vpcs import VPCs
from .vpn_connections import VPNConnections
from .windows import Windows

from .instances import InstanceResponse
from .tags import TagResponse


class EC2Response(object):

    sub_responses = [InstanceResponse, TagResponse, AmisResponse, AvailabilityZonesAndRegions, SecurityGroups]

    def dispatch(self, uri, body, headers):
        if body:
            querystring = parse_qs(body)
        else:
            querystring = parse_qs(headers)

        action = querystring['Action'][0]
        action = camelcase_to_underscores(action)

        for sub_response in self.sub_responses:
            method_names = method_namess_from_class(sub_response)
            if action in method_names:
                response = sub_response(querystring)
                method = getattr(response, action)
                return method()
        raise NotImplementedError("The {} action has not been implemented".format(action))
