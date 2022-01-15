import copy
import ipaddress
import itertools
import json
import pathlib
import re
import warnings
import weakref
from collections import OrderedDict
from collections import defaultdict
from datetime import datetime
from operator import itemgetter
from os import environ
from os import listdir

from boto3 import Session

from moto.core import ACCOUNT_ID
from moto.core import BaseBackend
from moto.core.models import Model, BaseModel, CloudFormationModel
from moto.core.utils import (
    iso_8601_datetime_with_milliseconds,
    camelcase_to_underscores,
    aws_api_matches,
    BackendDict,
)
from moto.kms import kms_backends
from moto.packages.boto.ec2.blockdevicemapping import (
    BlockDeviceMapping,
    BlockDeviceType,
)
from moto.packages.boto.ec2.instance import Instance as BotoInstance, Reservation
from moto.packages.boto.ec2.launchspecification import LaunchSpecification
from moto.packages.boto.ec2.spotinstancerequest import (
    SpotInstanceRequest as BotoSpotRequest,
)
from moto.utilities.utils import load_resource, merge_multiple_dicts, filter_resources
from .exceptions import (
    CidrLimitExceeded,
    GenericInvalidParameterValueError,
    UnsupportedTenancy,
    DependencyViolationError,
    EC2ClientError,
    FilterNotImplementedError,
    FlowLogAlreadyExists,
    GatewayNotAttachedError,
    InvalidAddressError,
    InvalidAllocationIdError,
    InvalidAMIIdError,
    InvalidAMIAttributeItemValueError,
    InvalidAssociationIdError,
    InvalidAvailabilityZoneError,
    InvalidCIDRBlockParameterError,
    InvalidCIDRSubnetError,
    InvalidCustomerGatewayIdError,
    InvalidDestinationCIDRBlockParameterError,
    InvalidDHCPOptionsIdError,
    InvalidDomainError,
    InvalidID,
    InvalidInstanceIdError,
    InvalidInstanceTypeError,
    InvalidInternetGatewayIdError,
    InvalidKeyPairDuplicateError,
    InvalidKeyPairFormatError,
    InvalidKeyPairNameError,
    InvalidAggregationIntervalParameterError,
    InvalidServiceName,
    InvalidFilter,
    InvalidNextToken,
    InvalidDependantParameterError,
    InvalidDependantParameterTypeError,
    InvalidFlowLogIdError,
    InvalidLaunchTemplateNameError,
    InvalidNetworkAclIdError,
    InvalidNetworkAttachmentIdError,
    InvalidNetworkInterfaceIdError,
    InvalidParameterValueError,
    InvalidParameterValueErrorTagNull,
    InvalidParameterValueErrorUnknownAttribute,
    InvalidPermissionNotFoundError,
    InvalidPermissionDuplicateError,
    InvalidRouteTableIdError,
    InvalidRouteError,
    InvalidSecurityGroupDuplicateError,
    InvalidSecurityGroupNotFoundError,
    InvalidSnapshotIdError,
    InvalidSnapshotInUse,
    InvalidSubnetConflictError,
    InvalidSubnetIdError,
    InvalidSubnetRangeError,
    InvalidVolumeIdError,
    VolumeInUseError,
    InvalidVolumeAttachmentError,
    InvalidVolumeDetachmentError,
    InvalidVpcCidrBlockAssociationIdError,
    InvalidVPCPeeringConnectionIdError,
    InvalidVPCPeeringConnectionStateTransitionError,
    InvalidVPCIdError,
    InvalidVPCRangeError,
    InvalidVpnGatewayIdError,
    InvalidVpnGatewayAttachmentError,
    InvalidVpnConnectionIdError,
    InvalidSubnetCidrBlockAssociationID,
    MalformedAMIIdError,
    MalformedDHCPOptionsIdError,
    MissingParameterError,
    MotoNotImplementedError,
    NetworkAclEntryAlreadyExistsError,
    OperationNotPermitted,
    OperationNotPermitted2,
    OperationNotPermitted3,
    OperationNotPermitted4,
    ResourceAlreadyAssociatedError,
    RulesPerSecurityGroupLimitExceededError,
    TagLimitExceeded,
    InvalidParameterDependency,
    IncorrectStateIamProfileAssociationError,
    InvalidAssociationIDIamProfileAssociationError,
    InvalidVpcEndPointIdError,
    InvalidTaggableResourceType,
    InvalidGatewayIDError,
    InvalidCarrierGatewayID,
)
from .utils import (
    EC2_RESOURCE_TO_PREFIX,
    EC2_PREFIX_TO_RESOURCE,
    random_ami_id,
    random_dhcp_option_id,
    random_eip_allocation_id,
    random_eip_association_id,
    random_eni_attach_id,
    random_eni_id,
    random_instance_id,
    random_internet_gateway_id,
    random_egress_only_internet_gateway_id,
    random_ip,
    generate_dns_from_ip,
    random_mac_address,
    random_ipv6_cidr,
    random_transit_gateway_attachment_id,
    random_transit_gateway_route_table_id,
    random_vpc_ep_id,
    random_launch_template_id,
    random_nat_gateway_id,
    random_transit_gateway_id,
    random_key_pair,
    random_private_ip,
    random_public_ip,
    random_reservation_id,
    random_route_table_id,
    generate_route_id,
    random_managed_prefix_list_id,
    create_dns_entries,
    split_route_id,
    random_security_group_id,
    random_security_group_rule_id,
    random_snapshot_id,
    random_spot_fleet_request_id,
    random_spot_request_id,
    random_subnet_id,
    random_subnet_association_id,
    random_flow_log_id,
    random_volume_id,
    random_vpc_id,
    random_vpc_cidr_association_id,
    random_vpc_peering_connection_id,
    random_iam_instance_profile_association_id,
    random_carrier_gateway_id,
    generic_filter,
    is_valid_resource_id,
    get_prefix,
    simple_aws_filter_to_re,
    is_valid_cidr,
    is_valid_ipv6_cidr,
    filter_internet_gateways,
    filter_reservations,
    filter_iam_instance_profile_associations,
    filter_iam_instance_profiles,
    random_network_acl_id,
    random_network_acl_subnet_association_id,
    random_vpn_gateway_id,
    random_vpn_connection_id,
    random_customer_gateway_id,
    random_subnet_ipv6_cidr_block_association_id,
    is_tag_filter,
    tag_filter_matches,
    rsa_public_key_parse,
    rsa_public_key_fingerprint,
    describe_tag_filter,
)

INSTANCE_TYPES = load_resource(__name__, "resources/instance_types.json")

root = pathlib.Path(__file__).parent
offerings_path = "resources/instance_type_offerings"
INSTANCE_TYPE_OFFERINGS = {}
for location_type in listdir(root / offerings_path):
    INSTANCE_TYPE_OFFERINGS[location_type] = {}
    for _region in listdir(root / offerings_path / location_type):
        full_path = offerings_path + "/" + location_type + "/" + _region
        res = load_resource(__name__, full_path)
        for instance in res:
            instance["LocationType"] = location_type
        INSTANCE_TYPE_OFFERINGS[location_type][_region.replace(".json", "")] = res

if "MOTO_AMIS_PATH" in environ:
    with open(environ.get("MOTO_AMIS_PATH"), "r", encoding="utf-8") as f:
        AMIS = json.load(f)
else:
    AMIS = load_resource(__name__, "resources/amis.json")

OWNER_ID = ACCOUNT_ID
MAX_NUMBER_OF_ENDPOINT_SERVICES_RESULTS = 1000
DEFAULT_VPC_ENDPOINT_SERVICES = []


def utc_date_and_time():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")


def validate_resource_ids(resource_ids):
    if not resource_ids:
        raise MissingParameterError(parameter="resourceIdSet")
    for resource_id in resource_ids:
        if not is_valid_resource_id(resource_id):
            raise InvalidID(resource_id=resource_id)
    return True


class InstanceState(object):
    def __init__(self, name="pending", code=0):
        self.name = name
        self.code = code


class StateReason(object):
    def __init__(self, message="", code=""):
        self.message = message
        self.code = code


class TaggedEC2Resource(BaseModel):
    def get_tags(self, *args, **kwargs):
        tags = []
        if self.id:
            tags = self.ec2_backend.describe_tags(filters={"resource-id": [self.id]})
        return tags

    def add_tag(self, key, value):
        self.ec2_backend.create_tags([self.id], {key: value})

    def add_tags(self, tag_map):
        for key, value in tag_map.items():
            self.ec2_backend.create_tags([self.id], {key: value})

    def get_filter_value(self, filter_name, method_name=None):
        tags = self.get_tags()

        if filter_name.startswith("tag:"):
            tagname = filter_name.replace("tag:", "", 1)
            for tag in tags:
                if tag["key"] == tagname:
                    return tag["value"]

            return None
        elif filter_name == "tag-key":
            return [tag["key"] for tag in tags]
        elif filter_name == "tag-value":
            return [tag["value"] for tag in tags]

        value = getattr(self, filter_name.lower().replace("-", "_"), None)
        if value is not None:
            return value

        raise FilterNotImplementedError(filter_name, method_name)


class NetworkInterface(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        subnet,
        private_ip_address,
        private_ip_addresses=None,
        device_index=0,
        public_ip_auto_assign=False,
        group_ids=None,
        description=None,
        tags=None,
        **kwargs,
    ):
        self.ec2_backend = ec2_backend
        self.id = random_eni_id()
        self.device_index = device_index
        if isinstance(private_ip_address, list) and private_ip_address:
            private_ip_address = private_ip_address[0]
        self.private_ip_address = private_ip_address or None
        self.private_ip_addresses = private_ip_addresses or []
        self.ipv6_addresses = kwargs.get("ipv6_addresses") or []

        self.subnet = subnet
        if isinstance(subnet, str):
            self.subnet = self.ec2_backend.get_subnet(subnet)
        self.instance = None
        self.attachment_id = None
        self.description = description
        self.source_dest_check = True

        self.public_ip = None
        self.public_ip_auto_assign = public_ip_auto_assign
        self.start()
        self.add_tags(tags or {})
        self.status = "available"
        self.attachments = []
        self.mac_address = random_mac_address()
        self.interface_type = "interface"
        # Local set to the ENI. When attached to an instance, @property group_set
        #   returns groups for both self and the attached instance.
        self._group_set = []

        if self.subnet.ipv6_cidr_block_associations:
            association = list(self.subnet.ipv6_cidr_block_associations.values())[0]
            subnet_ipv6_cidr_block = association.get("ipv6CidrBlock")
            if kwargs.get("ipv6_address_count"):
                while len(self.ipv6_addresses) < kwargs.get("ipv6_address_count"):
                    ip = random_private_ip(subnet_ipv6_cidr_block, ipv6=True)
                    if ip not in self.ipv6_addresses:
                        self.ipv6_addresses.append(ip)

        if self.private_ip_addresses:
            primary_selected = True if private_ip_address else False
            for item in self.private_ip_addresses.copy():
                if isinstance(item, str):
                    self.private_ip_addresses.remove(item)
                    self.private_ip_addresses.append(
                        {
                            "Primary": True if not primary_selected else False,
                            "PrivateIpAddress": item,
                        }
                    )
                    primary_selected = True

        if not self.private_ip_address:
            if self.private_ip_addresses:
                for ip in self.private_ip_addresses:
                    if isinstance(ip, dict) and ip.get("Primary"):
                        self.private_ip_address = ip.get("PrivateIpAddress")
                        break
            if not self.private_ip_addresses:
                self.private_ip_address = random_private_ip(self.subnet.cidr_block)

        if not self.private_ip_addresses:
            self.private_ip_addresses.append(
                {"Primary": True, "PrivateIpAddress": self.private_ip_address}
            )

        secondary_ips = kwargs.get("secondary_ips_count", None)
        if secondary_ips:
            ips = [
                random_private_ip(self.subnet.cidr_block)
                for index in range(0, int(secondary_ips))
            ]
            if ips:
                self.private_ip_addresses.extend(
                    [{"Primary": False, "PrivateIpAddress": ip} for ip in ips]
                )

        if self.subnet:
            vpc = self.ec2_backend.get_vpc(self.subnet.vpc_id)
            if vpc and vpc.enable_dns_hostnames:
                self.private_dns_name = generate_dns_from_ip(self.private_ip_address)
                for address in self.private_ip_addresses:
                    if address.get("Primary", None):
                        address["PrivateDnsName"] = self.private_dns_name

        group = None
        if group_ids:
            for group_id in group_ids:
                group = self.ec2_backend.get_security_group_from_id(group_id)
                if not group:
                    # Create with specific group ID.
                    group = SecurityGroup(
                        self.ec2_backend,
                        group_id,
                        group_id,
                        group_id,
                        vpc_id=subnet.vpc_id,
                    )
                    self.ec2_backend.groups[subnet.vpc_id][group_id] = group
                if group:
                    self._group_set.append(group)
        if not group_ids:
            group = self.ec2_backend.get_default_security_group(vpc.id)
            if group:
                self._group_set.append(group)

    @property
    def owner_id(self):
        return ACCOUNT_ID

    @property
    def association(self):
        association = {}
        if self.public_ip:
            eips = self.ec2_backend.address_by_ip(
                [self.public_ip], fail_if_not_found=False
            )
            eip = eips[0] if len(eips) > 0 else None
            if eip:
                association["allocationId"] = eip.allocation_id or None
                association["associationId"] = eip.association_id or None
        return association

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-networkinterface.html
        return "AWS::EC2::NetworkInterface"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        security_group_ids = properties.get("SecurityGroups", [])

        ec2_backend = ec2_backends[region_name]
        subnet_id = properties.get("SubnetId")
        if subnet_id:
            subnet = ec2_backend.get_subnet(subnet_id)
        else:
            subnet = None

        private_ip_address = properties.get("PrivateIpAddress", None)
        description = properties.get("Description", None)

        network_interface = ec2_backend.create_network_interface(
            subnet,
            private_ip_address,
            group_ids=security_group_ids,
            description=description,
        )
        return network_interface

    def stop(self):
        if self.public_ip_auto_assign:
            self.public_ip = None

    def start(self):
        self.check_auto_public_ip()

    def check_auto_public_ip(self):
        if (
            self.public_ip_auto_assign
            and str(self.public_ip_auto_assign).lower() == "true"
        ):
            self.public_ip = random_public_ip()

    @property
    def group_set(self):
        if self.instance and self.instance.security_groups:
            return set(self._group_set) | set(self.instance.security_groups)
        else:
            return self._group_set

    @classmethod
    def has_cfn_attr(cls, attribute):
        return attribute in ["PrimaryPrivateIpAddress", "SecondaryPrivateIpAddresses"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "PrimaryPrivateIpAddress":
            return self.private_ip_address
        elif attribute_name == "SecondaryPrivateIpAddresses":
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "SecondaryPrivateIpAddresses" ]"'
            )
        raise UnformattedGetAttTemplateException()

    @property
    def physical_resource_id(self):
        return self.id

    def get_filter_value(self, filter_name):
        if filter_name == "network-interface-id":
            return self.id
        elif filter_name in ("addresses.private-ip-address", "private-ip-address"):
            return self.private_ip_address
        elif filter_name == "subnet-id":
            return self.subnet.id
        elif filter_name == "vpc-id":
            return self.subnet.vpc_id
        elif filter_name == "group-id":
            return [group.id for group in self._group_set]
        elif filter_name == "availability-zone":
            return self.subnet.availability_zone
        elif filter_name == "description":
            return self.description
        elif filter_name == "attachment.instance-id":
            return self.instance.id if self.instance else None
        else:
            return super().get_filter_value(filter_name, "DescribeNetworkInterfaces")


class NetworkInterfaceBackend(object):
    def __init__(self):
        self.enis = {}
        super().__init__()

    def create_network_interface(
        self,
        subnet,
        private_ip_address,
        private_ip_addresses=None,
        group_ids=None,
        description=None,
        tags=None,
        **kwargs,
    ):
        eni = NetworkInterface(
            self,
            subnet,
            private_ip_address,
            private_ip_addresses,
            group_ids=group_ids,
            description=description,
            tags=tags,
            **kwargs,
        )
        self.enis[eni.id] = eni
        return eni

    def get_network_interface(self, eni_id):
        for eni in self.enis.values():
            if eni_id == eni.id:
                return eni
        raise InvalidNetworkInterfaceIdError(eni_id)

    def delete_network_interface(self, eni_id):
        deleted = self.enis.pop(eni_id, None)
        if not deleted:
            raise InvalidNetworkInterfaceIdError(eni_id)
        return deleted

    def describe_network_interfaces(self, filters=None):
        # Note: This is only used in EC2Backend#do_resources_exist
        # Client-calls use #get_all_network_interfaces()
        # We should probably merge these at some point..
        enis = self.enis.values()

        if filters:
            for (_filter, _filter_value) in filters.items():
                if _filter == "network-interface-id":
                    _filter = "id"
                    enis = [
                        eni for eni in enis if getattr(eni, _filter) in _filter_value
                    ]
                else:
                    self.raise_not_implemented_error(
                        "The filter '{0}' for DescribeNetworkInterfaces".format(_filter)
                    )
        return enis

    def attach_network_interface(self, eni_id, instance_id, device_index):
        eni = self.get_network_interface(eni_id)
        instance = self.get_instance(instance_id)
        return instance.attach_eni(eni, device_index)

    def detach_network_interface(self, attachment_id):
        found_eni = None

        for eni in self.enis.values():
            if eni.attachment_id == attachment_id:
                found_eni = eni
                break
        else:
            raise InvalidNetworkAttachmentIdError(attachment_id)

        found_eni.instance.detach_eni(found_eni)

    def modify_network_interface_attribute(
        self, eni_id, group_ids, source_dest_check=None, description=None
    ):
        eni = self.get_network_interface(eni_id)
        groups = [self.get_security_group_from_id(group_id) for group_id in group_ids]
        if groups:
            eni._group_set = groups
        if source_dest_check in [True, False]:
            eni.source_dest_check = source_dest_check

        if description:
            eni.description = description

    def get_all_network_interfaces(self, eni_ids=None, filters=None):
        enis = self.enis.copy().values()

        if eni_ids:
            enis = [eni for eni in enis if eni.id in eni_ids]
            if len(enis) != len(eni_ids):
                invalid_id = list(
                    set(eni_ids).difference(set([eni.id for eni in enis]))
                )[0]
                raise InvalidNetworkInterfaceIdError(invalid_id)

        return generic_filter(filters, enis)

    def unassign_private_ip_addresses(self, eni_id=None, private_ip_address=None):
        eni = self.get_network_interface(eni_id)
        if private_ip_address:
            for item in eni.private_ip_addresses.copy():
                if item.get("PrivateIpAddress") in private_ip_address:
                    eni.private_ip_addresses.remove(item)
        return eni

    def assign_private_ip_addresses(self, eni_id=None, secondary_ips_count=None):
        eni = self.get_network_interface(eni_id)
        eni_assigned_ips = [
            item.get("PrivateIpAddress") for item in eni.private_ip_addresses
        ]
        while secondary_ips_count:
            ip = random_private_ip(eni.subnet.cidr_block)
            if ip not in eni_assigned_ips:
                eni.private_ip_addresses.append(
                    {"Primary": False, "PrivateIpAddress": ip}
                )
                secondary_ips_count -= 1
        return eni

    def assign_ipv6_addresses(self, eni_id=None, ipv6_addresses=None, ipv6_count=None):
        eni = self.get_network_interface(eni_id)
        if ipv6_addresses:
            eni.ipv6_addresses.extend(ipv6_addresses)

        while ipv6_count:
            association = list(eni.subnet.ipv6_cidr_block_associations.values())[0]
            subnet_ipv6_cidr_block = association.get("ipv6CidrBlock")
            ip = random_private_ip(subnet_ipv6_cidr_block, ipv6=True)
            if ip not in eni.ipv6_addresses:
                eni.ipv6_addresses.append(ip)
                ipv6_count -= 1
        return eni

    def unassign_ipv6_addresses(self, eni_id=None, ips=None):
        eni = self.get_network_interface(eni_id)
        if ips:
            for ip in eni.ipv6_addresses.copy():
                if ip in ips:
                    eni.ipv6_addresses.remove(ip)
        return eni, ips


class Instance(TaggedEC2Resource, BotoInstance, CloudFormationModel):
    VALID_ATTRIBUTES = {
        "instanceType",
        "kernel",
        "ramdisk",
        "userData",
        "disableApiTermination",
        "instanceInitiatedShutdownBehavior",
        "rootDeviceName",
        "blockDeviceMapping",
        "productCodes",
        "sourceDestCheck",
        "groupSet",
        "ebsOptimized",
        "sriovNetSupport",
    }

    def __init__(self, ec2_backend, image_id, user_data, security_groups, **kwargs):
        super().__init__()
        self.ec2_backend = ec2_backend
        self.id = random_instance_id()
        self.lifecycle = kwargs.get("lifecycle")

        nics = kwargs.get("nics", {})

        launch_template_arg = kwargs.get("launch_template", {})
        if launch_template_arg and not image_id:
            # the image id from the template should be used
            template = (
                ec2_backend.describe_launch_templates(
                    template_ids=[launch_template_arg["LaunchTemplateId"]]
                )[0]
                if "LaunchTemplateId" in launch_template_arg
                else ec2_backend.describe_launch_templates(
                    template_names=[launch_template_arg["LaunchTemplateName"]]
                )[0]
            )
            version = launch_template_arg.get("Version", template.latest_version_number)
            self.image_id = template.get_version(int(version)).image_id
        else:
            self.image_id = image_id

        self._state = InstanceState("running", 16)
        self._reason = ""
        self._state_reason = StateReason()
        self.user_data = user_data
        self.security_groups = security_groups
        self.instance_type = kwargs.get("instance_type", "m1.small")
        self.region_name = kwargs.get("region_name", "us-east-1")
        placement = kwargs.get("placement", None)
        self.subnet_id = kwargs.get("subnet_id")
        if not self.subnet_id:
            self.subnet_id = next(
                (n["SubnetId"] for n in nics.values() if "SubnetId" in n), None
            )
        in_ec2_classic = not bool(self.subnet_id)
        self.key_name = kwargs.get("key_name")
        self.ebs_optimized = kwargs.get("ebs_optimized", False)
        self.source_dest_check = "true"
        self.launch_time = utc_date_and_time()
        self.ami_launch_index = kwargs.get("ami_launch_index", 0)
        self.disable_api_termination = kwargs.get("disable_api_termination", False)
        self.instance_initiated_shutdown_behavior = kwargs.get(
            "instance_initiated_shutdown_behavior", "stop"
        )
        self.sriov_net_support = "simple"
        self._spot_fleet_id = kwargs.get("spot_fleet_id", None)
        self.associate_public_ip = kwargs.get("associate_public_ip", False)
        if in_ec2_classic:
            # If we are in EC2-Classic, autoassign a public IP
            self.associate_public_ip = True

        amis = self.ec2_backend.describe_images(filters={"image-id": self.image_id})
        ami = amis[0] if amis else None
        if ami is None:
            warnings.warn(
                "Could not find AMI with image-id:{0}, "
                "in the near future this will "
                "cause an error.\n"
                "Use ec2_backend.describe_images() to "
                "find suitable image for your test".format(self.image_id),
                PendingDeprecationWarning,
            )

        self.platform = ami.platform if ami else None
        self.virtualization_type = ami.virtualization_type if ami else "paravirtual"
        self.architecture = ami.architecture if ami else "x86_64"

        # handle weird bug around user_data -- something grabs the repr(), so
        # it must be clean
        if isinstance(self.user_data, list) and len(self.user_data) > 0:
            if isinstance(self.user_data[0], bytes):
                # string will have a "b" prefix -- need to get rid of it
                self.user_data[0] = self.user_data[0].decode("utf-8")

        if self.subnet_id:
            subnet = ec2_backend.get_subnet(self.subnet_id)
            self._placement.zone = subnet.availability_zone

            if self.associate_public_ip is None:
                # Mapping public ip hasnt been explicitly enabled or disabled
                self.associate_public_ip = subnet.map_public_ip_on_launch == "true"
        elif placement:
            self._placement.zone = placement
        else:
            self._placement.zone = ec2_backend.region_name + "a"

        self.block_device_mapping = BlockDeviceMapping()

        self._private_ips = set()
        self.prep_nics(
            nics,
            private_ip=kwargs.get("private_ip"),
            associate_public_ip=self.associate_public_ip,
            security_groups=self.security_groups,
        )

    @property
    def vpc_id(self):
        if self.subnet_id:
            subnet = self.ec2_backend.get_subnet(self.subnet_id)
            return subnet.vpc_id
        if self.nics and 0 in self.nics:
            return self.nics[0].subnet.vpc_id
        return None

    def __del__(self):
        try:
            subnet = self.ec2_backend.get_subnet(self.subnet_id)
            for ip in self._private_ips:
                subnet.del_subnet_ip(ip)
        except Exception:
            # Its not "super" critical we clean this up, as reset will do this
            # worst case we'll get IP address exaustion... rarely
            pass

    def add_block_device(
        self,
        size,
        device_path,
        snapshot_id=None,
        encrypted=False,
        delete_on_termination=False,
        kms_key_id=None,
    ):
        volume = self.ec2_backend.create_volume(
            size=size,
            zone_name=self._placement.zone,
            snapshot_id=snapshot_id,
            encrypted=encrypted,
            kms_key_id=kms_key_id,
        )
        self.ec2_backend.attach_volume(
            volume.id, self.id, device_path, delete_on_termination
        )

    def setup_defaults(self):
        # Default have an instance with root volume should you not wish to
        # override with attach volume cmd.
        volume = self.ec2_backend.create_volume(size=8, zone_name=self._placement.zone)
        self.ec2_backend.attach_volume(volume.id, self.id, "/dev/sda1", True)

    def teardown_defaults(self):
        for device_path in list(self.block_device_mapping.keys()):
            volume = self.block_device_mapping[device_path]
            volume_id = volume.volume_id
            self.ec2_backend.detach_volume(volume_id, self.id, device_path)
            if volume.delete_on_termination:
                self.ec2_backend.delete_volume(volume_id)

    @property
    def get_block_device_mapping(self):
        return self.block_device_mapping.items()

    @property
    def private_ip(self):
        return self.nics[0].private_ip_address

    @property
    def private_dns(self):
        formatted_ip = self.private_ip.replace(".", "-")
        if self.region_name == "us-east-1":
            return "ip-{0}.ec2.internal".format(formatted_ip)
        else:
            return "ip-{0}.{1}.compute.internal".format(formatted_ip, self.region_name)

    @property
    def public_ip(self):
        return self.nics[0].public_ip

    @property
    def public_dns(self):
        if self.public_ip:
            formatted_ip = self.public_ip.replace(".", "-")
            if self.region_name == "us-east-1":
                return "ec2-{0}.compute-1.amazonaws.com".format(formatted_ip)
            else:
                return "ec2-{0}.{1}.compute.amazonaws.com".format(
                    formatted_ip, self.region_name
                )

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-instance.html
        return "AWS::EC2::Instance"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[region_name]
        security_group_ids = properties.get("SecurityGroups", [])
        group_names = [
            ec2_backend.get_security_group_from_id(group_id).name
            for group_id in security_group_ids
        ]

        reservation = ec2_backend.add_instances(
            image_id=properties["ImageId"],
            user_data=properties.get("UserData"),
            count=1,
            security_group_names=group_names,
            instance_type=properties.get("InstanceType", "m1.small"),
            subnet_id=properties.get("SubnetId"),
            key_name=properties.get("KeyName"),
            private_ip=properties.get("PrivateIpAddress"),
            block_device_mappings=properties.get("BlockDeviceMappings", {}),
        )
        instance = reservation.instances[0]
        for tag in properties.get("Tags", []):
            instance.add_tag(tag["Key"], tag["Value"])

        # Associating iam instance profile.
        # TODO: Don't forget to implement replace_iam_instance_profile_association once update_from_cloudformation_json
        #  for ec2 instance will be implemented.
        if properties.get("IamInstanceProfile"):
            ec2_backend.associate_iam_instance_profile(
                instance_id=instance.id,
                iam_instance_profile_name=properties.get("IamInstanceProfile"),
            )

        return instance

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        ec2_backend = ec2_backends[region_name]
        all_instances = ec2_backend.all_instances()

        # the resource_name for instances is the stack name, logical id, and random suffix separated
        # by hyphens.  So to lookup the instances using the 'aws:cloudformation:logical-id' tag, we need to
        # extract the logical-id from the resource_name
        logical_id = resource_name.split("-")[1]

        for instance in all_instances:
            instance_tags = instance.get_tags()
            for tag in instance_tags:
                if (
                    tag["key"] == "aws:cloudformation:logical-id"
                    and tag["value"] == logical_id
                ):
                    instance.delete(region_name)

    @property
    def physical_resource_id(self):
        return self.id

    def start(self, *args, **kwargs):
        for nic in self.nics.values():
            nic.start()

        self._state.name = "running"
        self._state.code = 16

        self._reason = ""
        self._state_reason = StateReason()

    def stop(self, *args, **kwargs):
        for nic in self.nics.values():
            nic.stop()

        self._state.name = "stopped"
        self._state.code = 80

        self._reason = "User initiated ({0})".format(
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        self._state_reason = StateReason(
            "Client.UserInitiatedShutdown: User initiated shutdown",
            "Client.UserInitiatedShutdown",
        )

    def delete(self, region):
        self.terminate()

    def terminate(self, *args, **kwargs):
        for nic in self.nics.values():
            nic.stop()

        self.teardown_defaults()

        if self._spot_fleet_id:
            spot_fleet = self.ec2_backend.get_spot_fleet_request(self._spot_fleet_id)
            for spec in spot_fleet.launch_specs:
                if (
                    spec.instance_type == self.instance_type
                    and spec.subnet_id == self.subnet_id
                ):
                    break
            spot_fleet.fulfilled_capacity -= spec.weighted_capacity
            spot_fleet.spot_requests = [
                req for req in spot_fleet.spot_requests if req.instance != self
            ]

        self._state.name = "terminated"
        self._state.code = 48

        self._reason = "User initiated ({0})".format(
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        self._state_reason = StateReason(
            "Client.UserInitiatedShutdown: User initiated shutdown",
            "Client.UserInitiatedShutdown",
        )

        # Disassociate iam instance profile if associated, otherwise iam_instance_profile_associations will
        # be pointing to None.
        if self.ec2_backend.iam_instance_profile_associations.get(self.id):
            self.ec2_backend.disassociate_iam_instance_profile(
                association_id=self.ec2_backend.iam_instance_profile_associations[
                    self.id
                ].id
            )

    def reboot(self, *args, **kwargs):
        self._state.name = "running"
        self._state.code = 16

        self._reason = ""
        self._state_reason = StateReason()

    @property
    def dynamic_group_list(self):
        return self.security_groups

    def prep_nics(
        self, nic_spec, private_ip=None, associate_public_ip=None, security_groups=None
    ):
        self.nics = {}

        if self.subnet_id:
            subnet = self.ec2_backend.get_subnet(self.subnet_id)
            if not private_ip:
                private_ip = subnet.get_available_subnet_ip(instance=self)
            else:
                subnet.request_ip(private_ip, instance=self)

            self._private_ips.add(private_ip)
        elif private_ip is None:
            # Preserve old behaviour if in EC2-Classic mode
            private_ip = random_private_ip()

        # Primary NIC defaults
        primary_nic = {
            "SubnetId": self.subnet_id,
            "PrivateIpAddress": private_ip,
            "AssociatePublicIpAddress": associate_public_ip,
        }
        primary_nic = dict((k, v) for k, v in primary_nic.items() if v)

        # If empty NIC spec but primary NIC values provided, create NIC from
        # them.
        if primary_nic and not nic_spec:
            nic_spec[0] = primary_nic
            nic_spec[0]["DeviceIndex"] = 0

        # Flesh out data structures and associations
        for nic in nic_spec.values():
            device_index = int(nic.get("DeviceIndex"))

            nic_id = nic.get("NetworkInterfaceId")
            if nic_id:
                # If existing NIC found, use it.
                use_nic = self.ec2_backend.get_network_interface(nic_id)
                use_nic.device_index = device_index
                use_nic.public_ip_auto_assign = False

            else:
                # If primary NIC values provided, use them for the primary NIC.
                if device_index == 0 and primary_nic:
                    nic.update(primary_nic)

                if "SubnetId" in nic:
                    subnet = self.ec2_backend.get_subnet(nic["SubnetId"])
                else:
                    # Get default Subnet
                    subnet = [
                        subnet
                        for subnet in self.ec2_backend.get_all_subnets(
                            filters={"availabilityZone": self._placement.zone}
                        )
                        if subnet.default_for_az
                    ][0]

                group_id = nic.get("SecurityGroupId")
                group_ids = [group_id] if group_id else []
                if security_groups:
                    group_ids.extend([group.id for group in security_groups])

                use_nic = self.ec2_backend.create_network_interface(
                    subnet,
                    nic.get("PrivateIpAddress"),
                    device_index=device_index,
                    public_ip_auto_assign=nic.get("AssociatePublicIpAddress", False),
                    group_ids=group_ids,
                )

            self.attach_eni(use_nic, device_index)

    def attach_eni(self, eni, device_index):
        device_index = int(device_index)
        self.nics[device_index] = eni

        # This is used upon associate/disassociate public IP.
        eni.instance = self
        eni.attachment_id = random_eni_attach_id()
        eni.device_index = device_index

        return eni.attachment_id

    def detach_eni(self, eni):
        self.nics.pop(eni.device_index, None)
        eni.instance = None
        eni.attachment_id = None
        eni.device_index = None

    @classmethod
    def has_cfn_attr(cls, attribute):
        return attribute in [
            "AvailabilityZone",
            "PrivateDnsName",
            "PublicDnsName",
            "PrivateIp",
            "PublicIp",
        ]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "AvailabilityZone":
            return self.placement
        elif attribute_name == "PrivateDnsName":
            return self.private_dns
        elif attribute_name == "PublicDnsName":
            return self.public_dns
        elif attribute_name == "PrivateIp":
            return self.private_ip
        elif attribute_name == "PublicIp":
            return self.public_ip
        raise UnformattedGetAttTemplateException()

    def applies(self, filters):
        if filters:
            applicable = False
            for f in filters:
                acceptable_values = f["values"]
                if f["name"] == "instance-state-name":
                    if self._state.name in acceptable_values:
                        applicable = True
                if f["name"] == "instance-state-code":
                    if str(self._state.code) in acceptable_values:
                        applicable = True
            return applicable
        # If there are no filters, all instances are valid
        return True


class InstanceBackend(object):
    def __init__(self):
        self.reservations = OrderedDict()
        super().__init__()

    def get_instance(self, instance_id):
        for instance in self.all_instances():
            if instance.id == instance_id:
                return instance
        raise InvalidInstanceIdError(instance_id)

    def add_instances(self, image_id, count, user_data, security_group_names, **kwargs):
        new_reservation = Reservation()
        new_reservation.id = random_reservation_id()

        security_groups = [
            self.get_security_group_by_name_or_id(name) for name in security_group_names
        ]

        for sg_id in kwargs.pop("security_group_ids", []):
            if isinstance(sg_id, str):
                security_groups.append(self.get_security_group_from_id(sg_id))
            else:
                security_groups.append(sg_id)

        self.reservations[new_reservation.id] = new_reservation

        tags = kwargs.pop("tags", {})
        instance_tags = tags.get("instance", {})
        volume_tags = tags.get("volume", {})

        for index in range(count):
            kwargs["ami_launch_index"] = index
            new_instance = Instance(
                self, image_id, user_data, security_groups, **kwargs
            )
            new_reservation.instances.append(new_instance)
            new_instance.add_tags(instance_tags)
            if "block_device_mappings" in kwargs:
                for block_device in kwargs["block_device_mappings"]:
                    device_name = block_device["DeviceName"]
                    volume_size = block_device["Ebs"].get("VolumeSize")
                    snapshot_id = block_device["Ebs"].get("SnapshotId")
                    encrypted = block_device["Ebs"].get("Encrypted", False)
                    delete_on_termination = block_device["Ebs"].get(
                        "DeleteOnTermination", False
                    )
                    kms_key_id = block_device["Ebs"].get("KmsKeyId")
                    new_instance.add_block_device(
                        volume_size,
                        device_name,
                        snapshot_id,
                        encrypted,
                        delete_on_termination,
                        kms_key_id,
                    )
            else:
                new_instance.setup_defaults()
            if kwargs.get("instance_market_options"):
                new_instance.lifecycle = "spot"
            # Tag all created volumes.
            for _, device in new_instance.get_block_device_mapping:
                volumes = self.describe_volumes(volume_ids=[device.volume_id])
                for volume in volumes:
                    volume.add_tags(volume_tags)

        return new_reservation

    def run_instances(self):
        # Logic resides in add_instances
        # Fake method here to make implementation coverage script aware that this method is implemented
        pass

    def start_instances(self, instance_ids):
        started_instances = []
        for instance in self.get_multi_instances_by_id(instance_ids):
            instance.start()
            started_instances.append(instance)

        return started_instances

    def stop_instances(self, instance_ids):
        stopped_instances = []
        for instance in self.get_multi_instances_by_id(instance_ids):
            instance.stop()
            stopped_instances.append(instance)

        return stopped_instances

    def terminate_instances(self, instance_ids):
        terminated_instances = []
        if not instance_ids:
            raise EC2ClientError(
                "InvalidParameterCombination", "No instances specified"
            )
        for instance in self.get_multi_instances_by_id(instance_ids):
            if instance.disable_api_termination == "true":
                raise OperationNotPermitted4(instance.id)
            instance.terminate()
            terminated_instances.append(instance)

        return terminated_instances

    def reboot_instances(self, instance_ids):
        rebooted_instances = []
        for instance in self.get_multi_instances_by_id(instance_ids):
            instance.reboot()
            rebooted_instances.append(instance)

        return rebooted_instances

    def modify_instance_attribute(self, instance_id, key, value):
        instance = self.get_instance(instance_id)
        setattr(instance, key, value)
        return instance

    def modify_instance_security_groups(self, instance_id, new_group_id_list):
        instance = self.get_instance(instance_id)
        new_group_list = []
        for new_group_id in new_group_id_list:
            new_group_list.append(self.get_security_group_from_id(new_group_id))
        setattr(instance, "security_groups", new_group_list)
        return instance

    def describe_instance_attribute(self, instance_id, attribute):
        if attribute not in Instance.VALID_ATTRIBUTES:
            raise InvalidParameterValueErrorUnknownAttribute(attribute)

        if attribute == "groupSet":
            key = "security_groups"
        else:
            key = camelcase_to_underscores(attribute)
        instance = self.get_instance(instance_id)
        value = getattr(instance, key)
        return instance, value

    def describe_instance_credit_specifications(self, instance_ids):
        queried_instances = []
        for instance in self.get_multi_instances_by_id(instance_ids):
            queried_instances.append(instance)
        return queried_instances

    def all_instances(self, filters=None):
        instances = []
        for reservation in self.all_reservations():
            for instance in reservation.instances:
                if instance.applies(filters):
                    instances.append(instance)
        return instances

    def all_running_instances(self, filters=None):
        instances = []
        for reservation in self.all_reservations():
            for instance in reservation.instances:
                if instance.state_code == 16 and instance.applies(filters):
                    instances.append(instance)
        return instances

    def get_multi_instances_by_id(self, instance_ids, filters=None):
        """
        :param instance_ids: A string list with instance ids
        :return: A list with instance objects
        """
        result = []

        for reservation in self.all_reservations():
            for instance in reservation.instances:
                if instance.id in instance_ids:
                    if instance.applies(filters):
                        result.append(instance)

        # TODO: Trim error message down to specific invalid id.
        if instance_ids and len(instance_ids) > len(result):
            raise InvalidInstanceIdError(instance_ids)

        return result

    def get_instance_by_id(self, instance_id):
        for reservation in self.all_reservations():
            for instance in reservation.instances:
                if instance.id == instance_id:
                    return instance

    def get_reservations_by_instance_ids(self, instance_ids, filters=None):
        """Go through all of the reservations and filter to only return those
        associated with the given instance_ids.
        """
        reservations = []
        for reservation in self.all_reservations():
            reservation_instance_ids = [
                instance.id for instance in reservation.instances
            ]
            matching_reservation = any(
                instance_id in reservation_instance_ids for instance_id in instance_ids
            )
            if matching_reservation:
                reservation.instances = [
                    instance
                    for instance in reservation.instances
                    if instance.id in instance_ids
                ]
                reservations.append(reservation)
        found_instance_ids = [
            instance.id
            for reservation in reservations
            for instance in reservation.instances
        ]
        if len(found_instance_ids) != len(instance_ids):
            invalid_id = list(set(instance_ids).difference(set(found_instance_ids)))[0]
            raise InvalidInstanceIdError(invalid_id)
        if filters is not None:
            reservations = filter_reservations(reservations, filters)
        return reservations

    def describe_instances(self, filters=None):
        return self.all_reservations(filters)

    def describe_instance_status(self, instance_ids, include_all_instances, filters):
        if instance_ids:
            return self.get_multi_instances_by_id(instance_ids, filters)
        elif include_all_instances:
            return self.all_instances(filters)
        else:
            return self.all_running_instances(filters)

    def all_reservations(self, filters=None):
        reservations = [
            copy.copy(reservation) for reservation in self.reservations.copy().values()
        ]
        if filters is not None:
            reservations = filter_reservations(reservations, filters)
        return reservations


class InstanceTypeBackend(object):
    def __init__(self):
        super().__init__()

    def describe_instance_types(self, instance_types=None):
        matches = INSTANCE_TYPES.values()
        if instance_types:
            matches = [t for t in matches if t.get("InstanceType") in instance_types]
            if len(instance_types) > len(matches):
                unknown_ids = set(instance_types) - set(
                    t.get("InstanceType") for t in matches
                )
                raise InvalidInstanceTypeError(unknown_ids)
        return matches


class InstanceTypeOfferingBackend(object):
    def __init__(self):
        super().__init__()

    def describe_instance_type_offerings(self, location_type=None, filters=None):
        location_type = location_type or "region"
        matches = INSTANCE_TYPE_OFFERINGS[location_type]
        matches = matches.get(self.region_name, [])

        def matches_filters(offering, filters):
            def matches_filter(key, values):
                if key == "location":
                    if location_type in ("availability-zone", "availability-zone-id"):
                        return offering.get("Location") in values
                    elif location_type == "region":
                        return any(
                            v for v in values if offering.get("Location").startswith(v)
                        )
                    else:
                        return False
                elif key == "instance-type":
                    return offering.get("InstanceType") in values
                else:
                    return False

            return all([matches_filter(key, values) for key, values in filters.items()])

        matches = [o for o in matches if matches_filters(o, filters or {})]
        return matches


class KeyPair(object):
    def __init__(self, name, fingerprint, material):
        self.name = name
        self.fingerprint = fingerprint
        self.material = material

    def get_filter_value(self, filter_name):
        if filter_name == "key-name":
            return self.name
        elif filter_name == "fingerprint":
            return self.fingerprint
        else:
            raise FilterNotImplementedError(filter_name, "DescribeKeyPairs")


class KeyPairBackend(object):
    def __init__(self):
        self.keypairs = {}
        super().__init__()

    def create_key_pair(self, name):
        if name in self.keypairs:
            raise InvalidKeyPairDuplicateError(name)
        keypair = KeyPair(name, **random_key_pair())
        self.keypairs[name] = keypair
        return keypair

    def delete_key_pair(self, name):
        if name in self.keypairs:
            self.keypairs.pop(name)
        return True

    def describe_key_pairs(self, key_names=None, filters=None):
        results = []
        if key_names:
            results = [
                keypair
                for keypair in self.keypairs.values()
                if keypair.name in key_names
            ]
            if len(key_names) > len(results):
                unknown_keys = set(key_names) - set(results)
                raise InvalidKeyPairNameError(unknown_keys)
        else:
            results = self.keypairs.values()

        if filters:
            return generic_filter(filters, results)
        else:
            return results

    def import_key_pair(self, key_name, public_key_material):
        if key_name in self.keypairs:
            raise InvalidKeyPairDuplicateError(key_name)

        try:
            rsa_public_key = rsa_public_key_parse(public_key_material)
        except ValueError:
            raise InvalidKeyPairFormatError()

        fingerprint = rsa_public_key_fingerprint(rsa_public_key)
        keypair = KeyPair(
            key_name, material=public_key_material, fingerprint=fingerprint
        )
        self.keypairs[key_name] = keypair
        return keypair


class SettingsBackend(object):
    def __init__(self):
        self.ebs_encryption_by_default = False
        super().__init__()

    def disable_ebs_encryption_by_default(self):
        ec2_backend = ec2_backends[self.region_name]
        ec2_backend.ebs_encryption_by_default = False

    def enable_ebs_encryption_by_default(self):
        ec2_backend = ec2_backends[self.region_name]
        ec2_backend.ebs_encryption_by_default = True

    def get_ebs_encryption_by_default(self):
        ec2_backend = ec2_backends[self.region_name]
        return ec2_backend.ebs_encryption_by_default


class TagBackend(object):
    VALID_TAG_FILTERS = ["key", "resource-id", "resource-type", "value"]

    VALID_TAG_RESOURCE_FILTER_TYPES = [
        "customer-gateway",
        "dhcp-options",
        "image",
        "instance",
        "internet-gateway",
        "network-acl",
        "network-interface",
        "reserved-instances",
        "route-table",
        "security-group",
        "snapshot",
        "spot-instances-request",
        "subnet",
        "volume",
        "vpc",
        "vpc-flow-log",
        "vpc-peering-connection" "vpn-connection",
        "vpn-gateway",
    ]

    def __init__(self):
        self.tags = defaultdict(dict)
        super().__init__()

    def create_tags(self, resource_ids, tags):
        if None in set([tags[tag] for tag in tags]):
            raise InvalidParameterValueErrorTagNull()
        for resource_id in resource_ids:
            if resource_id in self.tags:
                if (
                    len(self.tags[resource_id])
                    + len([tag for tag in tags if not tag.startswith("aws:")])
                    > 50
                ):
                    raise TagLimitExceeded()
            elif len([tag for tag in tags if not tag.startswith("aws:")]) > 50:
                raise TagLimitExceeded()
        for resource_id in resource_ids:
            for tag in tags:
                self.tags[resource_id][tag] = tags[tag]
        return True

    def delete_tags(self, resource_ids, tags):
        for resource_id in resource_ids:
            for tag in tags:
                if tag in self.tags[resource_id]:
                    if tags[tag] is None:
                        self.tags[resource_id].pop(tag)
                    elif tags[tag] == self.tags[resource_id][tag]:
                        self.tags[resource_id].pop(tag)
        return True

    def describe_tags(self, filters=None):
        results = []
        key_filters = []
        resource_id_filters = []
        resource_type_filters = []
        value_filters = []
        if filters is not None:
            for tag_filter in filters:
                if tag_filter in self.VALID_TAG_FILTERS:
                    if tag_filter == "key":
                        for value in filters[tag_filter]:
                            key_filters.append(
                                re.compile(simple_aws_filter_to_re(value))
                            )
                    if tag_filter == "resource-id":
                        for value in filters[tag_filter]:
                            resource_id_filters.append(
                                re.compile(simple_aws_filter_to_re(value))
                            )
                    if tag_filter == "resource-type":
                        for value in filters[tag_filter]:
                            resource_type_filters.append(value)
                    if tag_filter == "value":
                        for value in filters[tag_filter]:
                            value_filters.append(
                                re.compile(simple_aws_filter_to_re(value))
                            )
        for resource_id, tags in self.tags.copy().items():
            for key, value in tags.items():
                add_result = False
                if filters is None:
                    add_result = True
                else:
                    key_pass = False
                    id_pass = False
                    type_pass = False
                    value_pass = False
                    if key_filters:
                        for pattern in key_filters:
                            if pattern.match(key) is not None:
                                key_pass = True
                    else:
                        key_pass = True
                    if resource_id_filters:
                        for pattern in resource_id_filters:
                            if pattern.match(resource_id) is not None:
                                id_pass = True
                    else:
                        id_pass = True
                    if resource_type_filters:
                        for resource_type in resource_type_filters:
                            if (
                                EC2_PREFIX_TO_RESOURCE[get_prefix(resource_id)]
                                == resource_type
                            ):
                                type_pass = True
                    else:
                        type_pass = True
                    if value_filters:
                        for pattern in value_filters:
                            if pattern.match(value) is not None:
                                value_pass = True
                    else:
                        value_pass = True
                    if key_pass and id_pass and type_pass and value_pass:
                        add_result = True
                        # If we're not filtering, or we are filtering and this
                if add_result:
                    result = {
                        "resource_id": resource_id,
                        "key": key,
                        "value": value,
                        "resource_type": EC2_PREFIX_TO_RESOURCE.get(
                            get_prefix(resource_id), ""
                        ),
                    }
                    results.append(result)
        return results


class Ami(TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        ami_id,
        instance=None,
        source_ami=None,
        name=None,
        description=None,
        owner_id=OWNER_ID,
        owner_alias=None,
        public=False,
        virtualization_type=None,
        architecture=None,
        state="available",
        creation_date=None,
        platform=None,
        image_type="machine",
        image_location=None,
        hypervisor=None,
        root_device_type="standard",
        root_device_name="/dev/sda1",
        sriov="simple",
        region_name="us-east-1a",
        snapshot_description=None,
    ):
        self.ec2_backend = ec2_backend
        self.id = ami_id
        self.state = state
        self.name = name
        self.image_type = image_type
        self.image_location = image_location
        self.owner_id = owner_id
        self.owner_alias = owner_alias
        self.description = description
        self.virtualization_type = virtualization_type
        self.architecture = architecture
        self.kernel_id = None
        self.platform = platform
        self.hypervisor = hypervisor
        self.root_device_name = root_device_name
        self.root_device_type = root_device_type
        self.sriov = sriov
        self.creation_date = (
            utc_date_and_time() if creation_date is None else creation_date
        )

        if instance:
            self.instance = instance
            self.instance_id = instance.id
            self.virtualization_type = instance.virtualization_type
            self.architecture = instance.architecture
            self.kernel_id = instance.kernel
            self.platform = instance.platform

        elif source_ami:
            """
            http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/CopyingAMIs.html
            "We don't copy launch permissions, user-defined tags, or Amazon S3 bucket permissions from the source AMI to the new AMI."
            ~ 2014.09.29
            """
            self.virtualization_type = source_ami.virtualization_type
            self.architecture = source_ami.architecture
            self.kernel_id = source_ami.kernel_id
            self.platform = source_ami.platform
            if not name:
                self.name = source_ami.name
            if not description:
                self.description = source_ami.description

        self.launch_permission_groups = set()
        self.launch_permission_users = set()

        if public:
            self.launch_permission_groups.add("all")

        # AWS auto-creates these, we should reflect the same.
        volume = self.ec2_backend.create_volume(size=15, zone_name=region_name)
        snapshot_description = (
            snapshot_description or "Auto-created snapshot for AMI %s" % self.id
        )
        self.ebs_snapshot = self.ec2_backend.create_snapshot(
            volume.id, snapshot_description, owner_id, from_ami=ami_id
        )
        self.ec2_backend.delete_volume(volume.id)

    @property
    def is_public(self):
        return "all" in self.launch_permission_groups

    @property
    def is_public_string(self):
        return str(self.is_public).lower()

    def get_filter_value(self, filter_name):
        if filter_name == "virtualization-type":
            return self.virtualization_type
        elif filter_name == "kernel-id":
            return self.kernel_id
        elif filter_name in ["architecture", "platform"]:
            return getattr(self, filter_name)
        elif filter_name == "image-id":
            return self.id
        elif filter_name == "is-public":
            return self.is_public_string
        elif filter_name == "state":
            return self.state
        elif filter_name == "name":
            return self.name
        elif filter_name == "owner-id":
            return self.owner_id
        elif filter_name == "owner-alias":
            return self.owner_alias
        else:
            return super().get_filter_value(filter_name, "DescribeImages")


class AmiBackend(object):
    AMI_REGEX = re.compile("ami-[a-z0-9]+")

    def __init__(self):
        self.amis = {}
        self._load_amis()
        super().__init__()

    def _load_amis(self):
        for ami in AMIS:
            ami_id = ami["ami_id"]
            # we are assuming the default loaded amis are owned by amazon
            # owner_alias is required for terraform owner filters
            ami["owner_alias"] = "amazon"
            self.amis[ami_id] = Ami(self, **ami)

    def create_image(
        self,
        instance_id,
        name=None,
        description=None,
        context=None,
        tag_specifications=None,
    ):
        # TODO: check that instance exists and pull info from it.
        ami_id = random_ami_id()
        instance = self.get_instance(instance_id)
        tags = []
        for tag_specification in tag_specifications:
            resource_type = tag_specification["ResourceType"]
            if resource_type == "image":
                tags += tag_specification["Tag"]
            elif resource_type == "snapshot":
                raise NotImplementedError()
            else:
                raise InvalidTaggableResourceType(resource_type)

        ami = Ami(
            self,
            ami_id,
            instance=instance,
            source_ami=None,
            name=name,
            description=description,
            owner_id=OWNER_ID,
            snapshot_description=f"Created by CreateImage({instance_id}) for {ami_id}",
        )
        for tag in tags:
            ami.add_tag(tag["Key"], tag["Value"])
        self.amis[ami_id] = ami
        return ami

    def copy_image(self, source_image_id, source_region, name=None, description=None):
        source_ami = ec2_backends[source_region].describe_images(
            ami_ids=[source_image_id]
        )[0]
        ami_id = random_ami_id()
        ami = Ami(
            self,
            ami_id,
            instance=None,
            source_ami=source_ami,
            name=name,
            description=description,
        )
        self.amis[ami_id] = ami
        return ami

    def describe_images(
        self, ami_ids=(), filters=None, exec_users=None, owners=None, context=None
    ):
        images = self.amis.copy().values()

        if len(ami_ids):
            # boto3 seems to default to just searching based on ami ids if that parameter is passed
            # and if no images are found, it raises an errors
            malformed_ami_ids = [
                ami_id for ami_id in ami_ids if not ami_id.startswith("ami-")
            ]
            if malformed_ami_ids:
                raise MalformedAMIIdError(malformed_ami_ids)

            images = [ami for ami in images if ami.id in ami_ids]
            if len(images) == 0:
                raise InvalidAMIIdError(ami_ids)
        else:
            # Limit images by launch permissions
            if exec_users:
                tmp_images = []
                for ami in images:
                    for user_id in exec_users:
                        if user_id in ami.launch_permission_users:
                            tmp_images.append(ami)
                images = tmp_images

            # Limit by owner ids
            if owners:
                # support filtering by Owners=['self']
                if "self" in owners:
                    owners = list(
                        map(lambda o: OWNER_ID if o == "self" else o, owners,)
                    )
                images = [
                    ami
                    for ami in images
                    if ami.owner_id in owners or ami.owner_alias in owners
                ]

            # Generic filters
            if filters:
                return generic_filter(filters, images)

        return images

    def deregister_image(self, ami_id):
        if ami_id in self.amis:
            self.amis.pop(ami_id)
            return True
        raise InvalidAMIIdError(ami_id)

    def get_launch_permission_groups(self, ami_id):
        ami = self.describe_images(ami_ids=[ami_id])[0]
        return ami.launch_permission_groups

    def get_launch_permission_users(self, ami_id):
        ami = self.describe_images(ami_ids=[ami_id])[0]
        return ami.launch_permission_users

    def validate_permission_targets(self, user_ids=None, group=None):
        # If anything is invalid, nothing is added. (No partial success.)
        if user_ids:
            """
            AWS docs:
              "The AWS account ID is a 12-digit number, such as 123456789012, that you use to construct Amazon Resource Names (ARNs)."
              http://docs.aws.amazon.com/general/latest/gr/acct-identifiers.html
            """
            for user_id in user_ids:
                if len(user_id) != 12 or not user_id.isdigit():
                    raise InvalidAMIAttributeItemValueError("userId", user_id)

        if group and group != "all":
            raise InvalidAMIAttributeItemValueError("UserGroup", group)

    def add_launch_permission(self, ami_id, user_ids=None, group=None):
        ami = self.describe_images(ami_ids=[ami_id])[0]
        self.validate_permission_targets(user_ids=user_ids, group=group)

        if user_ids:
            for user_id in user_ids:
                ami.launch_permission_users.add(user_id)

        if group:
            ami.launch_permission_groups.add(group)

        return True

    def register_image(self, name=None, description=None):
        ami_id = random_ami_id()
        ami = Ami(
            self,
            ami_id,
            instance=None,
            source_ami=None,
            name=name,
            description=description,
        )
        self.amis[ami_id] = ami
        return ami

    def remove_launch_permission(self, ami_id, user_ids=None, group=None):
        ami = self.describe_images(ami_ids=[ami_id])[0]
        self.validate_permission_targets(user_ids=user_ids, group=group)

        if user_ids:
            for user_id in user_ids:
                ami.launch_permission_users.discard(user_id)

        if group:
            ami.launch_permission_groups.discard(group)

        return True


class Region(object):
    def __init__(self, name, endpoint, opt_in_status):
        self.name = name
        self.endpoint = endpoint
        self.opt_in_status = opt_in_status


class Zone(object):
    def __init__(self, name, region_name, zone_id):
        self.name = name
        self.region_name = region_name
        self.zone_id = zone_id


class RegionsAndZonesBackend(object):
    regions_opt_in_not_required = [
        "af-south-1",
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-northeast-3",
        "ap-south-1",
        "ap-southeast-1",
        "ap-southeast-2",
        "ap-southeast-3",
        "ca-central-1",
        "eu-central-1",
        "eu-north-1",
        "eu-south-1",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "sa-east-1",
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
    ]

    regions = []
    for region in Session().get_available_regions("ec2"):
        if region in regions_opt_in_not_required:
            regions.append(
                Region(
                    region, "ec2.{}.amazonaws.com".format(region), "opt-in-not-required"
                )
            )
        else:
            regions.append(
                Region(region, "ec2.{}.amazonaws.com".format(region), "not-opted-in")
            )
    for region in Session().get_available_regions("ec2", partition_name="aws-us-gov"):
        regions.append(
            Region(region, "ec2.{}.amazonaws.com".format(region), "opt-in-not-required")
        )
    for region in Session().get_available_regions("ec2", partition_name="aws-cn"):
        regions.append(
            Region(
                region, "ec2.{}.amazonaws.com.cn".format(region), "opt-in-not-required"
            )
        )

    zones = {
        "af-south-1": [
            Zone(region_name="af-south-1", name="af-south-1a", zone_id="afs1-az1"),
            Zone(region_name="af-south-1", name="af-south-1b", zone_id="afs1-az2"),
            Zone(region_name="af-south-1", name="af-south-1c", zone_id="afs1-az3"),
        ],
        "ap-south-1": [
            Zone(region_name="ap-south-1", name="ap-south-1a", zone_id="aps1-az1"),
            Zone(region_name="ap-south-1", name="ap-south-1b", zone_id="aps1-az3"),
        ],
        "eu-west-3": [
            Zone(region_name="eu-west-3", name="eu-west-3a", zone_id="euw3-az1"),
            Zone(region_name="eu-west-3", name="eu-west-3b", zone_id="euw3-az2"),
            Zone(region_name="eu-west-3", name="eu-west-3c", zone_id="euw3-az3"),
        ],
        "eu-north-1": [
            Zone(region_name="eu-north-1", name="eu-north-1a", zone_id="eun1-az1"),
            Zone(region_name="eu-north-1", name="eu-north-1b", zone_id="eun1-az2"),
            Zone(region_name="eu-north-1", name="eu-north-1c", zone_id="eun1-az3"),
        ],
        "eu-west-2": [
            Zone(region_name="eu-west-2", name="eu-west-2a", zone_id="euw2-az2"),
            Zone(region_name="eu-west-2", name="eu-west-2b", zone_id="euw2-az3"),
            Zone(region_name="eu-west-2", name="eu-west-2c", zone_id="euw2-az1"),
        ],
        "eu-west-1": [
            Zone(region_name="eu-west-1", name="eu-west-1a", zone_id="euw1-az3"),
            Zone(region_name="eu-west-1", name="eu-west-1b", zone_id="euw1-az1"),
            Zone(region_name="eu-west-1", name="eu-west-1c", zone_id="euw1-az2"),
        ],
        "ap-northeast-3": [
            Zone(
                region_name="ap-northeast-3",
                name="ap-northeast-3a",
                zone_id="apne3-az1",
            ),
            Zone(
                region_name="ap-northeast-3",
                name="ap-northeast-3b",
                zone_id="apne3-az2",
            ),
            Zone(
                region_name="ap-northeast-3",
                name="ap-northeast-3c",
                zone_id="apne3-az3",
            ),
        ],
        "ap-northeast-2": [
            Zone(
                region_name="ap-northeast-2",
                name="ap-northeast-2a",
                zone_id="apne2-az1",
            ),
            Zone(
                region_name="ap-northeast-2",
                name="ap-northeast-2b",
                zone_id="apne2-az2",
            ),
            Zone(
                region_name="ap-northeast-2",
                name="ap-northeast-2c",
                zone_id="apne2-az3",
            ),
            Zone(
                region_name="ap-northeast-2",
                name="ap-northeast-2d",
                zone_id="apne2-az4",
            ),
        ],
        "ap-northeast-1": [
            Zone(
                region_name="ap-northeast-1",
                name="ap-northeast-1a",
                zone_id="apne1-az4",
            ),
            Zone(
                region_name="ap-northeast-1",
                name="ap-northeast-1c",
                zone_id="apne1-az1",
            ),
            Zone(
                region_name="ap-northeast-1",
                name="ap-northeast-1d",
                zone_id="apne1-az2",
            ),
        ],
        "ap-east-1": [
            Zone(region_name="ap-east-1", name="ap-east-1a", zone_id="ape1-az1"),
            Zone(region_name="ap-east-1", name="ap-east-1b", zone_id="ape1-az2"),
            Zone(region_name="ap-east-1", name="ap-east-1c", zone_id="ape1-az3"),
        ],
        "sa-east-1": [
            Zone(region_name="sa-east-1", name="sa-east-1a", zone_id="sae1-az1"),
            Zone(region_name="sa-east-1", name="sa-east-1c", zone_id="sae1-az3"),
        ],
        "ca-central-1": [
            Zone(region_name="ca-central-1", name="ca-central-1a", zone_id="cac1-az1"),
            Zone(region_name="ca-central-1", name="ca-central-1b", zone_id="cac1-az2"),
        ],
        "ap-southeast-1": [
            Zone(
                region_name="ap-southeast-1",
                name="ap-southeast-1a",
                zone_id="apse1-az1",
            ),
            Zone(
                region_name="ap-southeast-1",
                name="ap-southeast-1b",
                zone_id="apse1-az2",
            ),
            Zone(
                region_name="ap-southeast-1",
                name="ap-southeast-1c",
                zone_id="apse1-az3",
            ),
        ],
        "ap-southeast-2": [
            Zone(
                region_name="ap-southeast-2",
                name="ap-southeast-2a",
                zone_id="apse2-az1",
            ),
            Zone(
                region_name="ap-southeast-2",
                name="ap-southeast-2b",
                zone_id="apse2-az3",
            ),
            Zone(
                region_name="ap-southeast-2",
                name="ap-southeast-2c",
                zone_id="apse2-az2",
            ),
        ],
        "ap-southeast-3": [
            Zone(
                region_name="ap-southeast-3",
                name="ap-southeast-3a",
                zone_id="apse3-az1",
            ),
            Zone(
                region_name="ap-southeast-3",
                name="ap-southeast-3b",
                zone_id="apse3-az2",
            ),
            Zone(
                region_name="ap-southeast-3",
                name="ap-southeast-3c",
                zone_id="apse3-az3",
            ),
        ],
        "eu-central-1": [
            Zone(region_name="eu-central-1", name="eu-central-1a", zone_id="euc1-az2"),
            Zone(region_name="eu-central-1", name="eu-central-1b", zone_id="euc1-az3"),
            Zone(region_name="eu-central-1", name="eu-central-1c", zone_id="euc1-az1"),
        ],
        "eu-south-1": [
            Zone(region_name="eu-south-1", name="eu-south-1a", zone_id="eus1-az1"),
            Zone(region_name="eu-south-1", name="eu-south-1b", zone_id="eus1-az2"),
            Zone(region_name="eu-south-1", name="eu-south-1c", zone_id="eus1-az3"),
        ],
        "us-east-1": [
            Zone(region_name="us-east-1", name="us-east-1a", zone_id="use1-az6"),
            Zone(region_name="us-east-1", name="us-east-1b", zone_id="use1-az1"),
            Zone(region_name="us-east-1", name="us-east-1c", zone_id="use1-az2"),
            Zone(region_name="us-east-1", name="us-east-1d", zone_id="use1-az4"),
            Zone(region_name="us-east-1", name="us-east-1e", zone_id="use1-az3"),
            Zone(region_name="us-east-1", name="us-east-1f", zone_id="use1-az5"),
        ],
        "us-east-2": [
            Zone(region_name="us-east-2", name="us-east-2a", zone_id="use2-az1"),
            Zone(region_name="us-east-2", name="us-east-2b", zone_id="use2-az2"),
            Zone(region_name="us-east-2", name="us-east-2c", zone_id="use2-az3"),
        ],
        "us-west-1": [
            Zone(region_name="us-west-1", name="us-west-1a", zone_id="usw1-az3"),
            Zone(region_name="us-west-1", name="us-west-1b", zone_id="usw1-az1"),
        ],
        "us-west-2": [
            Zone(region_name="us-west-2", name="us-west-2a", zone_id="usw2-az2"),
            Zone(region_name="us-west-2", name="us-west-2b", zone_id="usw2-az1"),
            Zone(region_name="us-west-2", name="us-west-2c", zone_id="usw2-az3"),
        ],
        "me-south-1": [
            Zone(region_name="me-south-1", name="me-south-1a", zone_id="mes1-az1"),
            Zone(region_name="me-south-1", name="me-south-1b", zone_id="mes1-az2"),
            Zone(region_name="me-south-1", name="me-south-1c", zone_id="mes1-az3"),
        ],
        "cn-north-1": [
            Zone(region_name="cn-north-1", name="cn-north-1a", zone_id="cnn1-az1"),
            Zone(region_name="cn-north-1", name="cn-north-1b", zone_id="cnn1-az2"),
        ],
        "cn-northwest-1": [
            Zone(
                region_name="cn-northwest-1",
                name="cn-northwest-1a",
                zone_id="cnnw1-az1",
            ),
            Zone(
                region_name="cn-northwest-1",
                name="cn-northwest-1b",
                zone_id="cnnw1-az2",
            ),
            Zone(
                region_name="cn-northwest-1",
                name="cn-northwest-1c",
                zone_id="cnnw1-az3",
            ),
        ],
        "us-gov-west-1": [
            Zone(
                region_name="us-gov-west-1", name="us-gov-west-1a", zone_id="usgw1-az1"
            ),
            Zone(
                region_name="us-gov-west-1", name="us-gov-west-1b", zone_id="usgw1-az2"
            ),
            Zone(
                region_name="us-gov-west-1", name="us-gov-west-1c", zone_id="usgw1-az3"
            ),
        ],
        "us-gov-east-1": [
            Zone(
                region_name="us-gov-east-1", name="us-gov-east-1a", zone_id="usge1-az1"
            ),
            Zone(
                region_name="us-gov-east-1", name="us-gov-east-1b", zone_id="usge1-az2"
            ),
            Zone(
                region_name="us-gov-east-1", name="us-gov-east-1c", zone_id="usge1-az3"
            ),
        ],
    }

    def describe_regions(self, region_names=None):
        if not region_names:
            return self.regions
        ret = []
        for name in region_names:
            for region in self.regions:
                if region.name == name:
                    ret.append(region)
        return ret

    def describe_availability_zones(self):
        # We might not have any zones for the current region, if it was introduced recently
        return self.zones.get(self.region_name, [])

    def get_zone_by_name(self, name):
        for zone in self.describe_availability_zones():
            if zone.name == name:
                return zone


class SecurityRule(object):
    def __init__(
        self,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups,
        prefix_list_ids=None,
    ):
        self.id = random_security_group_rule_id()
        self.ip_protocol = str(ip_protocol)
        self.ip_ranges = ip_ranges or []
        self.source_groups = source_groups or []
        self.prefix_list_ids = prefix_list_ids or []
        self.from_port = self.to_port = None

        if self.ip_protocol != "-1":
            self.from_port = int(from_port)
            self.to_port = int(to_port)

        ip_protocol_keywords = {
            "tcp": "tcp",
            "6": "tcp",
            "udp": "udp",
            "17": "udp",
            "all": "-1",
            "-1": "-1",
            "tCp": "tcp",
            "6": "tcp",
            "UDp": "udp",
            "17": "udp",
            "ALL": "-1",
            "icMp": "icmp",
            "1": "icmp",
            "icmp": "icmp",
        }
        proto = ip_protocol_keywords.get(self.ip_protocol.lower())
        self.ip_protocol = proto if proto else self.ip_protocol

    @property
    def owner_id(self):
        return ACCOUNT_ID

    def __eq__(self, other):
        if self.ip_protocol != other.ip_protocol:
            return False
        ip_ranges = list(
            [item for item in self.ip_ranges if item not in other.ip_ranges]
            + [item for item in other.ip_ranges if item not in self.ip_ranges]
        )
        if ip_ranges:
            return False
        source_groups = list(
            [item for item in self.source_groups if item not in other.source_groups]
            + [item for item in other.source_groups if item not in self.source_groups]
        )
        if source_groups:
            return False
        prefix_list_ids = list(
            [item for item in self.prefix_list_ids if item not in other.prefix_list_ids]
            + [
                item
                for item in other.prefix_list_ids
                if item not in self.prefix_list_ids
            ]
        )
        if prefix_list_ids:
            return False
        if self.ip_protocol != "-1":
            if self.from_port != other.from_port:
                return False
            if self.to_port != other.to_port:
                return False

        return True


class SecurityGroup(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        group_id,
        name,
        description,
        vpc_id=None,
        tags=None,
        is_default=None,
    ):
        self.ec2_backend = ec2_backend
        self.id = group_id
        self.group_id = self.id
        self.name = name
        self.group_name = self.name
        self.description = description
        self.ingress_rules = []
        self.egress_rules = []
        self.enis = {}
        self.vpc_id = vpc_id
        self.owner_id = ACCOUNT_ID
        self.add_tags(tags or {})
        self.is_default = is_default or False

        # Append default IPv6 egress rule for VPCs with IPv6 support
        if vpc_id:
            vpc = self.ec2_backend.vpcs.get(vpc_id)
            if vpc:
                self.egress_rules.append(
                    SecurityRule("-1", None, None, [{"CidrIp": "0.0.0.0/0"}], [])
                )
            if vpc and len(vpc.get_cidr_block_association_set(ipv6=True)) > 0:
                self.egress_rules.append(
                    SecurityRule("-1", None, None, [{"CidrIpv6": "::/0"}], [])
                )

        # each filter as a simple function in a mapping

        self.filters = {
            "description": self.filter_description,
            "egress.ip-permission.cidr": self.filter_egress__ip_permission__cidr,
            "egress.ip-permission.from-port": self.filter_egress__ip_permission__from_port,
            "egress.ip-permission.group-id": self.filter_egress__ip_permission__group_id,
            "egress.ip-permission.group-name": self.filter_egress__ip_permission__group_name,
            "egress.ip-permission.ipv6-cidr": self.filter_egress__ip_permission__ipv6_cidr,
            "egress.ip-permission.prefix-list-id": self.filter_egress__ip_permission__prefix_list_id,
            "egress.ip-permission.protocol": self.filter_egress__ip_permission__protocol,
            "egress.ip-permission.to-port": self.filter_egress__ip_permission__to_port,
            "egress.ip-permission.user-id": self.filter_egress__ip_permission__user_id,
            "group-id": self.filter_group_id,
            "group-name": self.filter_group_name,
            "ip-permission.cidr": self.filter_ip_permission__cidr,
            "ip-permission.from-port": self.filter_ip_permission__from_port,
            "ip-permission.group-id": self.filter_ip_permission__group_id,
            "ip-permission.group-name": self.filter_ip_permission__group_name,
            "ip-permission.ipv6-cidr": self.filter_ip_permission__ipv6_cidr,
            "ip-permission.prefix-list-id": self.filter_ip_permission__prefix_list_id,
            "ip-permission.protocol": self.filter_ip_permission__protocol,
            "ip-permission.to-port": self.filter_ip_permission__to_port,
            "ip-permission.user-id": self.filter_ip_permission__user_id,
            "owner-id": self.filter_owner_id,
            "vpc-id": self.filter_vpc_id,
        }

    @staticmethod
    def cloudformation_name_type():
        return "GroupName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-securitygroup.html
        return "AWS::EC2::SecurityGroup"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[region_name]
        vpc_id = properties.get("VpcId")
        security_group = ec2_backend.create_security_group(
            name=resource_name,
            description=properties.get("GroupDescription"),
            vpc_id=vpc_id,
        )

        for tag in properties.get("Tags", []):
            tag_key = tag["Key"]
            tag_value = tag["Value"]
            security_group.add_tag(tag_key, tag_value)

        for ingress_rule in properties.get("SecurityGroupIngress", []):
            source_group_id = ingress_rule.get("SourceSecurityGroupId",)
            source_group_name = ingress_rule.get("SourceSecurityGroupName",)
            source_group = {}
            if source_group_id:
                source_group["GroupId"] = source_group_id
            if source_group_name:
                source_group["GroupName"] = source_group_name

            ec2_backend.authorize_security_group_ingress(
                group_name_or_id=security_group.id,
                ip_protocol=ingress_rule["IpProtocol"],
                from_port=ingress_rule["FromPort"],
                to_port=ingress_rule["ToPort"],
                ip_ranges=ingress_rule.get("CidrIp"),
                source_groups=[source_group] if source_group else [],
                vpc_id=vpc_id,
            )

        return security_group

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        cls._delete_security_group_given_vpc_id(
            original_resource.name, original_resource.vpc_id, region_name
        )
        return cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, region_name
        )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        vpc_id = properties.get("VpcId")
        cls._delete_security_group_given_vpc_id(resource_name, vpc_id, region_name)

    @classmethod
    def _delete_security_group_given_vpc_id(cls, resource_name, vpc_id, region_name):
        ec2_backend = ec2_backends[region_name]
        security_group = ec2_backend.get_security_group_by_name_or_id(
            resource_name, vpc_id
        )
        if security_group:
            security_group.delete(region_name)

    def delete(self, region_name):
        """Not exposed as part of the ELB API - used for CloudFormation."""
        self.ec2_backend.delete_security_group(group_id=self.id)

    @property
    def physical_resource_id(self):
        return self.id

    def filter_description(self, values):
        for value in values:
            if aws_api_matches(value, self.description):
                return True
        return False

    def filter_egress__ip_permission__cidr(self, values):
        for value in values:
            for rule in self.egress_rules:
                for cidr in rule.ip_ranges:
                    if aws_api_matches(value, cidr.get("CidrIp", "NONE")):
                        return True
        return False

    def filter_egress__ip_permission__from_port(self, values):
        for value in values:
            for rule in self.egress_rules:
                if rule.ip_protocol != -1 and aws_api_matches(
                    value, str(rule.from_port)
                ):
                    return True
        return False

    def filter_egress__ip_permission__group_id(self, values):
        for value in values:
            for rule in self.egress_rules:
                for sg in rule.source_groups:
                    if aws_api_matches(value, sg.get("GroupId", None)):
                        return True
        return False

    def filter_egress__ip_permission__group_name(self, values):
        for value in values:
            for rule in self.egress_rules:
                for group in rule.source_groups:
                    if aws_api_matches(value, group.get("GroupName", None)):
                        return True
        return False

    def filter_egress__ip_permission__ipv6_cidr(self, values):
        raise MotoNotImplementedError("egress.ip-permission.ipv6-cidr filter")

    def filter_egress__ip_permission__prefix_list_id(self, values):
        raise MotoNotImplementedError("egress.ip-permission.prefix-list-id filter")

    def filter_egress__ip_permission__protocol(self, values):
        for value in values:
            for rule in self.egress_rules:
                if aws_api_matches(value, rule.ip_protocol):
                    return True
        return False

    def filter_egress__ip_permission__to_port(self, values):
        for value in values:
            for rule in self.egress_rules:
                if aws_api_matches(value, rule.to_port):
                    return True
        return False

    def filter_egress__ip_permission__user_id(self, values):
        for value in values:
            for rule in self.egress_rules:
                if aws_api_matches(value, rule.owner_id):
                    return True
        return False

    def filter_group_id(self, values):
        for value in values:
            if aws_api_matches(value, self.id):
                return True
        return False

    def filter_group_name(self, values):
        for value in values:
            if aws_api_matches(value, self.group_name):
                return True
        return False

    def filter_ip_permission__cidr(self, values):
        for value in values:
            for rule in self.ingress_rules:
                for cidr in rule.ip_ranges:
                    if aws_api_matches(value, cidr.get("CidrIp", "NONE")):
                        return True
        return False

    def filter_ip_permission__from_port(self, values):
        for value in values:
            for rule in self.ingress_rules:
                if aws_api_matches(value, rule.from_port):
                    return True
        return False

    def filter_ip_permission__group_id(self, values):
        for value in values:
            for rule in self.ingress_rules:
                for group in rule.source_groups:
                    if aws_api_matches(value, group.get("GroupId", None)):
                        return True
        return False

    def filter_ip_permission__group_name(self, values):
        for value in values:
            for rule in self.ingress_rules:
                for group in rule.source_groups:
                    if aws_api_matches(value, group.get("GroupName", None)):
                        return True
        return False

    def filter_ip_permission__ipv6_cidr(self, values):
        raise MotoNotImplementedError("ip-permission.ipv6 filter")

    def filter_ip_permission__prefix_list_id(self, values):
        raise MotoNotImplementedError("ip-permission.prefix-list-id filter")

    def filter_ip_permission__protocol(self, values):
        for value in values:
            for rule in self.ingress_rules:
                if aws_api_matches(value, rule.protocol):
                    return True
        return False

    def filter_ip_permission__to_port(self, values):
        for value in values:
            for rule in self.ingress_rules:
                if aws_api_matches(value, rule.to_port):
                    return True
        return False

    def filter_ip_permission__user_id(self, values):
        for value in values:
            for rule in self.ingress_rules:
                if aws_api_matches(value, rule.owner_id):
                    return True
        return False

    def filter_owner_id(self, values):
        for value in values:
            if aws_api_matches(value, self.owner_id):
                return True
        return False

    def filter_vpc_id(self, values):
        for value in values:
            if aws_api_matches(value, self.vpc_id):
                return True
        return False

    def matches_filter(self, key, filter_value):
        if is_tag_filter(key):
            tag_value = self.get_filter_value(key)
            if isinstance(filter_value, list):
                return tag_filter_matches(self, key, filter_value)
            return tag_value in filter_value
        else:
            return self.filters[key](filter_value)

    def matches_filters(self, filters):
        for key, value in filters.items():
            if not self.matches_filter(key, value):
                return False
        return True

    @classmethod
    def has_cfn_attr(cls, attribute):
        return attribute in ["GroupId"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "GroupId":
            return self.id
        raise UnformattedGetAttTemplateException()

    def add_ingress_rule(self, rule):
        if rule in self.ingress_rules:
            raise InvalidPermissionDuplicateError()
        self.ingress_rules.append(rule)

    def add_egress_rule(self, rule):
        if rule in self.egress_rules:
            raise InvalidPermissionDuplicateError()
        self.egress_rules.append(rule)

    def get_number_of_ingress_rules(self):
        return sum(
            len(rule.ip_ranges) + len(rule.source_groups) for rule in self.ingress_rules
        )

    def get_number_of_egress_rules(self):
        return sum(
            len(rule.ip_ranges) + len(rule.source_groups) for rule in self.egress_rules
        )


class SecurityGroupBackend(object):
    def __init__(self):
        # the key in the dict group is the vpc_id or None (non-vpc)
        self.groups = defaultdict(dict)
        # This will help us in RuleLimitExceed errors.
        self.sg_old_ingress_ruls = {}
        self.sg_old_egress_ruls = {}

        super().__init__()

    def create_security_group(
        self, name, description, vpc_id=None, tags=None, force=False, is_default=None
    ):
        vpc_id = vpc_id or self.default_vpc.id
        if not description:
            raise MissingParameterError("GroupDescription")

        group_id = random_security_group_id()
        if not force:
            existing_group = self.get_security_group_by_name_or_id(name, vpc_id)
            if existing_group:
                raise InvalidSecurityGroupDuplicateError(name)
        group = SecurityGroup(
            self,
            group_id,
            name,
            description,
            vpc_id=vpc_id,
            tags=tags,
            is_default=is_default,
        )

        self.groups[vpc_id][group_id] = group
        return group

    def describe_security_groups(self, group_ids=None, groupnames=None, filters=None):
        all_groups = self.groups.copy()
        matches = itertools.chain(*[x.copy().values() for x in all_groups.values()])
        if group_ids:
            matches = [grp for grp in matches if grp.id in group_ids]
            if len(group_ids) > len(matches):
                unknown_ids = set(group_ids) - set(matches)
                raise InvalidSecurityGroupNotFoundError(unknown_ids)
        if groupnames:
            matches = [grp for grp in matches if grp.name in groupnames]
            if len(groupnames) > len(matches):
                unknown_names = set(groupnames) - set(matches)
                raise InvalidSecurityGroupNotFoundError(unknown_names)
        if filters:
            matches = [grp for grp in matches if grp.matches_filters(filters)]

        return matches

    def _delete_security_group(self, vpc_id, group_id):
        vpc_id = vpc_id or self.default_vpc.id
        if self.groups[vpc_id][group_id].enis:
            raise DependencyViolationError(
                "{0} is being utilized by {1}".format(group_id, "ENIs")
            )
        return self.groups[vpc_id].pop(group_id)

    def delete_security_group(self, name=None, group_id=None):
        if group_id:
            # loop over all the SGs, find the right one
            for vpc_id, groups in self.groups.items():
                if group_id in groups:
                    return self._delete_security_group(vpc_id, group_id)
            raise InvalidSecurityGroupNotFoundError(group_id)
        elif name:
            # Group Name.  Has to be in standard EC2, VPC needs to be
            # identified by group_id
            group = self.get_security_group_by_name_or_id(name)
            if group:
                return self._delete_security_group(None, group.id)
            raise InvalidSecurityGroupNotFoundError(name)

    def get_security_group_from_id(self, group_id):
        # 2 levels of chaining necessary since it's a complex structure
        all_groups = itertools.chain.from_iterable(
            [x.copy().values() for x in self.groups.copy().values()]
        )
        for group in all_groups:
            if group.id == group_id:
                return group

    def get_security_group_from_name(self, name, vpc_id=None):
        if vpc_id:
            for group in self.groups[vpc_id].values():
                if group.name == name:
                    return group
        else:
            for vpc_id in self.groups:
                for group in self.groups[vpc_id].values():
                    if group.name == name:
                        return group

    def get_security_group_by_name_or_id(self, group_name_or_id, vpc_id=None):

        # try searching by id, fallbacks to name search
        group = self.get_security_group_from_id(group_name_or_id)
        if group is None:
            group = self.get_security_group_from_name(group_name_or_id, vpc_id)
        return group

    def get_default_security_group(self, vpc_id=None):
        for group in self.groups[vpc_id or self.default_vpc.id].values():
            if group.is_default:
                return group

    def authorize_security_group_ingress(
        self,
        group_name_or_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups=None,
        prefix_list_ids=None,
        vpc_id=None,
    ):
        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)
        if group is None:
            raise InvalidSecurityGroupNotFoundError(group_name_or_id)
        if ip_ranges:
            if isinstance(ip_ranges, str):
                ip_ranges = [{"CidrIp": str(ip_ranges)}]
            elif not isinstance(ip_ranges, list):
                ip_ranges = [json.loads(ip_ranges)]
        if ip_ranges:
            for cidr in ip_ranges:
                if (
                    type(cidr) is dict
                    and not any(
                        [
                            is_valid_cidr(cidr.get("CidrIp", "")),
                            is_valid_ipv6_cidr(cidr.get("CidrIpv6", "")),
                        ]
                    )
                ) or (
                    type(cidr) is str
                    and not any([is_valid_cidr(cidr), is_valid_ipv6_cidr(cidr)])
                ):
                    raise InvalidCIDRSubnetError(cidr=cidr)

        self._verify_group_will_respect_rule_count_limit(
            group, group.get_number_of_ingress_rules(), ip_ranges, source_groups,
        )

        _source_groups = self._add_source_group(source_groups, vpc_id)

        security_rule = SecurityRule(
            ip_protocol, from_port, to_port, ip_ranges, _source_groups, prefix_list_ids
        )

        if security_rule in group.ingress_rules:
            raise InvalidPermissionDuplicateError()
        # To match drift property of the security rules.
        # If no rule found then add security_rule as a new rule
        for rule in group.ingress_rules:
            if (
                security_rule.from_port == rule.from_port
                and security_rule.to_port == rule.to_port
                and security_rule.ip_protocol == rule.ip_protocol
            ):
                rule.ip_ranges.extend(
                    [
                        item
                        for item in security_rule.ip_ranges
                        if item not in rule.ip_ranges
                    ]
                )
                rule.source_groups.extend(
                    [
                        item
                        for item in security_rule.source_groups
                        if item not in rule.source_groups
                    ]
                )
                rule.prefix_list_ids.extend(
                    [
                        item
                        for item in security_rule.prefix_list_ids
                        if item not in rule.prefix_list_ids
                    ]
                )
                security_rule = rule
                break
        else:
            group.add_ingress_rule(security_rule)
        return security_rule, group

    def revoke_security_group_ingress(
        self,
        group_name_or_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups=None,
        prefix_list_ids=None,
        vpc_id=None,
    ):

        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)

        _source_groups = self._add_source_group(source_groups, vpc_id)

        security_rule = SecurityRule(
            ip_protocol, from_port, to_port, ip_ranges, _source_groups, prefix_list_ids
        )

        # To match drift property of the security rules.
        for rule in group.ingress_rules:
            if (
                security_rule.from_port == rule.from_port
                and security_rule.to_port == rule.to_port
                and security_rule.ip_protocol == rule.ip_protocol
            ):
                security_rule = copy.deepcopy(rule)
                security_rule.ip_ranges.extend(
                    [item for item in ip_ranges if item not in rule.ip_ranges]
                )
                security_rule.source_groups.extend(
                    [item for item in _source_groups if item not in rule.source_groups]
                )
                security_rule.prefix_list_ids.extend(
                    [
                        item
                        for item in prefix_list_ids
                        if item not in rule.prefix_list_ids
                    ]
                )
                break

        if security_rule in group.ingress_rules:
            rule = group.ingress_rules[group.ingress_rules.index(security_rule)]
            self._remove_items_from_rule(
                ip_ranges, _source_groups, prefix_list_ids, rule
            )

            if (
                not rule.prefix_list_ids
                and not rule.source_groups
                and not rule.ip_ranges
            ):
                group.ingress_rules.remove(rule)
            self.sg_old_ingress_ruls[group.id] = group.ingress_rules.copy()
            return security_rule
        raise InvalidPermissionNotFoundError()

    def authorize_security_group_egress(
        self,
        group_name_or_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups=None,
        prefix_list_ids=None,
        vpc_id=None,
    ):
        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)
        if group is None:
            raise InvalidSecurityGroupNotFoundError(group_name_or_id)
        if ip_ranges and not isinstance(ip_ranges, list):

            if isinstance(ip_ranges, str) and "CidrIp" not in ip_ranges:
                ip_ranges = [{"CidrIp": ip_ranges}]
            else:
                ip_ranges = [json.loads(ip_ranges)]
        if ip_ranges:
            for cidr in ip_ranges:
                if (
                    type(cidr) is dict
                    and not any(
                        [
                            is_valid_cidr(cidr.get("CidrIp", "")),
                            is_valid_ipv6_cidr(cidr.get("CidrIpv6", "")),
                        ]
                    )
                ) or (
                    type(cidr) is str
                    and not any([is_valid_cidr(cidr), is_valid_ipv6_cidr(cidr)])
                ):
                    raise InvalidCIDRSubnetError(cidr=cidr)
        self._verify_group_will_respect_rule_count_limit(
            group,
            group.get_number_of_egress_rules(),
            ip_ranges,
            source_groups,
            egress=True,
        )

        _source_groups = self._add_source_group(source_groups, vpc_id)

        security_rule = SecurityRule(
            ip_protocol, from_port, to_port, ip_ranges, _source_groups, prefix_list_ids
        )

        if security_rule in group.egress_rules:
            raise InvalidPermissionDuplicateError()
        # To match drift property of the security rules.
        # If no rule found then add security_rule as a new rule
        for rule in group.egress_rules:
            if (
                security_rule.from_port == rule.from_port
                and security_rule.to_port == rule.to_port
                and security_rule.ip_protocol == rule.ip_protocol
            ):
                rule.ip_ranges.extend(
                    [
                        item
                        for item in security_rule.ip_ranges
                        if item not in rule.ip_ranges
                    ]
                )
                rule.source_groups.extend(
                    [
                        item
                        for item in security_rule.source_groups
                        if item not in rule.source_groups
                    ]
                )
                rule.prefix_list_ids.extend(
                    [
                        item
                        for item in security_rule.prefix_list_ids
                        if item not in rule.prefix_list_ids
                    ]
                )
                security_rule = rule
                break
        else:
            group.add_egress_rule(security_rule)

        return security_rule, group

    def revoke_security_group_egress(
        self,
        group_name_or_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups=None,
        prefix_list_ids=None,
        vpc_id=None,
    ):

        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)

        _source_groups = self._add_source_group(source_groups, vpc_id)

        # I don't believe this is required after changing the default egress rule
        # to be {'CidrIp': '0.0.0.0/0'} instead of just '0.0.0.0/0'
        # Not sure why this would return only the IP if it was 0.0.0.0/0 instead of
        # the ip_range?
        # for ip in ip_ranges:
        #     ip_ranges = [ip.get("CidrIp") if ip.get("CidrIp") == "0.0.0.0/0" else ip]

        if group.vpc_id:
            vpc = self.vpcs.get(group.vpc_id)
            if vpc and not len(vpc.get_cidr_block_association_set(ipv6=True)) > 0:
                for item in ip_ranges.copy():
                    if "CidrIpv6" in item:
                        ip_ranges.remove(item)

        security_rule = SecurityRule(
            ip_protocol, from_port, to_port, ip_ranges, _source_groups, prefix_list_ids
        )

        # To match drift property of the security rules.
        # If no rule found then add security_rule as a new rule
        for rule in group.egress_rules:
            if (
                security_rule.from_port == rule.from_port
                and security_rule.to_port == rule.to_port
                and security_rule.ip_protocol == rule.ip_protocol
            ):
                security_rule = copy.deepcopy(rule)
                security_rule.ip_ranges.extend(
                    [item for item in ip_ranges if item not in rule.ip_ranges]
                )
                security_rule.source_groups.extend(
                    [item for item in _source_groups if item not in rule.source_groups]
                )
                security_rule.prefix_list_ids.extend(
                    [
                        item
                        for item in prefix_list_ids
                        if item not in rule.prefix_list_ids
                    ]
                )
                break

        if security_rule in group.egress_rules:
            rule = group.egress_rules[group.egress_rules.index(security_rule)]
            self._remove_items_from_rule(
                ip_ranges, _source_groups, prefix_list_ids, rule
            )
            if (
                not rule.prefix_list_ids
                and not rule.source_groups
                and not rule.ip_ranges
            ):
                group.egress_rules.remove(rule)
            self.sg_old_egress_ruls[group.id] = group.egress_rules.copy()
            return security_rule
        raise InvalidPermissionNotFoundError()

    def update_security_group_rule_descriptions_ingress(
        self,
        group_name_or_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups=None,
        prefix_list_ids=None,
        vpc_id=None,
    ):

        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)
        if group is None:
            raise InvalidSecurityGroupNotFoundError(group_name_or_id)
        if ip_ranges and not isinstance(ip_ranges, list):

            if isinstance(ip_ranges, str) and "CidrIp" not in ip_ranges:
                ip_ranges = [{"CidrIp": ip_ranges}]
            else:
                ip_ranges = [json.loads(ip_ranges)]
        if ip_ranges:
            for cidr in ip_ranges:
                if (
                    type(cidr) is dict
                    and not any(
                        [
                            is_valid_cidr(cidr.get("CidrIp", "")),
                            is_valid_ipv6_cidr(cidr.get("CidrIpv6", "")),
                        ]
                    )
                ) or (
                    type(cidr) is str
                    and not any([is_valid_cidr(cidr), is_valid_ipv6_cidr(cidr)])
                ):
                    raise InvalidCIDRSubnetError(cidr=cidr)
        _source_groups = self._add_source_group(source_groups, vpc_id)

        security_rule = SecurityRule(
            ip_protocol, from_port, to_port, ip_ranges, _source_groups, prefix_list_ids
        )
        for rule in group.ingress_rules:
            if (
                security_rule.from_port == rule.from_port
                and security_rule.to_port == rule.to_port
                and security_rule.ip_protocol == rule.ip_protocol
            ):
                self._sg_update_description(security_rule, rule)
        return group

    def update_security_group_rule_descriptions_egress(
        self,
        group_name_or_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups=None,
        prefix_list_ids=None,
        vpc_id=None,
    ):

        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)
        if group is None:
            raise InvalidSecurityGroupNotFoundError(group_name_or_id)
        if ip_ranges and not isinstance(ip_ranges, list):

            if isinstance(ip_ranges, str) and "CidrIp" not in ip_ranges:
                ip_ranges = [{"CidrIp": ip_ranges}]
            else:
                ip_ranges = [json.loads(ip_ranges)]
        if ip_ranges:
            for cidr in ip_ranges:
                if (
                    type(cidr) is dict
                    and not any(
                        [
                            is_valid_cidr(cidr.get("CidrIp", "")),
                            is_valid_ipv6_cidr(cidr.get("CidrIpv6", "")),
                        ]
                    )
                ) or (
                    type(cidr) is str
                    and not any([is_valid_cidr(cidr), is_valid_ipv6_cidr(cidr)])
                ):
                    raise InvalidCIDRSubnetError(cidr=cidr)
        _source_groups = self._add_source_group(source_groups, vpc_id)

        security_rule = SecurityRule(
            ip_protocol, from_port, to_port, ip_ranges, _source_groups, prefix_list_ids
        )
        for rule in group.egress_rules:
            if (
                security_rule.from_port == rule.from_port
                and security_rule.to_port == rule.to_port
                and security_rule.ip_protocol == rule.ip_protocol
            ):
                self._sg_update_description(security_rule, rule)
        return group

    def _sg_update_description(self, security_rule, rule):
        for item in security_rule.ip_ranges:
            for cidr_item in rule.ip_ranges:
                if cidr_item.get("CidrIp") == item.get("CidrIp"):
                    cidr_item["Description"] = item.get("Description")
                if cidr_item.get("CidrIp6") == item.get("CidrIp6"):
                    cidr_item["Description"] = item.get("Description")

            for item in security_rule.source_groups:
                for source_group in rule.source_groups:
                    if source_group.get("GroupId") == item.get(
                        "GroupId"
                    ) or source_group.get("GroupName") == item.get("GroupName"):
                        source_group["Description"] = item.get("Description")

            for item in security_rule.source_groups:
                for source_group in rule.source_groups:
                    if source_group.get("GroupId") == item.get(
                        "GroupId"
                    ) or source_group.get("GroupName") == item.get("GroupName"):
                        source_group["Description"] = item.get("Description")

    def _remove_items_from_rule(self, ip_ranges, _source_groups, prefix_list_ids, rule):
        for item in ip_ranges:
            if item not in rule.ip_ranges:
                raise InvalidPermissionNotFoundError()
            else:
                rule.ip_ranges.remove(item)

        for item in _source_groups:
            if item not in rule.source_groups:
                raise InvalidPermissionNotFoundError()
            else:
                rule.source_groups.remove(item)

        for item in prefix_list_ids:
            if item not in rule.prefix_list_ids:
                raise InvalidPermissionNotFoundError()
            else:
                rule.prefix_list_ids.remove(item)
        pass

    def _add_source_group(self, source_groups, vpc_id):
        _source_groups = []
        for item in source_groups or []:
            if "OwnerId" not in item:
                item["OwnerId"] = ACCOUNT_ID
            # for VPCs
            if "GroupId" in item:
                if not self.get_security_group_by_name_or_id(
                    item.get("GroupId"), vpc_id
                ):
                    raise InvalidSecurityGroupNotFoundError(item.get("GroupId"))
            if "GroupName" in item:
                source_group = self.get_security_group_by_name_or_id(
                    item.get("GroupName"), vpc_id
                )
                if not source_group:
                    raise InvalidSecurityGroupNotFoundError(item.get("GroupName"))
                else:
                    item["GroupId"] = source_group.id
                    item.pop("GroupName")

            _source_groups.append(item)
        return _source_groups

    def _verify_group_will_respect_rule_count_limit(
        self, group, current_rule_nb, ip_ranges, source_groups=None, egress=False,
    ):
        max_nb_rules = 60 if group.vpc_id else 100
        future_group_nb_rules = current_rule_nb
        if ip_ranges:
            future_group_nb_rules += len(ip_ranges)
        if source_groups:
            future_group_nb_rules += len(source_groups)
        if future_group_nb_rules > max_nb_rules:
            if group and not egress:
                group.ingress_rules = self.sg_old_ingress_ruls[group.id]
            if group and egress:
                group.egress_rules = self.sg_old_egress_ruls[group.id]
            raise RulesPerSecurityGroupLimitExceededError


class SecurityGroupIngress(CloudFormationModel):
    def __init__(self, security_group, properties):
        self.security_group = security_group
        self.properties = properties

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-securitygroupingress.html
        return "AWS::EC2::SecurityGroupIngress"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[region_name]
        group_name = properties.get("GroupName")
        group_id = properties.get("GroupId")
        ip_protocol = properties.get("IpProtocol")
        cidr_ip = properties.get("CidrIp")
        cidr_desc = properties.get("Description")
        cidr_ipv6 = properties.get("CidrIpv6")
        from_port = properties.get("FromPort")
        source_security_group_id = properties.get("SourceSecurityGroupId")
        source_security_group_name = properties.get("SourceSecurityGroupName")
        # source_security_owner_id =
        # properties.get("SourceSecurityGroupOwnerId")  # IGNORED AT THE MOMENT
        to_port = properties.get("ToPort")

        assert group_id or group_name
        assert (
            source_security_group_name
            or cidr_ip
            or cidr_ipv6
            or source_security_group_id
        )
        assert ip_protocol

        source_group = {}
        if source_security_group_id:
            source_group["GroupId"] = source_security_group_id
        if source_security_group_name:
            source_group["GroupName"] = source_security_group_name
        if cidr_ip:
            ip_ranges = [{"CidrIp": cidr_ip, "Description": cidr_desc}]
        else:
            ip_ranges = []

        if group_id:
            security_group = ec2_backend.describe_security_groups(group_ids=[group_id])[
                0
            ]
        else:
            security_group = ec2_backend.describe_security_groups(
                groupnames=[group_name]
            )[0]

        ec2_backend.authorize_security_group_ingress(
            group_name_or_id=security_group.id,
            ip_protocol=ip_protocol,
            from_port=from_port,
            to_port=to_port,
            ip_ranges=ip_ranges,
            source_groups=[source_group] if source_group else [],
        )

        return cls(security_group, properties)


class VolumeAttachment(CloudFormationModel):
    def __init__(self, volume, instance, device, status):
        self.volume = volume
        self.attach_time = utc_date_and_time()
        self.instance = instance
        self.device = device
        self.status = status

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-volumeattachment.html
        return "AWS::EC2::VolumeAttachment"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        instance_id = properties["InstanceId"]
        volume_id = properties["VolumeId"]

        ec2_backend = ec2_backends[region_name]
        attachment = ec2_backend.attach_volume(
            volume_id=volume_id,
            instance_id=instance_id,
            device_path=properties["Device"],
        )
        return attachment


class Volume(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        volume_id,
        size,
        zone,
        snapshot_id=None,
        encrypted=False,
        kms_key_id=None,
        volume_type=None,
    ):
        self.id = volume_id
        self.volume_type = volume_type or "gp2"
        self.size = size
        self.zone = zone
        self.create_time = utc_date_and_time()
        self.attachment = None
        self.snapshot_id = snapshot_id
        self.ec2_backend = ec2_backend
        self.encrypted = encrypted
        self.kms_key_id = kms_key_id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-volume.html
        return "AWS::EC2::Volume"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[region_name]
        volume = ec2_backend.create_volume(
            size=properties.get("Size"), zone_name=properties.get("AvailabilityZone")
        )
        return volume

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def status(self):
        if self.attachment:
            return "in-use"
        else:
            return "available"

    def get_filter_value(self, filter_name):
        if filter_name.startswith("attachment") and not self.attachment:
            return None
        elif filter_name == "attachment.attach-time":
            return self.attachment.attach_time
        elif filter_name == "attachment.device":
            return self.attachment.device
        elif filter_name == "attachment.instance-id":
            return self.attachment.instance.id
        elif filter_name == "attachment.status":
            return self.attachment.status
        elif filter_name == "create-time":
            return self.create_time
        elif filter_name == "size":
            return self.size
        elif filter_name == "snapshot-id":
            return self.snapshot_id
        elif filter_name == "status":
            return self.status
        elif filter_name == "volume-id":
            return self.id
        elif filter_name == "encrypted":
            return str(self.encrypted).lower()
        elif filter_name == "availability-zone":
            return self.zone.name if self.zone else None
        else:
            return super().get_filter_value(filter_name, "DescribeVolumes")


class Snapshot(TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        snapshot_id,
        volume,
        description,
        encrypted=False,
        owner_id=OWNER_ID,
        from_ami=None,
    ):
        self.id = snapshot_id
        self.volume = volume
        self.description = description
        self.start_time = utc_date_and_time()
        self.create_volume_permission_groups = set()
        self.create_volume_permission_userids = set()
        self.ec2_backend = ec2_backend
        self.status = "completed"
        self.encrypted = encrypted
        self.owner_id = owner_id
        self.from_ami = from_ami

    def get_filter_value(self, filter_name):
        if filter_name == "description":
            return self.description
        elif filter_name == "snapshot-id":
            return self.id
        elif filter_name == "start-time":
            return self.start_time
        elif filter_name == "volume-id":
            return self.volume.id
        elif filter_name == "volume-size":
            return self.volume.size
        elif filter_name == "encrypted":
            return str(self.encrypted).lower()
        elif filter_name == "status":
            return self.status
        elif filter_name == "owner-id":
            return self.owner_id
        else:
            return super().get_filter_value(filter_name, "DescribeSnapshots")


class EBSBackend(object):
    def __init__(self):
        self.volumes = {}
        self.attachments = {}
        self.snapshots = {}
        super().__init__()

    def create_volume(
        self,
        size,
        zone_name,
        snapshot_id=None,
        encrypted=False,
        kms_key_id=None,
        volume_type=None,
    ):
        if kms_key_id and not encrypted:
            raise InvalidParameterDependency("KmsKeyId", "Encrypted")
        if encrypted and not kms_key_id:
            kms_key_id = self._get_default_encryption_key()
        volume_id = random_volume_id()
        zone = self.get_zone_by_name(zone_name)
        if snapshot_id:
            snapshot = self.get_snapshot(snapshot_id)
            if size is None:
                size = snapshot.volume.size
            if snapshot.encrypted:
                encrypted = snapshot.encrypted
        volume = Volume(
            self,
            volume_id=volume_id,
            size=size,
            zone=zone,
            snapshot_id=snapshot_id,
            encrypted=encrypted,
            kms_key_id=kms_key_id,
            volume_type=volume_type,
        )
        self.volumes[volume_id] = volume
        return volume

    def describe_volumes(self, volume_ids=None, filters=None):
        matches = self.volumes.copy().values()
        if volume_ids:
            matches = [vol for vol in matches if vol.id in volume_ids]
            if len(volume_ids) > len(matches):
                unknown_ids = set(volume_ids) - set(matches)
                raise InvalidVolumeIdError(unknown_ids)
        if filters:
            matches = generic_filter(filters, matches)
        return matches

    def get_volume(self, volume_id):
        volume = self.volumes.get(volume_id, None)
        if not volume:
            raise InvalidVolumeIdError(volume_id)
        return volume

    def delete_volume(self, volume_id):
        if volume_id in self.volumes:
            volume = self.volumes[volume_id]
            if volume.attachment:
                raise VolumeInUseError(volume_id, volume.attachment.instance.id)
            return self.volumes.pop(volume_id)
        raise InvalidVolumeIdError(volume_id)

    def attach_volume(
        self, volume_id, instance_id, device_path, delete_on_termination=False
    ):
        volume = self.get_volume(volume_id)
        instance = self.get_instance(instance_id)

        if not volume or not instance:
            return False

        volume.attachment = VolumeAttachment(volume, instance, device_path, "attached")
        # Modify instance to capture mount of block device.
        bdt = BlockDeviceType(
            volume_id=volume_id,
            status=volume.status,
            size=volume.size,
            attach_time=utc_date_and_time(),
            delete_on_termination=delete_on_termination,
        )
        instance.block_device_mapping[device_path] = bdt
        return volume.attachment

    def detach_volume(self, volume_id, instance_id, device_path):
        volume = self.get_volume(volume_id)
        instance = self.get_instance(instance_id)

        old_attachment = volume.attachment
        if not old_attachment:
            raise InvalidVolumeAttachmentError(volume_id, instance_id)
        device_path = device_path or old_attachment.device

        try:
            del instance.block_device_mapping[device_path]
        except KeyError:
            raise InvalidVolumeDetachmentError(volume_id, instance_id, device_path)

        old_attachment.status = "detached"

        volume.attachment = None
        return old_attachment

    def create_snapshot(self, volume_id, description, owner_id=None, from_ami=None):
        snapshot_id = random_snapshot_id()
        volume = self.get_volume(volume_id)
        params = [self, snapshot_id, volume, description, volume.encrypted]
        if owner_id:
            params.append(owner_id)
        if from_ami:
            params.append(from_ami)
        snapshot = Snapshot(*params)
        self.snapshots[snapshot_id] = snapshot
        return snapshot

    def describe_snapshots(self, snapshot_ids=None, filters=None):
        matches = self.snapshots.copy().values()
        if snapshot_ids:
            matches = [snap for snap in matches if snap.id in snapshot_ids]
            if len(snapshot_ids) > len(matches):
                unknown_ids = set(snapshot_ids) - set(matches)
                raise InvalidSnapshotIdError(unknown_ids)
        if filters:
            matches = generic_filter(filters, matches)
        return matches

    def copy_snapshot(self, source_snapshot_id, source_region, description=None):
        source_snapshot = ec2_backends[source_region].describe_snapshots(
            snapshot_ids=[source_snapshot_id]
        )[0]
        snapshot_id = random_snapshot_id()
        snapshot = Snapshot(
            self,
            snapshot_id,
            volume=source_snapshot.volume,
            description=description,
            encrypted=source_snapshot.encrypted,
        )
        self.snapshots[snapshot_id] = snapshot
        return snapshot

    def get_snapshot(self, snapshot_id):
        snapshot = self.snapshots.get(snapshot_id, None)
        if not snapshot:
            raise InvalidSnapshotIdError(snapshot_id)
        return snapshot

    def delete_snapshot(self, snapshot_id):
        if snapshot_id in self.snapshots:
            snapshot = self.snapshots[snapshot_id]
            if snapshot.from_ami and snapshot.from_ami in self.amis:
                raise InvalidSnapshotInUse(snapshot_id, snapshot.from_ami)
            return self.snapshots.pop(snapshot_id)
        raise InvalidSnapshotIdError(snapshot_id)

    def get_create_volume_permission_groups(self, snapshot_id):
        snapshot = self.get_snapshot(snapshot_id)
        return snapshot.create_volume_permission_groups

    def get_create_volume_permission_userids(self, snapshot_id):
        snapshot = self.get_snapshot(snapshot_id)
        return snapshot.create_volume_permission_userids

    def add_create_volume_permission(self, snapshot_id, user_ids=None, groups=None):
        snapshot = self.get_snapshot(snapshot_id)
        if user_ids:
            snapshot.create_volume_permission_userids.update(user_ids)

        if groups and groups != ["all"]:
            raise InvalidAMIAttributeItemValueError("UserGroup", groups)
        else:
            snapshot.create_volume_permission_groups.update(groups)

        return True

    def remove_create_volume_permission(self, snapshot_id, user_ids=None, groups=None):
        snapshot = self.get_snapshot(snapshot_id)
        if user_ids:
            snapshot.create_volume_permission_userids.difference_update(user_ids)

        if groups and groups != ["all"]:
            raise InvalidAMIAttributeItemValueError("UserGroup", groups)
        else:
            snapshot.create_volume_permission_groups.difference_update(groups)

        return True

    def _get_default_encryption_key(self):
        # https://aws.amazon.com/kms/features/#AWS_Service_Integration
        # An AWS managed CMK is created automatically when you first create
        # an encrypted resource using an AWS service integrated with KMS.
        kms = kms_backends[self.region_name]
        ebs_alias = "alias/aws/ebs"
        if not kms.alias_exists(ebs_alias):
            key = kms.create_key(
                policy="",
                key_usage="ENCRYPT_DECRYPT",
                customer_master_key_spec="SYMMETRIC_DEFAULT",
                description="Default master key that protects my EBS volumes when no other key is defined",
                tags=None,
                region=self.region_name,
            )
            kms.add_alias(key.id, ebs_alias)
        ebs_key = kms.describe_key(ebs_alias)
        return ebs_key.arn


class VPC(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        vpc_id,
        cidr_block,
        is_default,
        instance_tenancy="default",
        amazon_provided_ipv6_cidr_block=False,
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
            )

    @property
    def owner_id(self):
        return ACCOUNT_ID

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-vpc.html
        return "AWS::EC2::VPC"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[region_name]
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
        self, cidr_block, amazon_provided_ipv6_cidr_block=False
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


class VPCBackend(object):
    vpc_refs = defaultdict(set)

    def __init__(self):
        self.vpcs = {}
        self.vpc_end_points = {}
        self.vpc_refs[self.__class__].add(weakref.ref(self))
        super().__init__()

    def create_vpc(
        self,
        cidr_block,
        instance_tenancy="default",
        amazon_provided_ipv6_cidr_block=False,
        tags=None,
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
            len(self.vpcs) == 0,
            instance_tenancy,
            amazon_provided_ipv6_cidr_block,
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
        else:
            raise InvalidVpcCidrBlockAssociationIdError(association_id)

    def associate_vpc_cidr_block(
        self, vpc_id, cidr_block, amazon_provided_ipv6_cidr_block
    ):
        vpc = self.get_vpc(vpc_id)
        association_set = vpc.associate_vpc_cidr_block(
            cidr_block, amazon_provided_ipv6_cidr_block
        )
        for route_table in self.route_tables.values():
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
                if vpc_endpoint.type.lower() == "interface":
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
    def _collect_default_endpoint_services(region):
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

        for _backends in backends.unique_backends():
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
        default_services = self._collect_default_endpoint_services(region)
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


class PeeringConnectionStatus(object):
    def __init__(self, code="initiating-request", message=""):
        self.code = code
        self.message = message

    def deleted(self):
        self.code = "deleted"
        self.message = "Deleted by {deleter ID}"

    def initiating(self):
        self.code = "initiating-request"
        self.message = "Initiating Request to {accepter ID}"

    def pending(self):
        self.code = "pending-acceptance"
        self.message = "Pending Acceptance by {accepter ID}"

    def accept(self):
        self.code = "active"
        self.message = "Active"

    def reject(self):
        self.code = "rejected"
        self.message = "Inactive"


class VPCPeeringConnection(TaggedEC2Resource, CloudFormationModel):
    DEFAULT_OPTIONS = {
        "AllowEgressFromLocalClassicLinkToRemoteVpc": "false",
        "AllowEgressFromLocalVpcToRemoteClassicLink": "false",
        "AllowDnsResolutionFromRemoteVpc": "false",
    }

    def __init__(self, backend, vpc_pcx_id, vpc, peer_vpc, tags=None):
        self.id = vpc_pcx_id
        self.ec2_backend = backend
        self.vpc = vpc
        self.peer_vpc = peer_vpc
        self.requester_options = self.DEFAULT_OPTIONS.copy()
        self.accepter_options = self.DEFAULT_OPTIONS.copy()
        self.add_tags(tags or {})
        self._status = PeeringConnectionStatus()

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-vpcpeeringconnection.html
        return "AWS::EC2::VPCPeeringConnection"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[region_name]
        vpc = ec2_backend.get_vpc(properties["VpcId"])
        peer_vpc = ec2_backend.get_vpc(properties["PeerVpcId"])

        vpc_pcx = ec2_backend.create_vpc_peering_connection(vpc, peer_vpc)

        return vpc_pcx

    @property
    def physical_resource_id(self):
        return self.id


class VPCPeeringConnectionBackend(object):
    # for cross region vpc reference
    vpc_pcx_refs = defaultdict(set)

    def __init__(self):
        self.vpc_pcxs = {}
        self.vpc_pcx_refs[self.__class__].add(weakref.ref(self))
        super().__init__()

    @classmethod
    def get_vpc_pcx_refs(cls):
        for inst_ref in cls.vpc_pcx_refs[cls]:
            inst = inst_ref()
            if inst is not None:
                yield inst

    def create_vpc_peering_connection(self, vpc, peer_vpc, tags=None):
        vpc_pcx_id = random_vpc_peering_connection_id()
        vpc_pcx = VPCPeeringConnection(self, vpc_pcx_id, vpc, peer_vpc, tags)
        vpc_pcx._status.pending()
        self.vpc_pcxs[vpc_pcx_id] = vpc_pcx
        # insert cross region peering info
        if vpc.ec2_backend.region_name != peer_vpc.ec2_backend.region_name:
            for vpc_pcx_cx in peer_vpc.ec2_backend.get_vpc_pcx_refs():
                if vpc_pcx_cx.region_name == peer_vpc.ec2_backend.region_name:
                    vpc_pcx_cx.vpc_pcxs[vpc_pcx_id] = vpc_pcx
        return vpc_pcx

    def describe_vpc_peering_connections(self, vpc_peering_ids=None):
        all_pcxs = self.vpc_pcxs.copy().values()
        if vpc_peering_ids:
            return [pcx for pcx in all_pcxs if pcx.id in vpc_peering_ids]
        return all_pcxs

    def get_vpc_peering_connection(self, vpc_pcx_id):
        if vpc_pcx_id not in self.vpc_pcxs:
            raise InvalidVPCPeeringConnectionIdError(vpc_pcx_id)
        return self.vpc_pcxs.get(vpc_pcx_id)

    def delete_vpc_peering_connection(self, vpc_pcx_id):
        deleted = self.get_vpc_peering_connection(vpc_pcx_id)
        deleted._status.deleted()
        return deleted

    def accept_vpc_peering_connection(self, vpc_pcx_id):
        vpc_pcx = self.get_vpc_peering_connection(vpc_pcx_id)
        # if cross region need accepter from another region
        pcx_req_region = vpc_pcx.vpc.ec2_backend.region_name
        pcx_acp_region = vpc_pcx.peer_vpc.ec2_backend.region_name
        if pcx_req_region != pcx_acp_region and self.region_name == pcx_req_region:
            raise OperationNotPermitted2(self.region_name, vpc_pcx.id, pcx_acp_region)
        if vpc_pcx._status.code != "pending-acceptance":
            raise InvalidVPCPeeringConnectionStateTransitionError(vpc_pcx.id)
        vpc_pcx._status.accept()
        return vpc_pcx

    def reject_vpc_peering_connection(self, vpc_pcx_id):
        vpc_pcx = self.get_vpc_peering_connection(vpc_pcx_id)
        # if cross region need accepter from another region
        pcx_req_region = vpc_pcx.vpc.ec2_backend.region_name
        pcx_acp_region = vpc_pcx.peer_vpc.ec2_backend.region_name
        if pcx_req_region != pcx_acp_region and self.region_name == pcx_req_region:
            raise OperationNotPermitted3(self.region_name, vpc_pcx.id, pcx_acp_region)
        if vpc_pcx._status.code != "pending-acceptance":
            raise InvalidVPCPeeringConnectionStateTransitionError(vpc_pcx.id)
        vpc_pcx._status.reject()
        return vpc_pcx

    def modify_vpc_peering_connection_options(
        self, vpc_pcx_id, accepter_options=None, requester_options=None
    ):
        vpc_pcx = self.get_vpc_peering_connection(vpc_pcx_id)
        if not vpc_pcx:
            raise InvalidVPCPeeringConnectionIdError(vpc_pcx_id)
        # TODO: check if actual vpc has this options enabled
        if accepter_options:
            vpc_pcx.accepter_options.update(accepter_options)
        if requester_options:
            vpc_pcx.requester_options.update(requester_options)


class Subnet(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        subnet_id,
        vpc_id,
        cidr_block,
        ipv6_cidr_block,
        availability_zone,
        default_for_az,
        map_public_ip_on_launch,
        assign_ipv6_address_on_creation=False,
    ):
        self.ec2_backend = ec2_backend
        self.id = subnet_id
        self.vpc_id = vpc_id
        self.cidr_block = cidr_block
        self.cidr = ipaddress.IPv4Network(str(self.cidr_block), strict=False)
        self._available_ip_addresses = self.cidr.num_addresses - 5
        self._availability_zone = availability_zone
        self.default_for_az = default_for_az
        self.map_public_ip_on_launch = map_public_ip_on_launch
        self.assign_ipv6_address_on_creation = assign_ipv6_address_on_creation
        self.ipv6_cidr_block_associations = {}
        if ipv6_cidr_block:
            self.attach_ipv6_cidr_block_associations(ipv6_cidr_block)

        # Theory is we assign ip's as we go (as 16,777,214 usable IPs in a /8)
        self._subnet_ip_generator = self.cidr.hosts()
        self.reserved_ips = [
            next(self._subnet_ip_generator) for _ in range(0, 3)
        ]  # Reserved by AWS
        self._unused_ips = set()  # if instance is destroyed hold IP here for reuse
        self._subnet_ips = {}  # has IP: instance
        self.state = "available"

    @property
    def owner_id(self):
        return ACCOUNT_ID

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-subnet.html
        return "AWS::EC2::Subnet"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        vpc_id = properties["VpcId"]
        cidr_block = properties["CidrBlock"]
        availability_zone = properties.get("AvailabilityZone")
        ec2_backend = ec2_backends[region_name]
        subnet = ec2_backend.create_subnet(
            vpc_id=vpc_id, cidr_block=cidr_block, availability_zone=availability_zone
        )
        for tag in properties.get("Tags", []):
            tag_key = tag["Key"]
            tag_value = tag["Value"]
            subnet.add_tag(tag_key, tag_value)

        return subnet

    @property
    def available_ip_addresses(self):
        enis = [
            eni
            for eni in self.ec2_backend.get_all_network_interfaces()
            if eni.subnet.id == self.id
        ]
        addresses_taken = []
        for eni in enis:
            if eni.private_ip_addresses:
                addresses_taken.extend(eni.private_ip_addresses)
        return str(self._available_ip_addresses - len(addresses_taken))

    @property
    def availability_zone(self):
        return self._availability_zone.name

    @property
    def availability_zone_id(self):
        return self._availability_zone.zone_id

    @property
    def physical_resource_id(self):
        return self.id

    def get_filter_value(self, filter_name):
        """
        API Version 2014-10-01 defines the following filters for DescribeSubnets:

        * availabilityZone
        * available-ip-address-count
        * cidrBlock
        * defaultForAz
        * state
        * subnet-id
        * tag:key=value
        * tag-key
        * tag-value
        * vpc-id

        Taken from: http://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeSubnets.html
        """
        if filter_name in ("cidr", "cidrBlock", "cidr-block"):
            return self.cidr_block
        elif filter_name in ("vpc-id", "vpcId"):
            return self.vpc_id
        elif filter_name == "subnet-id":
            return self.id
        elif filter_name in ("availabilityZone", "availability-zone"):
            return self.availability_zone
        elif filter_name in ("defaultForAz", "default-for-az"):
            return self.default_for_az
        elif filter_name == "state":
            return self.state
        else:
            return super().get_filter_value(filter_name, "DescribeSubnets")

    @classmethod
    def has_cfn_attr(cls, attribute):
        return attribute in ["AvailabilityZone"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "AvailabilityZone":
            raise NotImplementedError('"Fn::GetAtt" : [ "{0}" , "AvailabilityZone" ]"')
        raise UnformattedGetAttTemplateException()

    def get_available_subnet_ip(self, instance):
        try:
            new_ip = self._unused_ips.pop()
        except KeyError:
            new_ip = next(self._subnet_ip_generator)

            # Skips any IP's if they've been manually specified
            while str(new_ip) in self._subnet_ips:
                new_ip = next(self._subnet_ip_generator)

            if new_ip == self.cidr.broadcast_address:
                raise StopIteration()  # Broadcast address cant be used obviously
        # TODO StopIteration will be raised if no ip's available, not sure how aws handles this.

        new_ip = str(new_ip)
        self._subnet_ips[new_ip] = instance

        return new_ip

    def request_ip(self, ip, instance):
        if ipaddress.ip_address(ip) not in self.cidr:
            raise Exception(
                "IP does not fall in the subnet CIDR of {0}".format(self.cidr)
            )

        if ip in self._subnet_ips:
            raise Exception("IP already in use")
        try:
            self._unused_ips.remove(ip)
        except KeyError:
            pass

        self._subnet_ips[ip] = instance
        return ip

    def del_subnet_ip(self, ip):
        try:
            del self._subnet_ips[ip]
            self._unused_ips.add(ip)
        except KeyError:
            pass  # Unknown IP

    def attach_ipv6_cidr_block_associations(self, ipv6_cidr_block):
        association = {
            "associationId": random_subnet_ipv6_cidr_block_association_id(),
            "ipv6CidrBlock": ipv6_cidr_block,
            "ipv6CidrBlockState": "associated",
        }
        self.ipv6_cidr_block_associations[
            association.get("associationId")
        ] = association
        return association

    def detach_subnet_cidr_block(self, association_id):
        association = self.ipv6_cidr_block_associations.get(association_id)
        association["ipv6CidrBlockState"] = "disassociated"
        return association


class SubnetBackend(object):
    def __init__(self):
        # maps availability zone to dict of (subnet_id, subnet)
        self.subnets = defaultdict(dict)
        super().__init__()

    def get_subnet(self, subnet_id):
        for subnets in self.subnets.values():
            if subnet_id in subnets:
                return subnets[subnet_id]
        raise InvalidSubnetIdError(subnet_id)

    def create_subnet(
        self,
        vpc_id,
        cidr_block,
        ipv6_cidr_block=None,
        availability_zone=None,
        availability_zone_id=None,
        context=None,
        tags=None,
    ):
        subnet_id = random_subnet_id()
        vpc = self.get_vpc(
            vpc_id
        )  # Validate VPC exists and the supplied CIDR block is a subnet of the VPC's
        vpc_cidr_blocks = [
            ipaddress.IPv4Network(
                str(cidr_block_association["cidr_block"]), strict=False
            )
            for cidr_block_association in vpc.get_cidr_block_association_set()
        ]
        try:
            subnet_cidr_block = ipaddress.IPv4Network(str(cidr_block), strict=False)
        except ValueError:
            raise InvalidCIDRBlockParameterError(cidr_block)

        subnet_in_vpc_cidr_range = False
        for vpc_cidr_block in vpc_cidr_blocks:
            if (
                vpc_cidr_block.network_address <= subnet_cidr_block.network_address
                and vpc_cidr_block.broadcast_address
                >= subnet_cidr_block.broadcast_address
            ):
                subnet_in_vpc_cidr_range = True
                break

        if not subnet_in_vpc_cidr_range:
            raise InvalidSubnetRangeError(cidr_block)

        # The subnet size must use a /64 prefix length.
        if ipv6_cidr_block and "::/64" not in ipv6_cidr_block:
            raise GenericInvalidParameterValueError("ipv6-cidr-block", ipv6_cidr_block)

        for subnet in self.get_all_subnets(filters={"vpc-id": vpc_id}):
            if subnet.cidr.overlaps(subnet_cidr_block):
                raise InvalidSubnetConflictError(cidr_block)

        # if this is the first subnet for an availability zone,
        # consider it the default
        default_for_az = str(availability_zone not in self.subnets).lower()
        map_public_ip_on_launch = default_for_az

        if availability_zone is None and not availability_zone_id:
            availability_zone = "us-east-1a"
        try:
            if availability_zone:
                availability_zone_data = next(
                    zone
                    for zones in RegionsAndZonesBackend.zones.values()
                    for zone in zones
                    if zone.name == availability_zone
                )
            elif availability_zone_id:
                availability_zone_data = next(
                    zone
                    for zones in RegionsAndZonesBackend.zones.values()
                    for zone in zones
                    if zone.zone_id == availability_zone_id
                )

        except StopIteration:
            raise InvalidAvailabilityZoneError(
                availability_zone,
                ", ".join(
                    [
                        zone.name
                        for zones in RegionsAndZonesBackend.zones.values()
                        for zone in zones
                    ]
                ),
            )
        subnet = Subnet(
            self,
            subnet_id,
            vpc_id,
            cidr_block,
            ipv6_cidr_block,
            availability_zone_data,
            default_for_az,
            map_public_ip_on_launch,
            assign_ipv6_address_on_creation=False,
        )

        for tag in tags or []:
            tag_key = tag.get("Key")
            tag_value = tag.get("Value")
            subnet.add_tag(tag_key, tag_value)

        # AWS associates a new subnet with the default Network ACL
        self.associate_default_network_acl_with_subnet(subnet_id, vpc_id)
        self.subnets[availability_zone][subnet_id] = subnet
        return subnet

    def get_all_subnets(self, subnet_ids=None, filters=None):
        # Extract a list of all subnets
        matches = itertools.chain(
            *[x.copy().values() for x in self.subnets.copy().values()]
        )
        if subnet_ids:
            matches = [sn for sn in matches if sn.id in subnet_ids]
            if len(subnet_ids) > len(matches):
                unknown_ids = set(subnet_ids) - set(matches)
                raise InvalidSubnetIdError(list(unknown_ids)[0])
        if filters:
            matches = generic_filter(filters, matches)

        return matches

    def delete_subnet(self, subnet_id):
        for subnets in self.subnets.values():
            if subnet_id in subnets:
                return subnets.pop(subnet_id, None)
        raise InvalidSubnetIdError(subnet_id)

    def modify_subnet_attribute(self, subnet_id, attr_name, attr_value):
        subnet = self.get_subnet(subnet_id)
        if attr_name in ("map_public_ip_on_launch", "assign_ipv6_address_on_creation"):
            setattr(subnet, attr_name, attr_value)
        else:
            raise InvalidParameterValueError(attr_name)

    def get_subnet_from_ipv6_association(self, association_id):
        subnet = None
        for s in self.get_all_subnets():
            if association_id in s.ipv6_cidr_block_associations:
                subnet = s
        return subnet

    def associate_subnet_cidr_block(self, subnet_id, ipv6_cidr_block):
        subnet = self.get_subnet(subnet_id)
        if not subnet:
            raise InvalidSubnetIdError(subnet_id)
        association = subnet.attach_ipv6_cidr_block_associations(ipv6_cidr_block)
        return association

    def disassociate_subnet_cidr_block(self, association_id):
        subnet = self.get_subnet_from_ipv6_association(association_id)
        if not subnet:
            raise InvalidSubnetCidrBlockAssociationID(association_id)
        association = subnet.detach_subnet_cidr_block(association_id)
        return subnet.id, association


class FlowLogs(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        flow_log_id,
        resource_id,
        traffic_type,
        log_destination,
        log_group_name,
        deliver_logs_permission_arn,
        max_aggregation_interval,
        log_destination_type,
        log_format,
        deliver_logs_status="SUCCESS",
        deliver_logs_error_message=None,
    ):
        self.ec2_backend = ec2_backend
        self.id = flow_log_id
        self.resource_id = resource_id
        self.traffic_type = traffic_type
        self.log_destination = log_destination
        self.log_group_name = log_group_name
        self.deliver_logs_permission_arn = deliver_logs_permission_arn
        self.deliver_logs_status = deliver_logs_status
        self.deliver_logs_error_message = deliver_logs_error_message
        self.max_aggregation_interval = max_aggregation_interval
        self.log_destination_type = log_destination_type
        self.log_format = log_format

        self.created_at = utc_date_and_time()

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-flowlog.html
        return "AWS::EC2::FlowLog"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        resource_type = properties.get("ResourceType")
        resource_id = [properties.get("ResourceId")]
        traffic_type = properties.get("TrafficType")
        deliver_logs_permission_arn = properties.get("DeliverLogsPermissionArn")
        log_destination_type = properties.get("LogDestinationType")
        log_destination = properties.get("LogDestination")
        log_group_name = properties.get("LogGroupName")
        log_format = properties.get("LogFormat")
        max_aggregation_interval = properties.get("MaxAggregationInterval")

        ec2_backend = ec2_backends[region_name]
        flow_log, _ = ec2_backend.create_flow_logs(
            resource_type,
            resource_id,
            traffic_type,
            deliver_logs_permission_arn,
            log_destination_type,
            log_destination,
            log_group_name,
            log_format,
            max_aggregation_interval,
        )
        for tag in properties.get("Tags", []):
            tag_key = tag["Key"]
            tag_value = tag["Value"]
            flow_log[0].add_tag(tag_key, tag_value)

        return flow_log[0]

    @property
    def physical_resource_id(self):
        return self.id

    def get_filter_value(self, filter_name):
        """
        API Version 2016-11-15 defines the following filters for DescribeFlowLogs:

        * deliver-log-status
        * log-destination-type
        * flow-log-id
        * log-group-name
        * resource-id
        * traffic-type
        * tag:key=value
        * tag-key

        Taken from: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeFlowLogs.html
        """
        if filter_name == "resource-id":
            return self.resource_id
        elif filter_name == "traffic-type":
            return self.traffic_type
        elif filter_name == "log-destination-type":
            return self.log_destination_type
        elif filter_name == "flow-log-id":
            return self.id
        elif filter_name == "log-group-name":
            return self.log_group_name
        elif filter_name == "deliver-log-status":
            return "SUCCESS"
        else:
            return super().get_filter_value(filter_name, "DescribeFlowLogs")


class FlowLogsBackend(object):
    def __init__(self):
        self.flow_logs = defaultdict(dict)
        super().__init__()

    def _validate_request(
        self,
        log_group_name,
        log_destination,
        log_destination_type,
        max_aggregation_interval,
        deliver_logs_permission_arn,
    ):
        if log_group_name is None and log_destination is None:
            raise InvalidDependantParameterError(
                "LogDestination", "LogGroupName", "not provided",
            )

        if log_destination_type == "s3":
            if log_group_name is not None:
                raise InvalidDependantParameterTypeError(
                    "LogDestination", "cloud-watch-logs", "LogGroupName",
                )
        elif log_destination_type == "cloud-watch-logs":
            if deliver_logs_permission_arn is None:
                raise InvalidDependantParameterError(
                    "DeliverLogsPermissionArn",
                    "LogDestinationType",
                    "cloud-watch-logs",
                )

        if max_aggregation_interval not in ["60", "600"]:
            raise InvalidAggregationIntervalParameterError(
                "Flow Log Max Aggregation Interval"
            )

    def create_flow_logs(
        self,
        resource_type,
        resource_ids,
        traffic_type,
        deliver_logs_permission_arn,
        log_destination_type,
        log_destination,
        log_group_name,
        log_format,
        max_aggregation_interval,
    ):
        # Guess it's best to put it here due to possible
        # lack of them in the CloudFormation template
        max_aggregation_interval = (
            "600" if max_aggregation_interval is None else max_aggregation_interval
        )
        log_destination_type = (
            "cloud-watch-logs" if log_destination_type is None else log_destination_type
        )
        log_format = (
            "${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}"
            if log_format is None
            else log_format
        )

        # Validate the requests paremeters
        self._validate_request(
            log_group_name,
            log_destination,
            log_destination_type,
            max_aggregation_interval,
            deliver_logs_permission_arn,
        )

        flow_logs_set = []
        unsuccessful = []

        for resource_id in resource_ids:
            deliver_logs_status = "SUCCESS"
            deliver_logs_error_message = None
            flow_log_id = random_flow_log_id()
            if resource_type == "VPC":
                # Validate VPCs exist
                self.get_vpc(resource_id)
            elif resource_type == "Subnet":
                # Validate Subnets exist
                self.get_subnet(resource_id)
            elif resource_type == "NetworkInterface":
                # Validate NetworkInterfaces exist
                self.get_network_interface(resource_id)

            if log_destination_type == "s3":
                from moto.s3.models import s3_backend
                from moto.s3.exceptions import MissingBucket

                arn = log_destination.split(":", 5)[5]
                try:
                    s3_backend.get_bucket(arn)
                except MissingBucket:
                    # Instead of creating FlowLog report
                    # the unsuccessful status for the
                    # given resource_id
                    unsuccessful.append(
                        (
                            resource_id,
                            "400",
                            "LogDestination: {0} does not exist.".format(arn),
                        )
                    )
                    continue
            elif log_destination_type == "cloud-watch-logs":
                from moto.logs.models import logs_backends
                from moto.logs.exceptions import ResourceNotFoundException

                # API allows to create a FlowLog with a
                # non-existing LogGroup. It however later
                # on reports the FAILED delivery status.
                try:
                    # Need something easy to check the group exists.
                    # The list_tags_log_group seems to do the trick.
                    logs_backends[self.region_name].list_tags_log_group(log_group_name)
                except ResourceNotFoundException:
                    deliver_logs_status = "FAILED"
                    deliver_logs_error_message = "Access error"

            all_flow_logs = self.describe_flow_logs()
            if any(
                fl.resource_id == resource_id
                and (
                    fl.log_group_name == log_group_name
                    or fl.log_destination == log_destination
                )
                for fl in all_flow_logs
            ):
                raise FlowLogAlreadyExists()
            flow_logs = FlowLogs(
                self,
                flow_log_id,
                resource_id,
                traffic_type,
                log_destination,
                log_group_name,
                deliver_logs_permission_arn,
                max_aggregation_interval,
                log_destination_type,
                log_format,
                deliver_logs_status,
                deliver_logs_error_message,
            )
            self.flow_logs[flow_log_id] = flow_logs
            flow_logs_set.append(flow_logs)

        return flow_logs_set, unsuccessful

    def describe_flow_logs(self, flow_log_ids=None, filters=None):
        matches = itertools.chain([i for i in self.flow_logs.values()])
        if flow_log_ids:
            matches = [flow_log for flow_log in matches if flow_log.id in flow_log_ids]
        if filters:
            matches = generic_filter(filters, matches)
        return matches

    def delete_flow_logs(self, flow_log_ids):
        non_existing = []
        for flow_log in flow_log_ids:
            if flow_log in self.flow_logs:
                self.flow_logs.pop(flow_log, None)
            else:
                non_existing.append(flow_log)

        if non_existing:
            raise InvalidFlowLogIdError(
                len(flow_log_ids), " ".join(x for x in flow_log_ids),
            )
        return True


class SubnetRouteTableAssociation(CloudFormationModel):
    def __init__(self, route_table_id, subnet_id):
        self.route_table_id = route_table_id
        self.subnet_id = subnet_id

    @property
    def physical_resource_id(self):
        return self.route_table_id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-subnetroutetableassociation.html
        return "AWS::EC2::SubnetRouteTableAssociation"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        route_table_id = properties["RouteTableId"]
        subnet_id = properties["SubnetId"]

        ec2_backend = ec2_backends[region_name]
        subnet_association = ec2_backend.create_subnet_association(
            route_table_id=route_table_id, subnet_id=subnet_id
        )
        return subnet_association


class SubnetRouteTableAssociationBackend(object):
    def __init__(self):
        self.subnet_associations = {}
        super().__init__()

    def create_subnet_association(self, route_table_id, subnet_id):
        subnet_association = SubnetRouteTableAssociation(route_table_id, subnet_id)
        self.subnet_associations[
            "{0}:{1}".format(route_table_id, subnet_id)
        ] = subnet_association
        return subnet_association


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
        return ACCOUNT_ID

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-routetable.html
        return "AWS::EC2::RouteTable"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        vpc_id = properties["VpcId"]
        ec2_backend = ec2_backends[region_name]
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
        else:
            return super().get_filter_value(filter_name, "DescribeRouteTables")


class RouteTableBackend(object):
    def __init__(self):
        self.route_tables = {}
        super().__init__()

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
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        gateway_id = properties.get("GatewayId")
        instance_id = properties.get("InstanceId")
        interface_id = properties.get("NetworkInterfaceId")
        nat_gateway_id = properties.get("NatGatewayId")
        egress_only_igw_id = properties.get("EgressOnlyInternetGatewayId")
        transit_gateway_id = properties.get("TransitGatewayId")
        pcx_id = properties.get("VpcPeeringConnectionId")

        route_table_id = properties["RouteTableId"]
        ec2_backend = ec2_backends[region_name]
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


class VPCEndPoint(TaggedEC2Resource):
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
        self.type = endpoint_type
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

    @property
    def owner_id(self):
        return ACCOUNT_ID

    @property
    def created_at(self):
        return utc_date_and_time()


class ManagedPrefixList(TaggedEC2Resource):
    def __init__(
        self,
        backend,
        address_family=None,
        entry=None,
        max_entries=None,
        prefix_list_name=None,
        region=None,
        tags=None,
        owner_id=None,
    ):
        self.ec2_backend = backend
        self.address_family = address_family
        self.max_entries = max_entries
        self.id = random_managed_prefix_list_id()
        self.prefix_list_name = prefix_list_name
        self.state = "create-complete"
        self.state_message = "create complete"
        self.add_tags(tags or {})
        self.version = 1
        self.entries = {self.version: entry} if entry else {}
        self.resource_owner_id = owner_id if owner_id else None
        self.prefix_list_arn = self.arn(region, self.owner_id)
        self.delete_counter = 1

    def arn(self, region, owner_id):
        return "arn:aws:ec2:{region}:{owner_id}:prefix-list/{resource_id}".format(
            region=region, resource_id=self.id, owner_id=owner_id
        )

    @property
    def owner_id(self):
        return ACCOUNT_ID if not self.resource_owner_id else self.resource_owner_id


class ManagedPrefixListBackend(object):
    def __init__(self):
        self.managed_prefix_lists = {}
        self.create_default_pls()
        super().__init__()

    def create_managed_prefix_list(
        self,
        address_family=None,
        entry=None,
        max_entries=None,
        prefix_list_name=None,
        tags=None,
        owner_id=None,
    ):
        managed_prefix_list = ManagedPrefixList(
            self,
            address_family=address_family,
            entry=entry,
            max_entries=max_entries,
            prefix_list_name=prefix_list_name,
            region=self.region_name,
            tags=tags,
            owner_id=owner_id,
        )
        self.managed_prefix_lists[managed_prefix_list.id] = managed_prefix_list
        return managed_prefix_list

    def describe_managed_prefix_lists(self, prefix_list_ids=None, filters=None):
        managed_prefix_lists = list(self.managed_prefix_lists.copy().values())
        attr_pairs = (
            ("owner-id", "owner_id"),
            ("prefix-list-id", "id"),
            ("prefix-list-name", "prefix_list_name"),
        )

        if prefix_list_ids:
            managed_prefix_lists = [
                managed_prefix_list
                for managed_prefix_list in managed_prefix_lists
                if managed_prefix_list.id in prefix_list_ids
            ]

        result = managed_prefix_lists
        if filters:
            result = filter_resources(managed_prefix_lists, filters, attr_pairs)
            result = describe_tag_filter(filters, managed_prefix_lists)

        for item in result.copy():
            if not item.delete_counter:
                self.managed_prefix_lists.pop(item.id, None)
                result.remove(item)
            if item.state == "delete-complete":
                item.delete_counter -= 1
        return result

    def get_managed_prefix_list_entries(self, prefix_list_id=None):
        managed_prefix_list = self.managed_prefix_lists.get(prefix_list_id)
        return managed_prefix_list

    def delete_managed_prefix_list(self, prefix_list_id):
        managed_prefix_list = self.managed_prefix_lists.get(prefix_list_id)
        managed_prefix_list.state = "delete-complete"
        return managed_prefix_list

    def modify_managed_prefix_list(
        self,
        add_entry=None,
        prefix_list_id=None,
        current_version=None,
        prefix_list_name=None,
        remove_entry=None,
    ):
        managed_pl = self.managed_prefix_lists.get(prefix_list_id)
        managed_pl.prefix_list_name = prefix_list_name
        if remove_entry or add_entry:
            latest_version = managed_pl.entries.get(managed_pl.version)
            entries = (
                managed_pl.entries.get(current_version, latest_version).copy()
                if managed_pl.entries
                else []
            )
            for item in entries.copy():
                if item.get("Cidr", "") in remove_entry:
                    entries.remove(item)

            for item in add_entry:
                if item not in entries.copy():
                    entries.append(item)
            managed_pl.version += 1
            managed_pl.entries[managed_pl.version] = entries
        managed_pl.state = "modify-complete"
        return managed_pl

    def create_default_pls(self):
        entry = [
            {"Cidr": "52.216.0.0/15", "Description": "default"},
            {"Cidr": "3.5.0.0/19", "Description": "default"},
            {"Cidr": "54.231.0.0/16", "Description": "default"},
        ]

        managed_prefix_list = self.create_managed_prefix_list(
            address_family="IPv4",
            entry=entry,
            prefix_list_name="com.amazonaws.{}.s3".format(self.region_name),
            owner_id="aws",
        )
        managed_prefix_list.version = None
        managed_prefix_list.max_entries = None
        self.managed_prefix_lists[managed_prefix_list.id] = managed_prefix_list

        entry = [
            {"Cidr": "3.218.182.0/24", "Description": "default"},
            {"Cidr": "3.218.180.0/23", "Description": "default"},
            {"Cidr": "52.94.0.0/22", "Description": "default"},
            {"Cidr": "52.119.224.0/20", "Description": "default"},
        ]

        managed_prefix_list = self.create_managed_prefix_list(
            address_family="IPv4",
            entry=entry,
            prefix_list_name="com.amazonaws.{}.dynamodb".format(self.region_name),
            owner_id="aws",
        )
        managed_prefix_list.version = None
        managed_prefix_list.max_entries = None
        self.managed_prefix_lists[managed_prefix_list.id] = managed_prefix_list


class RouteBackend(object):
    def __init__(self):
        super().__init__()

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

            try:
                if destination_cidr_block:
                    ipaddress.IPv4Network(str(destination_cidr_block), strict=False)
            except ValueError:
                raise InvalidDestinationCIDRBlockParameterError(destination_cidr_block)

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


class InternetGateway(TaggedEC2Resource, CloudFormationModel):
    def __init__(self, ec2_backend):
        self.ec2_backend = ec2_backend
        self.id = random_internet_gateway_id()
        self.vpc = None

    @property
    def owner_id(self):
        return ACCOUNT_ID

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-internetgateway.html
        return "AWS::EC2::InternetGateway"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        ec2_backend = ec2_backends[region_name]
        return ec2_backend.create_internet_gateway()

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def attachment_state(self):
        if self.vpc:
            return "available"
        else:
            return "detached"


class InternetGatewayBackend(object):
    def __init__(self):
        self.internet_gateways = {}
        super().__init__()

    def create_internet_gateway(self, tags=None):
        igw = InternetGateway(self)
        for tag in tags or []:
            igw.add_tag(tag.get("Key"), tag.get("Value"))
        self.internet_gateways[igw.id] = igw
        return igw

    def describe_internet_gateways(self, internet_gateway_ids=None, filters=None):
        igws = []
        if internet_gateway_ids is None:
            igws = self.internet_gateways.values()
        else:
            for igw_id in internet_gateway_ids:
                if igw_id in self.internet_gateways:
                    igws.append(self.internet_gateways[igw_id])
                else:
                    raise InvalidInternetGatewayIdError(igw_id)
        if filters is not None:
            igws = filter_internet_gateways(igws, filters)
        return igws

    def delete_internet_gateway(self, internet_gateway_id):
        igw = self.get_internet_gateway(internet_gateway_id)
        if igw.vpc:
            raise DependencyViolationError(
                "{0} is being utilized by {1}".format(internet_gateway_id, igw.vpc.id)
            )
        self.internet_gateways.pop(internet_gateway_id)
        return True

    def detach_internet_gateway(self, internet_gateway_id, vpc_id):
        igw = self.get_internet_gateway(internet_gateway_id)
        if not igw.vpc or igw.vpc.id != vpc_id:
            raise GatewayNotAttachedError(internet_gateway_id, vpc_id)
        igw.vpc = None
        return True

    def attach_internet_gateway(self, internet_gateway_id, vpc_id):
        igw = self.get_internet_gateway(internet_gateway_id)
        if igw.vpc:
            raise ResourceAlreadyAssociatedError(internet_gateway_id)
        vpc = self.get_vpc(vpc_id)
        igw.vpc = vpc
        return VPCGatewayAttachment(gateway_id=internet_gateway_id, vpc_id=vpc_id)

    def get_internet_gateway(self, internet_gateway_id):
        igw_ids = [internet_gateway_id]
        return self.describe_internet_gateways(internet_gateway_ids=igw_ids)[0]


class CarrierGateway(TaggedEC2Resource):
    def __init__(self, ec2_backend, vpc_id, tags=None):
        self.id = random_carrier_gateway_id()
        self.ec2_backend = ec2_backend
        self.vpc_id = vpc_id
        self.state = "available"
        self.add_tags(tags or {})

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def owner_id(self):
        return ACCOUNT_ID


class CarrierGatewayBackend(object):
    def __init__(self):
        self.carrier_gateways = {}
        super().__init__()

    def create_carrier_gateway(self, vpc_id, tags=None):
        vpc = self.get_vpc(vpc_id)
        if not vpc:
            raise InvalidVPCIdError(vpc_id)
        carrier_gateway = CarrierGateway(self, vpc_id, tags)
        self.carrier_gateways[carrier_gateway.id] = carrier_gateway
        return carrier_gateway

    def delete_carrier_gateway(self, gateway_id):
        if not self.carrier_gateways.get(gateway_id):
            raise InvalidCarrierGatewayID(gateway_id)
        carrier_gateway = self.carrier_gateways.pop(gateway_id)
        carrier_gateway.state = "deleted"
        return carrier_gateway

    def describe_carrier_gateways(self, ids=None, filters=None):
        carrier_gateways = list(self.carrier_gateways.values())

        if ids:
            carrier_gateways = [
                carrier_gateway
                for carrier_gateway in carrier_gateways
                if carrier_gateway.id in ids
            ]

        attr_pairs = (
            ("carrier-gateway-id", "id"),
            ("state", "state"),
            ("vpc-id", "vpc_id"),
            ("owner-id", "owner_id"),
        )

        result = carrier_gateways
        if filters:
            result = filter_resources(carrier_gateways, filters, attr_pairs)
        return result


class EgressOnlyInternetGateway(TaggedEC2Resource):
    def __init__(self, ec2_backend, vpc_id, tags=None):
        self.id = random_egress_only_internet_gateway_id()
        self.ec2_backend = ec2_backend
        self.vpc_id = vpc_id
        self.state = "attached"
        self.add_tags(tags or {})

    @property
    def physical_resource_id(self):
        return self.id


class EgressOnlyInternetGatewayBackend(object):
    def __init__(self):
        self.egress_only_internet_gateway_backend = {}
        super().__init__()

    def create_egress_only_internet_gateway(self, vpc_id, tags=None):
        vpc = self.get_vpc(vpc_id)
        if not vpc:
            raise InvalidVPCIdError(vpc_id)
        egress_only_igw = EgressOnlyInternetGateway(self, vpc_id, tags)
        self.egress_only_internet_gateway_backend[egress_only_igw.id] = egress_only_igw
        return egress_only_igw

    def describe_egress_only_internet_gateways(self, ids=None, filters=None):
        """
        The Filters-argument is not yet supported
        """
        egress_only_igws = list(self.egress_only_internet_gateway_backend.values())

        if ids:
            egress_only_igws = [
                egress_only_igw
                for egress_only_igw in egress_only_igws
                if egress_only_igw.id in ids
            ]
        return egress_only_igws

    def delete_egress_only_internet_gateway(self, gateway_id):
        egress_only_igw = self.egress_only_internet_gateway_backend.get(gateway_id)
        if not egress_only_igw:
            raise InvalidGatewayIDError(gateway_id)
        if egress_only_igw:
            self.egress_only_internet_gateway_backend.pop(gateway_id)

    def get_egress_only_igw(self, gateway_id):
        egress_only_igw = self.egress_only_internet_gateway_backend.get(
            gateway_id, None
        )
        if not egress_only_igw:
            raise InvalidGatewayIDError(gateway_id)
        return egress_only_igw


class VPCGatewayAttachment(CloudFormationModel):
    # Represents both VPNGatewayAttachment and VPCGatewayAttachment
    def __init__(self, vpc_id, gateway_id=None, state=None):
        self.vpc_id = vpc_id
        self.gateway_id = gateway_id
        self.state = state

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-vpcgatewayattachment.html
        return "AWS::EC2::VPCGatewayAttachment"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[region_name]
        vpn_gateway_id = properties.get("VpnGatewayId", None)
        internet_gateway_id = properties.get("InternetGatewayId", None)
        if vpn_gateway_id:
            attachment = ec2_backend.attach_vpn_gateway(
                vpc_id=properties["VpcId"], vpn_gateway_id=vpn_gateway_id
            )
        elif internet_gateway_id:
            attachment = ec2_backend.attach_internet_gateway(
                internet_gateway_id=internet_gateway_id, vpc_id=properties["VpcId"]
            )
        return attachment

    @property
    def physical_resource_id(self):
        return self.vpc_id


class VPCGatewayAttachmentBackend(object):
    def __init__(self):
        self.gateway_attachments = {}
        super().__init__()

    def create_vpc_gateway_attachment(self, vpc_id, gateway_id):
        attachment = VPCGatewayAttachment(vpc_id, gateway_id=gateway_id)
        self.gateway_attachments[gateway_id] = attachment
        return attachment


class SpotInstanceRequest(BotoSpotRequest, TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        spot_request_id,
        price,
        image_id,
        spot_instance_type,
        valid_from,
        valid_until,
        launch_group,
        availability_zone_group,
        key_name,
        security_groups,
        user_data,
        instance_type,
        placement,
        kernel_id,
        ramdisk_id,
        monitoring_enabled,
        subnet_id,
        tags,
        spot_fleet_id,
        **kwargs,
    ):
        super().__init__(**kwargs)
        ls = LaunchSpecification()
        self.ec2_backend = ec2_backend
        self.launch_specification = ls
        self.id = spot_request_id
        self.state = "open"
        self.price = price
        self.type = spot_instance_type
        self.valid_from = valid_from
        self.valid_until = valid_until
        self.launch_group = launch_group
        self.availability_zone_group = availability_zone_group
        self.user_data = user_data  # NOT
        ls.kernel = kernel_id
        ls.ramdisk = ramdisk_id
        ls.image_id = image_id
        ls.key_name = key_name
        ls.instance_type = instance_type
        ls.placement = placement
        ls.monitored = monitoring_enabled
        ls.subnet_id = subnet_id
        self.spot_fleet_id = spot_fleet_id
        self.tags = tags

        if security_groups:
            for group_name in security_groups:
                group = self.ec2_backend.get_security_group_by_name_or_id(group_name)
                if group:
                    ls.groups.append(group)
        else:
            # If not security groups, add the default
            default_group = self.ec2_backend.get_security_group_by_name_or_id("default")
            ls.groups.append(default_group)

        self.instance = self.launch_instance()

    def get_filter_value(self, filter_name):
        if filter_name == "state":
            return self.state
        elif filter_name == "spot-instance-request-id":
            return self.id
        else:
            return super().get_filter_value(filter_name, "DescribeSpotInstanceRequests")

    def launch_instance(self):
        reservation = self.ec2_backend.add_instances(
            image_id=self.launch_specification.image_id,
            count=1,
            user_data=self.user_data,
            instance_type=self.launch_specification.instance_type,
            subnet_id=self.launch_specification.subnet_id,
            key_name=self.launch_specification.key_name,
            security_group_names=[],
            security_group_ids=self.launch_specification.groups,
            spot_fleet_id=self.spot_fleet_id,
            tags=self.tags,
            lifecycle="spot",
        )
        instance = reservation.instances[0]
        return instance


class SpotRequestBackend(object, metaclass=Model):
    def __init__(self):
        self.spot_instance_requests = {}
        super().__init__()

    def request_spot_instances(
        self,
        price,
        image_id,
        count,
        spot_instance_type,
        valid_from,
        valid_until,
        launch_group,
        availability_zone_group,
        key_name,
        security_groups,
        user_data,
        instance_type,
        placement,
        kernel_id,
        ramdisk_id,
        monitoring_enabled,
        subnet_id,
        tags=None,
        spot_fleet_id=None,
    ):
        requests = []
        tags = tags or {}
        for _ in range(count):
            spot_request_id = random_spot_request_id()
            request = SpotInstanceRequest(
                self,
                spot_request_id,
                price,
                image_id,
                spot_instance_type,
                valid_from,
                valid_until,
                launch_group,
                availability_zone_group,
                key_name,
                security_groups,
                user_data,
                instance_type,
                placement,
                kernel_id,
                ramdisk_id,
                monitoring_enabled,
                subnet_id,
                tags,
                spot_fleet_id,
            )
            self.spot_instance_requests[spot_request_id] = request
            requests.append(request)
        return requests

    @Model.prop("SpotInstanceRequest")
    def describe_spot_instance_requests(self, filters=None, spot_instance_ids=None):
        requests = self.spot_instance_requests.copy().values()

        if spot_instance_ids:
            requests = [i for i in requests if i.id in spot_instance_ids]

        return generic_filter(filters, requests)

    def cancel_spot_instance_requests(self, request_ids):
        requests = []
        for request_id in request_ids:
            requests.append(self.spot_instance_requests.pop(request_id))
        return requests


class SpotFleetLaunchSpec(object):
    def __init__(
        self,
        ebs_optimized,
        group_set,
        iam_instance_profile,
        image_id,
        instance_type,
        key_name,
        monitoring,
        spot_price,
        subnet_id,
        tag_specifications,
        user_data,
        weighted_capacity,
    ):
        self.ebs_optimized = ebs_optimized
        self.group_set = group_set
        self.iam_instance_profile = iam_instance_profile
        self.image_id = image_id
        self.instance_type = instance_type
        self.key_name = key_name
        self.monitoring = monitoring
        self.spot_price = spot_price
        self.subnet_id = subnet_id
        self.tag_specifications = tag_specifications
        self.user_data = user_data
        self.weighted_capacity = float(weighted_capacity)


class SpotFleetRequest(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        spot_fleet_request_id,
        spot_price,
        target_capacity,
        iam_fleet_role,
        allocation_strategy,
        launch_specs,
    ):

        self.ec2_backend = ec2_backend
        self.id = spot_fleet_request_id
        self.spot_price = spot_price
        self.target_capacity = int(target_capacity)
        self.iam_fleet_role = iam_fleet_role
        self.allocation_strategy = allocation_strategy
        self.state = "active"
        self.fulfilled_capacity = 0.0

        self.launch_specs = []
        for spec in launch_specs:
            self.launch_specs.append(
                SpotFleetLaunchSpec(
                    ebs_optimized=spec["ebs_optimized"],
                    group_set=[
                        val for key, val in spec.items() if key.startswith("group_set")
                    ],
                    iam_instance_profile=spec.get("iam_instance_profile._arn"),
                    image_id=spec["image_id"],
                    instance_type=spec["instance_type"],
                    key_name=spec.get("key_name"),
                    monitoring=spec.get("monitoring._enabled"),
                    spot_price=spec.get("spot_price", self.spot_price),
                    subnet_id=spec["subnet_id"],
                    tag_specifications=self._parse_tag_specifications(spec),
                    user_data=spec.get("user_data"),
                    weighted_capacity=spec["weighted_capacity"],
                )
            )

        self.spot_requests = []
        self.create_spot_requests(self.target_capacity)

    @property
    def physical_resource_id(self):
        return self.id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-spotfleet.html
        return "AWS::EC2::SpotFleet"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]["SpotFleetRequestConfigData"]
        ec2_backend = ec2_backends[region_name]

        spot_price = properties.get("SpotPrice")
        target_capacity = properties["TargetCapacity"]
        iam_fleet_role = properties["IamFleetRole"]
        allocation_strategy = properties["AllocationStrategy"]
        launch_specs = properties["LaunchSpecifications"]
        launch_specs = [
            dict(
                [
                    (camelcase_to_underscores(key), val)
                    for key, val in launch_spec.items()
                ]
            )
            for launch_spec in launch_specs
        ]

        spot_fleet_request = ec2_backend.request_spot_fleet(
            spot_price,
            target_capacity,
            iam_fleet_role,
            allocation_strategy,
            launch_specs,
        )

        return spot_fleet_request

    def get_launch_spec_counts(self, weight_to_add):
        weight_map = defaultdict(int)

        weight_so_far = 0
        if self.allocation_strategy == "diversified":
            launch_spec_index = 0
            while True:
                launch_spec = self.launch_specs[
                    launch_spec_index % len(self.launch_specs)
                ]
                weight_map[launch_spec] += 1
                weight_so_far += launch_spec.weighted_capacity
                if weight_so_far >= weight_to_add:
                    break
                launch_spec_index += 1
        else:  # lowestPrice
            cheapest_spec = sorted(
                # FIXME: change `+inf` to the on demand price scaled to weighted capacity when it's not present
                self.launch_specs,
                key=lambda spec: float(spec.spot_price or "+inf"),
            )[0]
            weight_so_far = weight_to_add + (
                weight_to_add % cheapest_spec.weighted_capacity
            )
            weight_map[cheapest_spec] = int(
                weight_so_far // cheapest_spec.weighted_capacity
            )

        return weight_map, weight_so_far

    def create_spot_requests(self, weight_to_add):
        weight_map, added_weight = self.get_launch_spec_counts(weight_to_add)
        for launch_spec, count in weight_map.items():
            requests = self.ec2_backend.request_spot_instances(
                price=launch_spec.spot_price,
                image_id=launch_spec.image_id,
                count=count,
                spot_instance_type="persistent",
                valid_from=None,
                valid_until=None,
                launch_group=None,
                availability_zone_group=None,
                key_name=launch_spec.key_name,
                security_groups=launch_spec.group_set,
                user_data=launch_spec.user_data,
                instance_type=launch_spec.instance_type,
                placement=None,
                kernel_id=None,
                ramdisk_id=None,
                monitoring_enabled=launch_spec.monitoring,
                subnet_id=launch_spec.subnet_id,
                spot_fleet_id=self.id,
                tags=launch_spec.tag_specifications,
            )
            self.spot_requests.extend(requests)
        self.fulfilled_capacity += added_weight
        return self.spot_requests

    def terminate_instances(self):
        instance_ids = []
        new_fulfilled_capacity = self.fulfilled_capacity
        for req in self.spot_requests:
            instance = req.instance
            for spec in self.launch_specs:
                if (
                    spec.instance_type == instance.instance_type
                    and spec.subnet_id == instance.subnet_id
                ):
                    break

            if new_fulfilled_capacity - spec.weighted_capacity < self.target_capacity:
                continue
            new_fulfilled_capacity -= spec.weighted_capacity
            instance_ids.append(instance.id)

        self.spot_requests = [
            req for req in self.spot_requests if req.instance.id not in instance_ids
        ]
        self.ec2_backend.terminate_instances(instance_ids)

    def _parse_tag_specifications(self, spec):
        try:
            tag_spec_num = max(
                [
                    int(key.split(".")[1])
                    for key in spec
                    if key.startswith("tag_specification_set")
                ]
            )
        except ValueError:  # no tag specifications
            return {}

        tag_specifications = {}
        for si in range(1, tag_spec_num + 1):
            resource_type = spec[
                "tag_specification_set.{si}._resource_type".format(si=si)
            ]

            tags = [
                key
                for key in spec
                if key.startswith("tag_specification_set.{si}._tag".format(si=si))
            ]
            tag_num = max([int(key.split(".")[3]) for key in tags])
            tag_specifications[resource_type] = dict(
                (
                    spec[
                        "tag_specification_set.{si}._tag.{ti}._key".format(si=si, ti=ti)
                    ],
                    spec[
                        "tag_specification_set.{si}._tag.{ti}._value".format(
                            si=si, ti=ti
                        )
                    ],
                )
                for ti in range(1, tag_num + 1)
            )

        return tag_specifications


class SpotFleetBackend(object):
    def __init__(self):
        self.spot_fleet_requests = {}
        super().__init__()

    def request_spot_fleet(
        self,
        spot_price,
        target_capacity,
        iam_fleet_role,
        allocation_strategy,
        launch_specs,
    ):

        spot_fleet_request_id = random_spot_fleet_request_id()
        request = SpotFleetRequest(
            self,
            spot_fleet_request_id,
            spot_price,
            target_capacity,
            iam_fleet_role,
            allocation_strategy,
            launch_specs,
        )
        self.spot_fleet_requests[spot_fleet_request_id] = request
        return request

    def get_spot_fleet_request(self, spot_fleet_request_id):
        return self.spot_fleet_requests[spot_fleet_request_id]

    def describe_spot_fleet_instances(self, spot_fleet_request_id):
        spot_fleet = self.get_spot_fleet_request(spot_fleet_request_id)
        return spot_fleet.spot_requests

    def describe_spot_fleet_requests(self, spot_fleet_request_ids):
        requests = self.spot_fleet_requests.values()

        if spot_fleet_request_ids:
            requests = [
                request for request in requests if request.id in spot_fleet_request_ids
            ]

        return requests

    def cancel_spot_fleet_requests(self, spot_fleet_request_ids, terminate_instances):
        spot_requests = []
        for spot_fleet_request_id in spot_fleet_request_ids:
            spot_fleet = self.spot_fleet_requests[spot_fleet_request_id]
            if terminate_instances:
                spot_fleet.target_capacity = 0
                spot_fleet.terminate_instances()
            spot_requests.append(spot_fleet)
            del self.spot_fleet_requests[spot_fleet_request_id]
        return spot_requests

    def modify_spot_fleet_request(
        self, spot_fleet_request_id, target_capacity, terminate_instances
    ):
        if target_capacity < 0:
            raise ValueError("Cannot reduce spot fleet capacity below 0")
        spot_fleet_request = self.spot_fleet_requests[spot_fleet_request_id]
        delta = target_capacity - spot_fleet_request.fulfilled_capacity
        spot_fleet_request.target_capacity = target_capacity
        if delta > 0:
            spot_fleet_request.create_spot_requests(delta)
        elif delta < 0 and terminate_instances == "Default":
            spot_fleet_request.terminate_instances()
        return True


class SpotPriceBackend(object):
    def describe_spot_price_history(self, instance_types=None, filters=None):
        matches = INSTANCE_TYPE_OFFERINGS["availability-zone"]
        matches = matches.get(self.region_name, [])

        def matches_filters(offering, filters):
            def matches_filter(key, values):
                if key == "availability-zone":
                    return offering.get("Location") in values
                elif key == "instance-type":
                    return offering.get("InstanceType") in values
                else:
                    return False

            return all([matches_filter(key, values) for key, values in filters.items()])

        matches = [o for o in matches if matches_filters(o, filters)]

        if instance_types:
            matches = [t for t in matches if t.get("InstanceType") in instance_types]

        return matches


class ElasticAddress(TaggedEC2Resource, CloudFormationModel):
    def __init__(self, ec2_backend, domain, address=None, tags=None):
        self.ec2_backend = ec2_backend
        if address:
            self.public_ip = address
        else:
            self.public_ip = random_ip()
        self.allocation_id = random_eip_allocation_id() if domain == "vpc" else None
        self.id = self.allocation_id
        self.domain = domain
        self.instance = None
        self.eni = None
        self.association_id = None
        self.add_tags(tags or {})

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-eip.html
        return "AWS::EC2::EIP"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        ec2_backend = ec2_backends[region_name]

        properties = cloudformation_json.get("Properties")
        instance_id = None
        if properties:
            domain = properties.get("Domain")
            # TODO: support tags from cloudformation template
            eip = ec2_backend.allocate_address(domain=domain if domain else "standard")
            instance_id = properties.get("InstanceId")
        else:
            eip = ec2_backend.allocate_address(domain="standard")

        if instance_id:
            instance = ec2_backend.get_instance_by_id(instance_id)
            ec2_backend.associate_address(instance, address=eip.public_ip)

        return eip

    @property
    def physical_resource_id(self):
        return self.public_ip

    @classmethod
    def has_cfn_attr(cls, attribute):
        return attribute in ["AllocationId"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "AllocationId":
            return self.allocation_id
        raise UnformattedGetAttTemplateException()

    def get_filter_value(self, filter_name):
        if filter_name == "allocation-id":
            return self.allocation_id
        elif filter_name == "association-id":
            return self.association_id
        elif filter_name == "domain":
            return self.domain
        elif filter_name == "instance-id":
            if self.instance:
                return self.instance.id
            return None
        elif filter_name == "network-interface-id":
            if self.eni:
                return self.eni.id
            return None
        elif filter_name == "private-ip-address":
            if self.eni:
                return self.eni.private_ip_address
            return None
        elif filter_name == "public-ip":
            return self.public_ip
        elif filter_name == "network-interface-owner-id":
            # TODO: implement network-interface-owner-id
            raise FilterNotImplementedError(filter_name, "DescribeAddresses")
        else:
            return super().get_filter_value(filter_name, "DescribeAddresses")


class ElasticAddressBackend(object):
    def __init__(self):
        self.addresses = []
        super().__init__()

    def allocate_address(self, domain, address=None, tags=None):
        if domain not in ["standard", "vpc"]:
            raise InvalidDomainError(domain)
        if address:
            address = ElasticAddress(self, domain=domain, address=address, tags=tags)
        else:
            address = ElasticAddress(self, domain=domain, tags=tags)
        self.addresses.append(address)
        return address

    def address_by_ip(self, ips, fail_if_not_found=True):
        eips = [
            address for address in self.addresses.copy() if address.public_ip in ips
        ]

        # TODO: Trim error message down to specific invalid address.
        if (not eips or len(ips) > len(eips)) and fail_if_not_found:
            raise InvalidAddressError(ips)

        return eips

    def address_by_allocation(self, allocation_ids):
        eips = [
            address
            for address in self.addresses
            if address.allocation_id in allocation_ids
        ]

        # TODO: Trim error message down to specific invalid id.
        if not eips or len(allocation_ids) > len(eips):
            raise InvalidAllocationIdError(allocation_ids)

        return eips

    def address_by_association(self, association_ids):
        eips = [
            address
            for address in self.addresses
            if address.association_id in association_ids
        ]

        # TODO: Trim error message down to specific invalid id.
        if not eips or len(association_ids) > len(eips):
            raise InvalidAssociationIdError(association_ids)

        return eips

    def associate_address(
        self,
        instance=None,
        eni=None,
        address=None,
        allocation_id=None,
        reassociate=False,
    ):
        eips = []
        if address:
            eips = self.address_by_ip([address])
        elif allocation_id:
            eips = self.address_by_allocation([allocation_id])
        eip = eips[0]

        new_instance_association = bool(
            instance and (not eip.instance or eip.instance.id == instance.id)
        )
        new_eni_association = bool(eni and (not eip.eni or eni.id == eip.eni.id))

        if new_instance_association or new_eni_association or reassociate:
            eip.instance = instance
            eip.eni = eni
            if not eip.eni and instance:
                # default to primary network interface
                eip.eni = instance.nics[0]
            if eip.eni:
                eip.eni.public_ip = eip.public_ip
            if eip.domain == "vpc":
                eip.association_id = random_eip_association_id()

            return eip

        raise ResourceAlreadyAssociatedError(eip.public_ip)

    def describe_addresses(self, allocation_ids=None, public_ips=None, filters=None):
        matches = self.addresses.copy()
        if allocation_ids:
            matches = [addr for addr in matches if addr.allocation_id in allocation_ids]
            if len(allocation_ids) > len(matches):
                unknown_ids = set(allocation_ids) - set(matches)
                raise InvalidAllocationIdError(unknown_ids)
        if public_ips:
            matches = [addr for addr in matches if addr.public_ip in public_ips]
            if len(public_ips) > len(matches):
                unknown_ips = set(public_ips) - set(matches)
                raise InvalidAddressError(unknown_ips)
        if filters:
            matches = generic_filter(filters, matches)

        return matches

    def disassociate_address(self, address=None, association_id=None):
        eips = []
        if address:
            eips = self.address_by_ip([address])
        elif association_id:
            eips = self.address_by_association([association_id])
        eip = eips[0]

        if eip.eni:
            eip.eni.public_ip = None
            if eip.eni.instance and eip.eni.instance._state.name == "running":
                eip.eni.check_auto_public_ip()
            eip.eni = None

        eip.instance = None
        eip.association_id = None
        return True

    def release_address(self, address=None, allocation_id=None):
        eips = []
        if address:
            eips = self.address_by_ip([address])
        elif allocation_id:
            eips = self.address_by_allocation([allocation_id])
        eip = eips[0]

        self.disassociate_address(address=eip.public_ip)
        eip.allocation_id = None
        self.addresses.remove(eip)
        return True


class DHCPOptionsSet(TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        domain_name_servers=None,
        domain_name=None,
        ntp_servers=None,
        netbios_name_servers=None,
        netbios_node_type=None,
    ):
        self.ec2_backend = ec2_backend
        self._options = {
            "domain-name-servers": domain_name_servers,
            "domain-name": domain_name,
            "ntp-servers": ntp_servers,
            "netbios-name-servers": netbios_name_servers,
            "netbios-node-type": netbios_node_type,
        }
        self.id = random_dhcp_option_id()
        self.vpc = None

    def get_filter_value(self, filter_name):
        """
        API Version 2015-10-01 defines the following filters for DescribeDhcpOptions:

        * dhcp-options-id
        * key
        * value
        * tag:key=value
        * tag-key
        * tag-value

        Taken from: http://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeDhcpOptions.html
        """
        if filter_name == "dhcp-options-id":
            return self.id
        elif filter_name == "key":
            return list(self._options.keys())
        elif filter_name == "value":
            values = [item for item in list(self._options.values()) if item]
            return itertools.chain(*values)
        else:
            return super().get_filter_value(filter_name, "DescribeDhcpOptions")

    @property
    def options(self):
        return self._options


class DHCPOptionsSetBackend(object):
    def __init__(self):
        self.dhcp_options_sets = {}
        super().__init__()

    def associate_dhcp_options(self, dhcp_options, vpc):
        dhcp_options.vpc = vpc
        vpc.dhcp_options = dhcp_options

    def create_dhcp_options(
        self,
        domain_name_servers=None,
        domain_name=None,
        ntp_servers=None,
        netbios_name_servers=None,
        netbios_node_type=None,
    ):

        NETBIOS_NODE_TYPES = [1, 2, 4, 8]

        for field_value in domain_name_servers, ntp_servers, netbios_name_servers:
            if field_value and len(field_value) > 4:
                raise InvalidParameterValueError(",".join(field_value))

        if netbios_node_type and int(netbios_node_type[0]) not in NETBIOS_NODE_TYPES:
            raise InvalidParameterValueError(netbios_node_type)

        options = DHCPOptionsSet(
            self,
            domain_name_servers,
            domain_name,
            ntp_servers,
            netbios_name_servers,
            netbios_node_type,
        )
        self.dhcp_options_sets[options.id] = options
        return options

    def delete_dhcp_options_set(self, options_id):
        if not (options_id and options_id.startswith("dopt-")):
            raise MalformedDHCPOptionsIdError(options_id)

        if options_id in self.dhcp_options_sets:
            if self.dhcp_options_sets[options_id].vpc:
                raise DependencyViolationError("Cannot delete assigned DHCP options.")
            self.dhcp_options_sets.pop(options_id)
        else:
            raise InvalidDHCPOptionsIdError(options_id)
        return True

    def describe_dhcp_options(self, dhcp_options_ids=None, filters=None):
        dhcp_options_sets = self.dhcp_options_sets.copy().values()

        if dhcp_options_ids:
            dhcp_options_sets = [
                dhcp_options_set
                for dhcp_options_set in dhcp_options_sets
                if dhcp_options_set.id in dhcp_options_ids
            ]
            if len(dhcp_options_sets) != len(dhcp_options_ids):
                invalid_id = list(
                    set(dhcp_options_ids).difference(
                        set(
                            [
                                dhcp_options_set.id
                                for dhcp_options_set in dhcp_options_sets
                            ]
                        )
                    )
                )[0]
                raise InvalidDHCPOptionsIdError(invalid_id)

        return generic_filter(filters, dhcp_options_sets)


class VPNConnection(TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        vpn_connection_id,
        vpn_conn_type,
        customer_gateway_id,
        vpn_gateway_id=None,
        transit_gateway_id=None,
        tags=None,
    ):
        self.ec2_backend = ec2_backend
        self.id = vpn_connection_id
        self.state = "available"
        self.customer_gateway_configuration = {}
        self.type = vpn_conn_type
        self.customer_gateway_id = customer_gateway_id
        self.vpn_gateway_id = vpn_gateway_id
        self.transit_gateway_id = transit_gateway_id
        self.tunnels = None
        self.options = None
        self.static_routes = None
        self.add_tags(tags or {})

    def get_filter_value(self, filter_name):
        return super().get_filter_value(filter_name, "DescribeVpnConnections")


class VPNConnectionBackend(object):
    def __init__(self):
        self.vpn_connections = {}
        super().__init__()

    def create_vpn_connection(
        self,
        vpn_conn_type,
        customer_gateway_id,
        vpn_gateway_id=None,
        transit_gateway_id=None,
        static_routes_only=None,
        tags=None,
    ):
        vpn_connection_id = random_vpn_connection_id()
        if static_routes_only:
            pass
        vpn_connection = VPNConnection(
            self,
            vpn_connection_id=vpn_connection_id,
            vpn_conn_type=vpn_conn_type,
            customer_gateway_id=customer_gateway_id,
            vpn_gateway_id=vpn_gateway_id,
            transit_gateway_id=transit_gateway_id,
            tags=tags,
        )
        self.vpn_connections[vpn_connection.id] = vpn_connection
        return vpn_connection

    def delete_vpn_connection(self, vpn_connection_id):

        if vpn_connection_id in self.vpn_connections:
            self.vpn_connections[vpn_connection_id].state = "deleted"
        else:
            raise InvalidVpnConnectionIdError(vpn_connection_id)
        return self.vpn_connections[vpn_connection_id]

    def describe_vpn_connections(self, vpn_connection_ids=None):
        vpn_connections = []
        for vpn_connection_id in vpn_connection_ids or []:
            if vpn_connection_id in self.vpn_connections:
                vpn_connections.append(self.vpn_connections[vpn_connection_id])
            else:
                raise InvalidVpnConnectionIdError(vpn_connection_id)
        return vpn_connections or self.vpn_connections.values()

    def get_all_vpn_connections(self, vpn_connection_ids=None, filters=None):
        vpn_connections = self.vpn_connections.values()

        if vpn_connection_ids:
            vpn_connections = [
                vpn_connection
                for vpn_connection in vpn_connections
                if vpn_connection.id in vpn_connection_ids
            ]
            if len(vpn_connections) != len(vpn_connection_ids):
                invalid_id = list(
                    set(vpn_connection_ids).difference(
                        set([vpn_connection.id for vpn_connection in vpn_connections])
                    )
                )[0]
                raise InvalidVpnConnectionIdError(invalid_id)

        return generic_filter(filters, vpn_connections)


class NetworkAclBackend(object):
    def __init__(self):
        self.network_acls = {}
        super().__init__()

    def get_network_acl(self, network_acl_id):
        network_acl = self.network_acls.get(network_acl_id, None)
        if not network_acl:
            raise InvalidNetworkAclIdError(network_acl_id)
        return network_acl

    def create_network_acl(self, vpc_id, tags=None, default=False):
        network_acl_id = random_network_acl_id()
        self.get_vpc(vpc_id)
        network_acl = NetworkAcl(self, network_acl_id, vpc_id, default)
        for tag in tags or []:
            network_acl.add_tag(tag.get("Key"), tag.get("Value"))
        self.network_acls[network_acl_id] = network_acl
        if default:
            self.add_default_entries(network_acl_id)
        return network_acl

    def add_default_entries(self, network_acl_id):
        default_acl_entries = [
            {"rule_number": "100", "rule_action": "allow", "egress": "true"},
            {"rule_number": "32767", "rule_action": "deny", "egress": "true"},
            {"rule_number": "100", "rule_action": "allow", "egress": "false"},
            {"rule_number": "32767", "rule_action": "deny", "egress": "false"},
        ]
        for entry in default_acl_entries:
            self.create_network_acl_entry(
                network_acl_id=network_acl_id,
                rule_number=entry["rule_number"],
                protocol="-1",
                rule_action=entry["rule_action"],
                egress=entry["egress"],
                cidr_block="0.0.0.0/0",
                icmp_code=None,
                icmp_type=None,
                port_range_from=None,
                port_range_to=None,
            )

    def get_all_network_acls(self, network_acl_ids=None, filters=None):
        self.describe_network_acls(network_acl_ids, filters)

    def delete_network_acl(self, network_acl_id):
        deleted = self.network_acls.pop(network_acl_id, None)
        if not deleted:
            raise InvalidNetworkAclIdError(network_acl_id)
        return deleted

    def create_network_acl_entry(
        self,
        network_acl_id,
        rule_number,
        protocol,
        rule_action,
        egress,
        cidr_block,
        icmp_code,
        icmp_type,
        port_range_from,
        port_range_to,
    ):

        network_acl = self.get_network_acl(network_acl_id)
        if any(
            entry.egress == egress and entry.rule_number == rule_number
            for entry in network_acl.network_acl_entries
        ):
            raise NetworkAclEntryAlreadyExistsError(rule_number)
        network_acl_entry = NetworkAclEntry(
            self,
            network_acl_id,
            rule_number,
            protocol,
            rule_action,
            egress,
            cidr_block,
            icmp_code,
            icmp_type,
            port_range_from,
            port_range_to,
        )

        network_acl.network_acl_entries.append(network_acl_entry)
        return network_acl_entry

    def delete_network_acl_entry(self, network_acl_id, rule_number, egress):
        network_acl = self.get_network_acl(network_acl_id)
        entry = next(
            entry
            for entry in network_acl.network_acl_entries
            if entry.egress == egress and entry.rule_number == rule_number
        )
        if entry is not None:
            network_acl.network_acl_entries.remove(entry)
        return entry

    def replace_network_acl_entry(
        self,
        network_acl_id,
        rule_number,
        protocol,
        rule_action,
        egress,
        cidr_block,
        icmp_code,
        icmp_type,
        port_range_from,
        port_range_to,
    ):

        self.delete_network_acl_entry(network_acl_id, rule_number, egress)
        network_acl_entry = self.create_network_acl_entry(
            network_acl_id,
            rule_number,
            protocol,
            rule_action,
            egress,
            cidr_block,
            icmp_code,
            icmp_type,
            port_range_from,
            port_range_to,
        )
        return network_acl_entry

    def replace_network_acl_association(self, association_id, network_acl_id):

        # lookup existing association for subnet and delete it
        default_acl = next(
            value
            for key, value in self.network_acls.items()
            if association_id in value.associations.keys()
        )

        subnet_id = None
        for key, value in default_acl.associations.items():
            if key == association_id:
                subnet_id = default_acl.associations[key].subnet_id
                del default_acl.associations[key]
                break

        new_assoc_id = random_network_acl_subnet_association_id()
        association = NetworkAclAssociation(
            self, new_assoc_id, subnet_id, network_acl_id
        )
        new_acl = self.get_network_acl(network_acl_id)
        new_acl.associations[new_assoc_id] = association
        return association

    def associate_default_network_acl_with_subnet(self, subnet_id, vpc_id):
        association_id = random_network_acl_subnet_association_id()
        acl = next(
            acl
            for acl in self.network_acls.values()
            if acl.default and acl.vpc_id == vpc_id
        )
        acl.associations[association_id] = NetworkAclAssociation(
            self, association_id, subnet_id, acl.id
        )

    def describe_network_acls(self, network_acl_ids=None, filters=None):
        network_acls = self.network_acls.copy().values()

        if network_acl_ids:
            network_acls = [
                network_acl
                for network_acl in network_acls
                if network_acl.id in network_acl_ids
            ]
            if len(network_acls) != len(network_acl_ids):
                invalid_id = list(
                    set(network_acl_ids).difference(
                        set([network_acl.id for network_acl in network_acls])
                    )
                )[0]
                raise InvalidRouteTableIdError(invalid_id)

        return generic_filter(filters, network_acls)


class NetworkAclAssociation(object):
    def __init__(self, ec2_backend, new_association_id, subnet_id, network_acl_id):
        self.ec2_backend = ec2_backend
        self.id = new_association_id
        self.new_association_id = new_association_id
        self.subnet_id = subnet_id
        self.network_acl_id = network_acl_id
        super().__init__()


class NetworkAcl(TaggedEC2Resource):
    def __init__(
        self, ec2_backend, network_acl_id, vpc_id, default=False, owner_id=OWNER_ID,
    ):
        self.ec2_backend = ec2_backend
        self.id = network_acl_id
        self.vpc_id = vpc_id
        self.owner_id = owner_id
        self.network_acl_entries = []
        self.associations = {}
        self.default = "true" if default is True else "false"

    def get_filter_value(self, filter_name):
        if filter_name == "default":
            return self.default
        elif filter_name == "vpc-id":
            return self.vpc_id
        elif filter_name == "association.network-acl-id":
            return self.id
        elif filter_name == "association.subnet-id":
            return [assoc.subnet_id for assoc in self.associations.values()]
        elif filter_name == "owner-id":
            return self.owner_id
        else:
            return super().get_filter_value(filter_name, "DescribeNetworkAcls")


class NetworkAclEntry(TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        network_acl_id,
        rule_number,
        protocol,
        rule_action,
        egress,
        cidr_block,
        icmp_code,
        icmp_type,
        port_range_from,
        port_range_to,
    ):
        self.ec2_backend = ec2_backend
        self.network_acl_id = network_acl_id
        self.rule_number = rule_number
        self.protocol = protocol
        self.rule_action = rule_action
        self.egress = egress
        self.cidr_block = cidr_block
        self.icmp_code = icmp_code
        self.icmp_type = icmp_type
        self.port_range_from = port_range_from
        self.port_range_to = port_range_to


class VpnGateway(CloudFormationModel, TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        gateway_id,
        gateway_type,
        amazon_side_asn,
        availability_zone,
        tags=None,
        state="available",
    ):
        self.ec2_backend = ec2_backend
        self.id = gateway_id
        self.type = gateway_type
        self.amazon_side_asn = amazon_side_asn
        self.availability_zone = availability_zone
        self.state = state
        self.add_tags(tags or {})
        self.attachments = {}
        super().__init__()

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-vpcgatewayattachment.html
        return "AWS::EC2::VPNGateway"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]
        _type = properties["Type"]
        asn = properties.get("AmazonSideAsn", None)
        ec2_backend = ec2_backends[region_name]

        return ec2_backend.create_vpn_gateway(gateway_type=_type, amazon_side_asn=asn)

    @property
    def physical_resource_id(self):
        return self.id

    def get_filter_value(self, filter_name):
        if filter_name == "attachment.vpc-id":
            return self.attachments.keys()
        elif filter_name == "attachment.state":
            return [attachment.state for attachment in self.attachments.values()]
        elif filter_name == "vpn-gateway-id":
            return self.id
        elif filter_name == "type":
            return self.type
        return super().get_filter_value(filter_name, "DescribeVpnGateways")


class VpnGatewayBackend(object):
    def __init__(self):
        self.vpn_gateways = {}
        super().__init__()

    def create_vpn_gateway(
        self,
        gateway_type="ipsec.1",
        amazon_side_asn=None,
        availability_zone=None,
        tags=None,
    ):
        vpn_gateway_id = random_vpn_gateway_id()
        vpn_gateway = VpnGateway(
            self, vpn_gateway_id, gateway_type, amazon_side_asn, availability_zone, tags
        )
        self.vpn_gateways[vpn_gateway_id] = vpn_gateway
        return vpn_gateway

    def describe_vpn_gateways(self, filters=None, vpn_gw_ids=None):
        vpn_gateways = list(self.vpn_gateways.values() or [])
        if vpn_gw_ids:
            vpn_gateways = [item for item in vpn_gateways if item.id in vpn_gw_ids]
        return generic_filter(filters, vpn_gateways)

    def get_vpn_gateway(self, vpn_gateway_id):
        vpn_gateway = self.vpn_gateways.get(vpn_gateway_id, None)
        if not vpn_gateway:
            raise InvalidVpnGatewayIdError(vpn_gateway_id)
        return vpn_gateway

    def attach_vpn_gateway(self, vpn_gateway_id, vpc_id):
        vpn_gateway = self.get_vpn_gateway(vpn_gateway_id)
        self.get_vpc(vpc_id)
        attachment = VPCGatewayAttachment(vpc_id, state="attached")
        for key in vpn_gateway.attachments.copy():
            if key.startswith("vpc-"):
                vpn_gateway.attachments.pop(key)
        vpn_gateway.attachments[vpc_id] = attachment
        return attachment

    def delete_vpn_gateway(self, vpn_gateway_id):
        deleted = self.vpn_gateways.get(vpn_gateway_id, None)
        if not deleted:
            raise InvalidVpnGatewayIdError(vpn_gateway_id)
        deleted.state = "deleted"
        return deleted

    def detach_vpn_gateway(self, vpn_gateway_id, vpc_id):
        vpn_gateway = self.get_vpn_gateway(vpn_gateway_id)
        detached = vpn_gateway.attachments.get(vpc_id, None)
        if not detached:
            raise InvalidVpnGatewayAttachmentError(vpn_gateway.id, vpc_id)
        detached.state = "detached"
        return detached


class CustomerGateway(TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        gateway_id,
        gateway_type,
        ip_address,
        bgp_asn,
        state="available",
        tags=None,
    ):
        self.ec2_backend = ec2_backend
        self.id = gateway_id
        self.type = gateway_type
        self.ip_address = ip_address
        self.bgp_asn = bgp_asn
        self.attachments = {}
        self.state = state
        self.add_tags(tags or {})
        super().__init__()

    def get_filter_value(self, filter_name):
        return super().get_filter_value(filter_name, "DescribeCustomerGateways")


class CustomerGatewayBackend(object):
    def __init__(self):
        self.customer_gateways = {}
        super().__init__()

    def create_customer_gateway(
        self, gateway_type="ipsec.1", ip_address=None, bgp_asn=None, tags=None
    ):
        customer_gateway_id = random_customer_gateway_id()
        customer_gateway = CustomerGateway(
            self, customer_gateway_id, gateway_type, ip_address, bgp_asn, tags=tags
        )
        self.customer_gateways[customer_gateway_id] = customer_gateway
        return customer_gateway

    def get_all_customer_gateways(self, filters=None, customer_gateway_ids=None):
        customer_gateways = self.customer_gateways.copy().values()
        if customer_gateway_ids:
            customer_gateways = [
                cg for cg in customer_gateways if cg.id in customer_gateway_ids
            ]

        if filters is not None:
            if filters.get("customer-gateway-id") is not None:
                customer_gateways = [
                    customer_gateway
                    for customer_gateway in customer_gateways
                    if customer_gateway.id in filters["customer-gateway-id"]
                ]
            if filters.get("type") is not None:
                customer_gateways = [
                    customer_gateway
                    for customer_gateway in customer_gateways
                    if customer_gateway.type in filters["type"]
                ]
            if filters.get("bgp-asn") is not None:
                customer_gateways = [
                    customer_gateway
                    for customer_gateway in customer_gateways
                    if customer_gateway.bgp_asn in filters["bgp-asn"]
                ]
            if filters.get("ip-address") is not None:
                customer_gateways = [
                    customer_gateway
                    for customer_gateway in customer_gateways
                    if customer_gateway.ip_address in filters["ip-address"]
                ]
        return customer_gateways

    def get_customer_gateway(self, customer_gateway_id):
        customer_gateway = self.customer_gateways.get(customer_gateway_id, None)
        if not customer_gateway:
            raise InvalidCustomerGatewayIdError(customer_gateway_id)
        return customer_gateway

    def delete_customer_gateway(self, customer_gateway_id):
        customer_gateway = self.get_customer_gateway(customer_gateway_id)
        customer_gateway.state = "deleted"
        # deleted = self.customer_gateways.pop(customer_gateway_id, None)
        deleted = True
        if not deleted:
            raise InvalidCustomerGatewayIdError(customer_gateway_id)
        return deleted


class TransitGateway(TaggedEC2Resource, CloudFormationModel):
    DEFAULT_OPTIONS = {
        "AmazonSideAsn": "64512",
        "AssociationDefaultRouteTableId": "tgw-rtb-0d571391e50cf8514",
        "AutoAcceptSharedAttachments": "disable",
        "DefaultRouteTableAssociation": "enable",
        "DefaultRouteTablePropagation": "enable",
        "DnsSupport": "enable",
        "MulticastSupport": "disable",
        "PropagationDefaultRouteTableId": "tgw-rtb-0d571391e50cf8514",
        "TransitGatewayCidrBlocks": None,
        "VpnEcmpSupport": "enable",
    }

    def __init__(self, backend, description=None, options=None):
        self.ec2_backend = backend
        self.id = random_transit_gateway_id()
        self.description = description
        self.state = "available"
        self.options = merge_multiple_dicts(self.DEFAULT_OPTIONS, options or {})
        self._created_at = datetime.utcnow()

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def create_time(self):
        return iso_8601_datetime_with_milliseconds(self._created_at)

    @property
    def owner_id(self):
        return ACCOUNT_ID

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-natgateway.html
        return "AWS::EC2::TransitGateway"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        ec2_backend = ec2_backends[region_name]
        properties = cloudformation_json["Properties"]
        description = properties["Description"]
        options = dict(properties)
        del options["Description"]
        transit_gateway = ec2_backend.create_transit_gateway(
            description=description, options=options
        )

        for tag in properties.get("Tags", []):
            tag_key = tag["Key"]
            tag_value = tag["Value"]
            transit_gateway.add_tag(tag_key, tag_value)

        return transit_gateway


class TransitGatewayBackend(object):
    def __init__(self):
        self.transit_gateways = {}
        super().__init__()

    def create_transit_gateway(self, description=None, options=None, tags=None):
        transit_gateway = TransitGateway(self, description, options)
        for tag in tags or []:
            tag_key = tag.get("Key")
            tag_value = tag.get("Value")
            transit_gateway.add_tag(tag_key, tag_value)

        self.transit_gateways[transit_gateway.id] = transit_gateway
        return transit_gateway

    def describe_transit_gateways(self, filters, transit_gateway_ids):
        transit_gateways = list(self.transit_gateways.copy().values())

        if transit_gateway_ids:
            transit_gateways = [
                item for item in transit_gateways if item.id in transit_gateway_ids
            ]

        attr_pairs = (
            ("transit-gateway-id", "id"),
            ("state", "state"),
            ("owner-id", "owner_id"),
        )

        result = transit_gateways
        if filters:
            result = filter_resources(transit_gateways, filters, attr_pairs)
        return result

    def delete_transit_gateway(self, transit_gateway_id):
        return self.transit_gateways.pop(transit_gateway_id)

    def modify_transit_gateway(
        self, transit_gateway_id, description=None, options=None
    ):
        transit_gateway = self.transit_gateways.get(transit_gateway_id)
        if description:
            transit_gateway.description = description
        if options:
            transit_gateway.options.update(options)
        return transit_gateway


class TransitGatewayRouteTable(TaggedEC2Resource):
    def __init__(
        self,
        backend,
        transit_gateway_id,
        tags=None,
        default_association_route_table=False,
        default_propagation_route_table=False,
    ):
        self.ec2_backend = backend
        self.id = random_transit_gateway_route_table_id()
        self.transit_gateway_id = transit_gateway_id

        self._created_at = datetime.utcnow()

        self.default_association_route_table = default_association_route_table
        self.default_propagation_route_table = default_propagation_route_table
        self.state = "available"
        self.routes = {}
        self.add_tags(tags or {})
        self.route_table_association = {}
        self.route_table_propagation = {}

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def create_time(self):
        return iso_8601_datetime_with_milliseconds(self._created_at)


class TransitGatewayRouteTableBackend(object):
    def __init__(self):
        self.transit_gateways_route_tables = {}
        super().__init__()

    def create_transit_gateway_route_table(
        self,
        transit_gateway_id,
        tags=None,
        default_association_route_table=False,
        default_propagation_route_table=False,
    ):
        transit_gateways_route_table = TransitGatewayRouteTable(
            self,
            transit_gateway_id=transit_gateway_id,
            tags=tags,
            default_association_route_table=default_association_route_table,
            default_propagation_route_table=default_propagation_route_table,
        )
        self.transit_gateways_route_tables[
            transit_gateways_route_table.id
        ] = transit_gateways_route_table
        return transit_gateways_route_table

    def get_all_transit_gateway_route_tables(
        self, transit_gateway_route_table_ids=None, filters=None
    ):
        transit_gateway_route_tables = list(self.transit_gateways_route_tables.values())

        attr_pairs = (
            ("default-association-route-table", "default_association_route_table"),
            ("default-propagation-route-table", "default_propagation_route_table"),
            ("state", "state"),
            ("transit-gateway-id", "transit_gateway_id"),
            ("transit-gateway-route-table-id", "id"),
        )

        if transit_gateway_route_table_ids:
            transit_gateway_route_tables = [
                transit_gateway_route_table
                for transit_gateway_route_table in transit_gateway_route_tables
                if transit_gateway_route_table.id in transit_gateway_route_table_ids
            ]

        result = transit_gateway_route_tables
        if filters:
            result = filter_resources(transit_gateway_route_tables, filters, attr_pairs)
        return result

    def delete_transit_gateway_route_table(self, transit_gateway_route_table_id):
        transit_gateways_route_table = self.transit_gateways_route_tables[
            transit_gateway_route_table_id
        ]
        transit_gateways_route_table.state = "deleted"
        return transit_gateways_route_table

    def create_transit_gateway_route(
        self,
        transit_gateway_route_table_id,
        destination_cidr_block,
        transit_gateway_attachment_id=None,
        blackhole=False,
    ):
        transit_gateways_route_table = self.transit_gateways_route_tables.get(
            transit_gateway_route_table_id
        )
        transit_gateway_attachment = self.transit_gateway_attachments.get(
            transit_gateway_attachment_id
        )
        transit_gateways_route_table.routes[destination_cidr_block] = {
            "destinationCidrBlock": destination_cidr_block,
            "prefixListId": "",
            "state": "blackhole" if blackhole else "active",
            "type": "static",
        }

        if transit_gateway_attachment:
            transit_gateway_attachment_dict = {
                "transitGatewayAttachments": {
                    "resourceId": transit_gateway_attachment.resource_id,
                    "resourceType": transit_gateway_attachment.resource_type,
                    "transitGatewayAttachmentId": transit_gateway_attachment_id,
                }
            }
            transit_gateways_route_table.routes[destination_cidr_block].update(
                transit_gateway_attachment_dict
            )
        return transit_gateways_route_table.routes[destination_cidr_block]

    def delete_transit_gateway_route(
        self, transit_gateway_route_table_id, destination_cidr_block,
    ):
        transit_gateways_route_table = self.transit_gateways_route_tables[
            transit_gateway_route_table_id
        ]
        transit_gateways_route_table.routes[destination_cidr_block]["state"] = "deleted"
        return transit_gateways_route_table

    def search_transit_gateway_routes(
        self, transit_gateway_route_table_id, filters, max_results=None
    ):
        transit_gateway_route_table = self.transit_gateways_route_tables.get(
            transit_gateway_route_table_id
        )
        if not transit_gateway_route_table:
            return []

        attr_pairs = (
            ("type", "type"),
            ("state", "state"),
        )

        routes = transit_gateway_route_table.routes.copy()
        for key in transit_gateway_route_table.routes:
            for attrs in attr_pairs:
                values = filters.get(attrs[0]) or None
                if values:
                    if routes.get(key).get(attrs[1]) not in values:
                        routes.pop(key)
                        break
        if max_results:
            routes = routes[: int(max_results)]
        return routes

    def set_route_table_association(
        self, transit_gateway_attachment_id, transit_gateway_route_table_id
    ):
        self.transit_gateways_route_tables[
            transit_gateway_route_table_id
        ].route_table_association = {
            "resourceId": self.transit_gateway_attachments[
                transit_gateway_attachment_id
            ].resource_id,
            "resourceType": self.transit_gateway_attachments[
                transit_gateway_attachment_id
            ].resource_type,
            "state": "associated",
            "transitGatewayAttachmentId": transit_gateway_attachment_id,
        }

    def unset_route_table_association(self, tgw_rt_id):
        tgw_rt = self.transit_gateways_route_tables[tgw_rt_id]
        tgw_rt.route_table_association = {}

    def set_route_table_propagation(
        self, transit_gateway_attachment_id, transit_gateway_route_table_id
    ):
        self.transit_gateways_route_tables[
            transit_gateway_route_table_id
        ].route_table_propagation = {
            "resourceId": self.transit_gateway_attachments[
                transit_gateway_attachment_id
            ].resource_id,
            "resourceType": self.transit_gateway_attachments[
                transit_gateway_attachment_id
            ].resource_type,
            "state": "enabled",
            "transitGatewayAttachmentId": transit_gateway_attachment_id,
        }

    def unset_route_table_propagation(self, tgw_rt_id):
        tgw_rt = self.transit_gateways_route_tables[tgw_rt_id]
        tgw_rt.route_table_propagation = {}

    def disable_route_table_propagation(self, transit_gateway_route_table_id):
        self.transit_gateways_route_tables[
            transit_gateway_route_table_id
        ].route_table_propagation = {}

    def get_all_transit_gateway_route_table_associations(
        self, transit_gateway_route_table_id=None, filters=None
    ):
        transit_gateway_route_tables = list(self.transit_gateways_route_tables.values())

        if transit_gateway_route_tables:
            transit_gateway_route_tables = [
                transit_gateway_route_table
                for transit_gateway_route_table in transit_gateway_route_tables
                if transit_gateway_route_table.id in transit_gateway_route_table_id
            ]

        attr_pairs = (
            ("resource-id", "route_table_association", "resourceId"),
            ("resource-type", "route_table_association", "resourceType"),
            (
                "transit-gateway-attachment-id",
                "route_table_association",
                "transitGatewayAttachmentId",
            ),
        )

        result = transit_gateway_route_tables
        if filters:
            result = filter_resources(transit_gateway_route_tables, filters, attr_pairs)
        return result

    def get_all_transit_gateway_route_table_propagations(
        self, transit_gateway_route_table_id=None, filters=None
    ):
        transit_gateway_route_tables = list(self.transit_gateways_route_tables.values())

        if transit_gateway_route_tables:
            transit_gateway_route_tables = [
                transit_gateway_route_table
                for transit_gateway_route_table in transit_gateway_route_tables
                if transit_gateway_route_table.id in transit_gateway_route_table_id
            ]

        attr_pairs = (
            ("resource-id", "route_table_propagation", "resourceId"),
            ("resource-type", "route_table_propagation", "resourceType"),
            (
                "transit-gateway-attachment-id",
                "route_table_propagation",
                "transitGatewayAttachmentId",
            ),
        )

        result = transit_gateway_route_tables
        if filters:
            result = filter_resources(transit_gateway_route_tables, filters, attr_pairs)
        return result


class TransitGatewayAttachment(TaggedEC2Resource):
    def __init__(
        self, backend, resource_id, resource_type, transit_gateway_id, tags=None
    ):
        self.ec2_backend = backend
        self.association = {}
        self.propagation = {}
        self.resource_id = resource_id
        self.resource_type = resource_type

        self.id = random_transit_gateway_attachment_id()
        self.transit_gateway_id = transit_gateway_id

        self.state = "available"
        self.add_tags(tags or {})

        self._created_at = datetime.utcnow()
        self.owner_id = self.resource_owner_id

    @property
    def create_time(self):
        return iso_8601_datetime_with_milliseconds(self._created_at)

    @property
    def resource_owner_id(self):
        return ACCOUNT_ID

    @property
    def transit_gateway_owner_id(self):
        return ACCOUNT_ID


class TransitGatewayVpcAttachment(TransitGatewayAttachment):
    DEFAULT_OPTIONS = {
        "ApplianceModeSupport": "disable",
        "DnsSupport": "enable",
        "Ipv6Support": "disable",
    }

    def __init__(
        self, backend, transit_gateway_id, vpc_id, subnet_ids, tags=None, options=None
    ):
        super().__init__(
            backend=backend,
            transit_gateway_id=transit_gateway_id,
            resource_id=vpc_id,
            resource_type="vpc",
            tags=tags,
        )

        self.vpc_id = vpc_id
        self.subnet_ids = subnet_ids
        self.options = merge_multiple_dicts(self.DEFAULT_OPTIONS, options or {})


class TransitGatewayPeeringAttachment(TransitGatewayAttachment):
    def __init__(
        self,
        backend,
        transit_gateway_id=None,
        peer_transit_gateway_id=None,
        peer_region=None,
        peer_account_id=None,
        tags=None,
        region_name=None,
    ):
        super().__init__(
            backend=backend,
            transit_gateway_id=transit_gateway_id,
            resource_id=peer_transit_gateway_id,
            resource_type="peering",
            tags=tags,
        )

        self.accepter_tgw_info = {
            "ownerId": peer_account_id,
            "region": peer_region,
            "transitGatewayId": peer_transit_gateway_id,
        }
        self.requester_tgw_info = {
            "ownerId": self.owner_id,
            "region": region_name,
            "transitGatewayId": transit_gateway_id,
        }
        self.status = PeeringConnectionStatus()

    @property
    def resource_owner_id(self):
        return ACCOUNT_ID


class TransitGatewayAttachmentBackend(object):
    def __init__(self):
        self.transit_gateway_attachments = {}
        super().__init__()

    def create_transit_gateway_vpn_attachment(
        self, vpn_id, transit_gateway_id, tags=None
    ):
        transit_gateway_vpn_attachment = TransitGatewayAttachment(
            self,
            resource_id=vpn_id,
            resource_type="vpn",
            transit_gateway_id=transit_gateway_id,
            tags=tags,
        )
        self.transit_gateway_attachments[
            transit_gateway_vpn_attachment.id
        ] = transit_gateway_vpn_attachment
        return transit_gateway_vpn_attachment

    def create_transit_gateway_vpc_attachment(
        self, transit_gateway_id, vpc_id, subnet_ids, tags=None, options=None
    ):
        transit_gateway_vpc_attachment = TransitGatewayVpcAttachment(
            self,
            transit_gateway_id=transit_gateway_id,
            tags=tags,
            vpc_id=vpc_id,
            subnet_ids=subnet_ids,
            options=options,
        )
        self.transit_gateway_attachments[
            transit_gateway_vpc_attachment.id
        ] = transit_gateway_vpc_attachment
        return transit_gateway_vpc_attachment

    def describe_transit_gateway_attachments(
        self, transit_gateways_attachment_ids=None, filters=None, max_results=0
    ):
        transit_gateway_attachments = list(self.transit_gateway_attachments.values())

        attr_pairs = (
            ("resource-id", "resource_id"),
            ("resource-type", "resource_type"),
            ("transit-gateway-id", "transit_gateway_id"),
        )

        if (
            not transit_gateways_attachment_ids == []
            and transit_gateways_attachment_ids is not None
        ):
            transit_gateway_attachments = [
                transit_gateways_attachment
                for transit_gateways_attachment in transit_gateway_attachments
                if transit_gateways_attachment.id in transit_gateways_attachment_ids
            ]

        result = transit_gateway_attachments
        if filters:
            result = filter_resources(transit_gateway_attachments, filters, attr_pairs)
        return result

    def describe_transit_gateway_vpc_attachments(
        self, transit_gateways_attachment_ids=None, filters=None, max_results=0
    ):
        transit_gateway_attachments = list(self.transit_gateway_attachments.values())

        attr_pairs = (
            ("state", "state"),
            ("transit-gateway-attachment-id", "id"),
            ("transit-gateway-id", "transit_gateway_id"),
            ("vpc-id", "resource_id"),
        )

        if (
            not transit_gateways_attachment_ids == []
            and transit_gateways_attachment_ids is not None
        ):
            transit_gateway_attachments = [
                transit_gateways_attachment
                for transit_gateways_attachment in transit_gateway_attachments
                if transit_gateways_attachment.id in transit_gateways_attachment_ids
            ]

        result = transit_gateway_attachments
        if filters:
            result = filter_resources(transit_gateway_attachments, filters, attr_pairs)
        return result

    def delete_transit_gateway_vpc_attachment(self, transit_gateway_attachment_id=None):
        transit_gateway_attachment = self.transit_gateway_attachments.pop(
            transit_gateway_attachment_id
        )
        transit_gateway_attachment.state = "deleted"
        return transit_gateway_attachment

    def modify_transit_gateway_vpc_attachment(
        self,
        add_subnet_ids=None,
        options=None,
        remove_subnet_ids=None,
        transit_gateway_attachment_id=None,
    ):

        tgw_attachment = self.transit_gateway_attachments[transit_gateway_attachment_id]
        if remove_subnet_ids:
            tgw_attachment.subnet_ids = [
                id for id in tgw_attachment.subnet_ids if id not in remove_subnet_ids
            ]

        if options:
            tgw_attachment.options.update(options)

        if add_subnet_ids:
            for subnet_id in add_subnet_ids:
                tgw_attachment.subnet_ids.append(subnet_id)

        return tgw_attachment

    def set_attachment_association(
        self, transit_gateway_attachment_id=None, transit_gateway_route_table_id=None
    ):
        self.transit_gateway_attachments[transit_gateway_attachment_id].association = {
            "state": "associated",
            "transitGatewayRouteTableId": transit_gateway_route_table_id,
        }

    def unset_attachment_association(self, tgw_attach_id):
        self.transit_gateway_attachments.get(tgw_attach_id).association = {}

    def set_attachment_propagation(
        self, transit_gateway_attachment_id=None, transit_gateway_route_table_id=None
    ):
        self.transit_gateway_attachments[transit_gateway_attachment_id].propagation = {
            "state": "enabled",
            "transitGatewayRouteTableId": transit_gateway_route_table_id,
        }

    def unset_attachment_propagation(self, tgw_attach_id):
        self.transit_gateway_attachments.get(tgw_attach_id).propagation = {}

    def disable_attachment_propagation(self, transit_gateway_attachment_id=None):
        self.transit_gateway_attachments[transit_gateway_attachment_id].propagation[
            "state"
        ] = "disabled"

    def create_transit_gateway_peering_attachment(
        self,
        transit_gateway_id,
        peer_transit_gateway_id,
        peer_region,
        peer_account_id,
        tags,
    ):
        transit_gateway_peering_attachment = TransitGatewayPeeringAttachment(
            self,
            transit_gateway_id=transit_gateway_id,
            peer_transit_gateway_id=peer_transit_gateway_id,
            peer_region=peer_region,
            peer_account_id=peer_account_id,
            tags=tags,
            region_name=self.region_name,
        )
        transit_gateway_peering_attachment.status.accept()
        transit_gateway_peering_attachment.state = "available"
        self.transit_gateway_attachments[
            transit_gateway_peering_attachment.id
        ] = transit_gateway_peering_attachment
        return transit_gateway_peering_attachment

    def describe_transit_gateway_peering_attachments(
        self, transit_gateways_attachment_ids=None, filters=None, max_results=0
    ):
        transit_gateway_attachments = list(self.transit_gateway_attachments.values())

        attr_pairs = (
            ("state", "state"),
            ("transit-gateway-attachment-id", "id"),
            ("local-owner-id", "requester_tgw_info", "ownerId"),
            ("remote-owner-id", "accepter_tgw_info", "ownerId"),
        )

        if transit_gateways_attachment_ids:
            transit_gateway_attachments = [
                transit_gateways_attachment
                for transit_gateways_attachment in transit_gateway_attachments
                if transit_gateways_attachment.id in transit_gateways_attachment_ids
            ]

        if filters:
            transit_gateway_attachments = filter_resources(
                transit_gateway_attachments, filters, attr_pairs
            )
            transit_gateway_attachments = describe_tag_filter(
                filters, transit_gateway_attachments
            )
        return transit_gateway_attachments

    def accept_transit_gateway_peering_attachment(self, transit_gateway_attachment_id):
        transit_gateway_attachment = self.transit_gateway_attachments[
            transit_gateway_attachment_id
        ]
        transit_gateway_attachment.state = "available"
        transit_gateway_attachment.status.accept()
        return transit_gateway_attachment

    def reject_transit_gateway_peering_attachment(self, transit_gateway_attachment_id):
        transit_gateway_attachment = self.transit_gateway_attachments[
            transit_gateway_attachment_id
        ]
        transit_gateway_attachment.state = "rejected"
        transit_gateway_attachment.status.reject()
        return transit_gateway_attachment

    def delete_transit_gateway_peering_attachment(self, transit_gateway_attachment_id):
        transit_gateway_attachment = self.transit_gateway_attachments[
            transit_gateway_attachment_id
        ]
        transit_gateway_attachment.state = "deleted"
        transit_gateway_attachment.status.deleted()
        return transit_gateway_attachment


class TransitGatewayRelations(object):
    # this class is for TransitGatewayAssociation and TransitGatewayPropagation
    def __init__(
        self,
        backend,
        transit_gateway_attachment_id=None,
        transit_gateway_route_table_id=None,
        state=None,
    ):
        self.ec2_backend = backend
        self.transit_gateway_attachment_id = transit_gateway_attachment_id
        self.transit_gateway_route_table_id = transit_gateway_route_table_id
        self.resource_id = backend.transit_gateway_attachments[
            transit_gateway_attachment_id
        ].resource_id
        self.resource_type = backend.transit_gateway_attachments[
            transit_gateway_attachment_id
        ].resource_type
        self.state = state


class TransitGatewayRelationsBackend(object):
    def __init__(self):
        self.transit_gateway_associations = {}
        self.transit_gateway_propagations = {}
        super().__init__()

    def associate_transit_gateway_route_table(
        self, transit_gateway_attachment_id=None, transit_gateway_route_table_id=None
    ):
        transit_gateway_association = TransitGatewayRelations(
            self,
            transit_gateway_attachment_id,
            transit_gateway_route_table_id,
            state="associated",
        )
        self.set_route_table_association(
            transit_gateway_attachment_id, transit_gateway_route_table_id
        )
        self.set_attachment_association(
            transit_gateway_attachment_id, transit_gateway_route_table_id
        )
        self.transit_gateway_associations[
            transit_gateway_attachment_id
        ] = transit_gateway_association

        return transit_gateway_association

    def enable_transit_gateway_route_table_propagation(
        self, transit_gateway_attachment_id=None, transit_gateway_route_table_id=None
    ):
        transit_gateway_propagation = TransitGatewayRelations(
            self,
            transit_gateway_attachment_id,
            transit_gateway_route_table_id,
            state="enabled",
        )
        self.set_route_table_propagation(
            transit_gateway_attachment_id, transit_gateway_route_table_id
        )
        self.set_attachment_propagation(
            transit_gateway_attachment_id, transit_gateway_route_table_id
        )
        self.transit_gateway_propagations[
            transit_gateway_attachment_id
        ] = transit_gateway_propagation

        return transit_gateway_propagation

    def disable_transit_gateway_route_table_propagation(
        self, transit_gateway_attachment_id=None, transit_gateway_route_table_id=None
    ):
        self.disable_route_table_propagation(
            transit_gateway_route_table_id=transit_gateway_route_table_id
        )
        self.disable_attachment_propagation(
            transit_gateway_attachment_id=transit_gateway_attachment_id
        )
        self.transit_gateway_propagations[
            transit_gateway_attachment_id
        ].state = "disabled"
        transit_gateway_propagation = self.transit_gateway_propagations.pop(
            transit_gateway_attachment_id
        )

        return transit_gateway_propagation

    def disassociate_transit_gateway_route_table(self, tgw_attach_id, tgw_rt_id):
        tgw_association = self.transit_gateway_associations.pop(tgw_attach_id)
        tgw_association.state = "disassociated"

        self.unset_route_table_association(tgw_rt_id)
        self.unset_attachment_association(tgw_attach_id)

        return tgw_association


class NatGateway(CloudFormationModel, TaggedEC2Resource):
    def __init__(
        self,
        backend,
        subnet_id,
        allocation_id,
        tags=None,
        connectivity_type="public",
        address_set=None,
    ):
        # public properties
        self.id = random_nat_gateway_id()
        self.subnet_id = subnet_id
        self.address_set = address_set or []
        self.state = "available"
        self.private_ip = random_private_ip()
        self.connectivity_type = connectivity_type

        # protected properties
        self._created_at = datetime.utcnow()
        self.ec2_backend = backend
        # NOTE: this is the core of NAT Gateways creation
        self._eni = self.ec2_backend.create_network_interface(
            backend.get_subnet(self.subnet_id), self.private_ip
        )

        # associate allocation with ENI
        if allocation_id and connectivity_type != "private":
            self.ec2_backend.associate_address(
                eni=self._eni, allocation_id=allocation_id
            )
        self.add_tags(tags or {})
        self.vpc_id = self.ec2_backend.get_subnet(subnet_id).vpc_id

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def create_time(self):
        return iso_8601_datetime_with_milliseconds(self._created_at)

    @property
    def network_interface_id(self):
        return self._eni.id

    @property
    def public_ip(self):
        if self.allocation_id:
            eips = self._backend.address_by_allocation([self.allocation_id])
        return eips[0].public_ip if self.allocation_id else None

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-natgateway.html
        return "AWS::EC2::NatGateway"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        ec2_backend = ec2_backends[region_name]
        nat_gateway = ec2_backend.create_nat_gateway(
            cloudformation_json["Properties"]["SubnetId"],
            cloudformation_json["Properties"]["AllocationId"],
        )
        return nat_gateway


class NatGatewayBackend(object):
    def __init__(self):
        self.nat_gateways = {}
        super().__init__()

    def describe_nat_gateways(self, filters, nat_gateway_ids):
        nat_gateways = list(self.nat_gateways.values())

        if nat_gateway_ids:
            nat_gateways = [item for item in nat_gateways if item.id in nat_gateway_ids]

        if filters is not None:
            if filters.get("nat-gateway-id") is not None:
                nat_gateways = [
                    nat_gateway
                    for nat_gateway in nat_gateways
                    if nat_gateway.id in filters["nat-gateway-id"]
                ]
            if filters.get("vpc-id") is not None:
                nat_gateways = [
                    nat_gateway
                    for nat_gateway in nat_gateways
                    if nat_gateway.vpc_id in filters["vpc-id"]
                ]
            if filters.get("subnet-id") is not None:
                nat_gateways = [
                    nat_gateway
                    for nat_gateway in nat_gateways
                    if nat_gateway.subnet_id in filters["subnet-id"]
                ]
            if filters.get("state") is not None:
                nat_gateways = [
                    nat_gateway
                    for nat_gateway in nat_gateways
                    if nat_gateway.state in filters["state"]
                ]

        return nat_gateways

    def create_nat_gateway(
        self, subnet_id, allocation_id, tags=None, connectivity_type="public"
    ):
        nat_gateway = NatGateway(
            self, subnet_id, allocation_id, tags, connectivity_type
        )
        address_set = {}
        if allocation_id:
            eips = self.address_by_allocation([allocation_id])
            eip = eips[0] if len(eips) > 0 else None
            if eip:
                address_set["allocationId"] = allocation_id
                address_set["publicIp"] = eip.public_ip or None
        address_set["networkInterfaceId"] = nat_gateway._eni.id
        address_set["privateIp"] = nat_gateway._eni.private_ip_address
        nat_gateway.address_set.append(address_set)
        self.nat_gateways[nat_gateway.id] = nat_gateway
        return nat_gateway

    def delete_nat_gateway(self, nat_gateway_id):
        nat_gw = self.nat_gateways.get(nat_gateway_id)
        nat_gw.state = "deleted"
        return nat_gw


class LaunchTemplateVersion(object):
    def __init__(self, template, number, data, description):
        self.template = template
        self.number = number
        self.data = data
        self.description = description
        self.create_time = utc_date_and_time()

    @property
    def image_id(self):
        return self.data.get("ImageId", "")

    @property
    def instance_type(self):
        return self.data.get("InstanceType", "")

    @property
    def security_groups(self):
        return self.data.get("SecurityGroups", [])

    @property
    def user_data(self):
        return self.data.get("UserData", "")


class LaunchTemplate(TaggedEC2Resource):
    def __init__(self, backend, name, template_data, version_description):
        self.ec2_backend = backend
        self.name = name
        self.id = random_launch_template_id()
        self.create_time = utc_date_and_time()

        self.versions = []
        self.create_version(template_data, version_description)
        self.default_version_number = 1

    def create_version(self, data, description):
        num = len(self.versions) + 1
        version = LaunchTemplateVersion(self, num, data, description)
        self.versions.append(version)
        return version

    def is_default(self, version):
        return self.default_version == version.number

    def get_version(self, num):
        return self.versions[num - 1]

    def default_version(self):
        return self.versions[self.default_version_number - 1]

    def latest_version(self):
        return self.versions[-1]

    @property
    def latest_version_number(self):
        return self.latest_version().number

    def get_filter_value(self, filter_name):
        if filter_name == "launch-template-name":
            return self.name
        else:
            return super().get_filter_value(filter_name, "DescribeLaunchTemplates")


class LaunchTemplateBackend(object):
    def __init__(self):
        self.launch_template_name_to_ids = {}
        self.launch_templates = OrderedDict()
        self.launch_template_insert_order = []
        super().__init__()

    def create_launch_template(self, name, description, template_data):
        if name in self.launch_template_name_to_ids:
            raise InvalidLaunchTemplateNameError()
        template = LaunchTemplate(self, name, template_data, description)
        self.launch_templates[template.id] = template
        self.launch_template_name_to_ids[template.name] = template.id
        self.launch_template_insert_order.append(template.id)
        return template

    def get_launch_template(self, template_id):
        return self.launch_templates[template_id]

    def get_launch_template_by_name(self, name):
        return self.get_launch_template(self.launch_template_name_to_ids[name])

    def describe_launch_templates(
        self, template_names=None, template_ids=None, filters=None
    ):
        if template_names and not template_ids:
            template_ids = []
            for name in template_names:
                template_ids.append(self.launch_template_name_to_ids[name])

        if template_ids:
            templates = [self.launch_templates[tid] for tid in template_ids]
        else:
            templates = list(self.launch_templates.values())

        return generic_filter(filters, templates)


class IamInstanceProfileAssociation(CloudFormationModel):
    def __init__(self, ec2_backend, association_id, instance, iam_instance_profile):
        self.ec2_backend = ec2_backend
        self.id = association_id
        self.instance = instance
        self.iam_instance_profile = iam_instance_profile
        self.state = "associated"


class IamInstanceProfileAssociationBackend(object):
    def __init__(self):
        self.iam_instance_profile_associations = {}
        super().__init__()

    def associate_iam_instance_profile(
        self,
        instance_id,
        iam_instance_profile_name=None,
        iam_instance_profile_arn=None,
    ):
        iam_association_id = random_iam_instance_profile_association_id()

        instance_profile = filter_iam_instance_profiles(
            iam_instance_profile_arn, iam_instance_profile_name
        )

        if instance_id in self.iam_instance_profile_associations.keys():
            raise IncorrectStateIamProfileAssociationError(instance_id)

        iam_instance_profile_associations = IamInstanceProfileAssociation(
            self,
            iam_association_id,
            self.get_instance(instance_id) if instance_id else None,
            instance_profile,
        )
        # Regarding to AWS there can be only one association with ec2.
        self.iam_instance_profile_associations[
            instance_id
        ] = iam_instance_profile_associations
        return iam_instance_profile_associations

    def describe_iam_instance_profile_associations(
        self, association_ids, filters=None, max_results=100, next_token=None
    ):
        associations_list = []
        if association_ids:
            for association in self.iam_instance_profile_associations.values():
                if association.id in association_ids:
                    associations_list.append(association)
        else:
            # That's mean that no association id were given. Showing all.
            associations_list.extend(self.iam_instance_profile_associations.values())

        associations_list = filter_iam_instance_profile_associations(
            associations_list, filters
        )

        starting_point = int(next_token or 0)
        ending_point = starting_point + int(max_results or 100)
        associations_page = associations_list[starting_point:ending_point]
        new_next_token = (
            str(ending_point) if ending_point < len(associations_list) else None
        )

        return associations_page, new_next_token

    def disassociate_iam_instance_profile(self, association_id):
        iam_instance_profile_associations = None
        for association_key in self.iam_instance_profile_associations.keys():
            if (
                self.iam_instance_profile_associations[association_key].id
                == association_id
            ):
                iam_instance_profile_associations = self.iam_instance_profile_associations[
                    association_key
                ]
                del self.iam_instance_profile_associations[association_key]
                # Deleting once and avoiding `RuntimeError: dictionary changed size during iteration`
                break

        if not iam_instance_profile_associations:
            raise InvalidAssociationIDIamProfileAssociationError(association_id)

        return iam_instance_profile_associations

    def replace_iam_instance_profile_association(
        self,
        association_id,
        iam_instance_profile_name=None,
        iam_instance_profile_arn=None,
    ):
        instance_profile = filter_iam_instance_profiles(
            iam_instance_profile_arn, iam_instance_profile_name
        )

        iam_instance_profile_association = None
        for association_key in self.iam_instance_profile_associations.keys():
            if (
                self.iam_instance_profile_associations[association_key].id
                == association_id
            ):
                self.iam_instance_profile_associations[
                    association_key
                ].iam_instance_profile = instance_profile
                iam_instance_profile_association = self.iam_instance_profile_associations[
                    association_key
                ]
                break

        if not iam_instance_profile_association:
            raise InvalidAssociationIDIamProfileAssociationError(association_id)

        return iam_instance_profile_association


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
):
    def __init__(self, region_name):
        self.region_name = region_name
        super().__init__()

        # Default VPC exists by default, which is the current behavior
        # of EC2-VPC. See for detail:
        #
        #   docs.aws.amazon.com/AmazonVPC/latest/UserGuide/default-vpc.html
        #
        if not self.vpcs:
            vpc = self.create_vpc("172.31.0.0/16")
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

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

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
