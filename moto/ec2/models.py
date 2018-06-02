from __future__ import unicode_literals

import copy
import itertools
import ipaddress
import json
import os
import re
import six
import warnings
from pkg_resources import resource_filename

import boto.ec2

from collections import defaultdict
from datetime import datetime
from boto.ec2.instance import Instance as BotoInstance, Reservation
from boto.ec2.blockdevicemapping import BlockDeviceMapping, BlockDeviceType
from boto.ec2.spotinstancerequest import SpotInstanceRequest as BotoSpotRequest
from boto.ec2.launchspecification import LaunchSpecification

from moto.compat import OrderedDict
from moto.core import BaseBackend
from moto.core.models import Model, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds, camelcase_to_underscores
from .exceptions import (
    CidrLimitExceeded,
    DependencyViolationError,
    EC2ClientError,
    FilterNotImplementedError,
    GatewayNotAttachedError,
    InvalidAddressError,
    InvalidAllocationIdError,
    InvalidAMIIdError,
    InvalidAMIAttributeItemValueError,
    InvalidAssociationIdError,
    InvalidCIDRSubnetError,
    InvalidCustomerGatewayIdError,
    InvalidDHCPOptionsIdError,
    InvalidDomainError,
    InvalidID,
    InvalidInstanceIdError,
    InvalidInternetGatewayIdError,
    InvalidKeyPairDuplicateError,
    InvalidKeyPairNameError,
    InvalidNetworkAclIdError,
    InvalidNetworkAttachmentIdError,
    InvalidNetworkInterfaceIdError,
    InvalidParameterValueError,
    InvalidParameterValueErrorTagNull,
    InvalidPermissionNotFoundError,
    InvalidPermissionDuplicateError,
    InvalidRouteTableIdError,
    InvalidRouteError,
    InvalidSecurityGroupDuplicateError,
    InvalidSecurityGroupNotFoundError,
    InvalidSnapshotIdError,
    InvalidSubnetIdError,
    InvalidVolumeIdError,
    InvalidVolumeAttachmentError,
    InvalidVpcCidrBlockAssociationIdError,
    InvalidVPCPeeringConnectionIdError,
    InvalidVPCPeeringConnectionStateTransitionError,
    InvalidVPCIdError,
    InvalidVpnGatewayIdError,
    InvalidVpnConnectionIdError,
    MalformedAMIIdError,
    MalformedDHCPOptionsIdError,
    MissingParameterError,
    MotoNotImplementedError,
    OperationNotPermitted,
    ResourceAlreadyAssociatedError,
    RulesPerSecurityGroupLimitExceededError,
    TagLimitExceeded)
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
    random_ip,
    random_ipv6_cidr,
    random_nat_gateway_id,
    random_key_pair,
    random_private_ip,
    random_public_ip,
    random_reservation_id,
    random_route_table_id,
    generate_route_id,
    split_route_id,
    random_security_group_id,
    random_snapshot_id,
    random_spot_fleet_request_id,
    random_spot_request_id,
    random_subnet_id,
    random_subnet_association_id,
    random_volume_id,
    random_vpc_id,
    random_vpc_cidr_association_id,
    random_vpc_peering_connection_id,
    generic_filter,
    is_valid_resource_id,
    get_prefix,
    simple_aws_filter_to_re,
    is_valid_cidr,
    filter_internet_gateways,
    filter_reservations,
    random_network_acl_id,
    random_network_acl_subnet_association_id,
    random_vpn_gateway_id,
    random_vpn_connection_id,
    random_customer_gateway_id,
    is_tag_filter,
    tag_filter_matches,
)

INSTANCE_TYPES = json.load(
    open(resource_filename(__name__, 'resources/instance_types.json'), 'r')
)
AMIS = json.load(
    open(os.environ.get('MOTO_AMIS_PATH') or resource_filename(
         __name__, 'resources/amis.json'), 'r')
)


def utc_date_and_time():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')


def validate_resource_ids(resource_ids):
    for resource_id in resource_ids:
        if not is_valid_resource_id(resource_id):
            raise InvalidID(resource_id=resource_id)
    return True


class InstanceState(object):
    def __init__(self, name='pending', code=0):
        self.name = name
        self.code = code


class StateReason(object):
    def __init__(self, message="", code=""):
        self.message = message
        self.code = code


class TaggedEC2Resource(BaseModel):
    def get_tags(self, *args, **kwargs):
        tags = self.ec2_backend.describe_tags(
            filters={'resource-id': [self.id]})
        return tags

    def add_tag(self, key, value):
        self.ec2_backend.create_tags([self.id], {key: value})

    def add_tags(self, tag_map):
        for key, value in tag_map.items():
            self.ec2_backend.create_tags([self.id], {key: value})

    def get_filter_value(self, filter_name, method_name=None):
        tags = self.get_tags()

        if filter_name.startswith('tag:'):
            tagname = filter_name.replace('tag:', '', 1)
            for tag in tags:
                if tag['key'] == tagname:
                    return tag['value']

            return ''
        elif filter_name == 'tag-key':
            return [tag['key'] for tag in tags]
        elif filter_name == 'tag-value':
            return [tag['value'] for tag in tags]
        else:
            raise FilterNotImplementedError(filter_name, method_name)


class NetworkInterface(TaggedEC2Resource):
    def __init__(self, ec2_backend, subnet, private_ip_address, device_index=0,
                 public_ip_auto_assign=True, group_ids=None):
        self.ec2_backend = ec2_backend
        self.id = random_eni_id()
        self.device_index = device_index
        self.private_ip_address = private_ip_address
        self.subnet = subnet
        self.instance = None
        self.attachment_id = None

        self.public_ip = None
        self.public_ip_auto_assign = public_ip_auto_assign
        self.start()

        self.attachments = []

        # Local set to the ENI. When attached to an instance, @property group_set
        #   returns groups for both self and the attached instance.
        self._group_set = []

        group = None
        if group_ids:
            for group_id in group_ids:
                group = self.ec2_backend.get_security_group_from_id(group_id)
                if not group:
                    # Create with specific group ID.
                    group = SecurityGroup(
                        self.ec2_backend, group_id, group_id, group_id, vpc_id=subnet.vpc_id)
                    self.ec2_backend.groups[subnet.vpc_id][group_id] = group
                if group:
                    self._group_set.append(group)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        security_group_ids = properties.get('SecurityGroups', [])

        ec2_backend = ec2_backends[region_name]
        subnet_id = properties.get('SubnetId')
        if subnet_id:
            subnet = ec2_backend.get_subnet(subnet_id)
        else:
            subnet = None

        private_ip_address = properties.get('PrivateIpAddress', None)

        network_interface = ec2_backend.create_network_interface(
            subnet,
            private_ip_address,
            group_ids=security_group_ids
        )
        return network_interface

    def stop(self):
        if self.public_ip_auto_assign:
            self.public_ip = None

    def start(self):
        self.check_auto_public_ip()

    def check_auto_public_ip(self):
        if self.public_ip_auto_assign:
            self.public_ip = random_public_ip()

    @property
    def group_set(self):
        if self.instance and self.instance.security_groups:
            return set(self._group_set) | set(self.instance.security_groups)
        else:
            return self._group_set

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'PrimaryPrivateIpAddress':
            return self.private_ip_address
        elif attribute_name == 'SecondaryPrivateIpAddresses':
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "SecondaryPrivateIpAddresses" ]"')
        raise UnformattedGetAttTemplateException()

    @property
    def physical_resource_id(self):
        return self.id

    def get_filter_value(self, filter_name):
        if filter_name == 'network-interface-id':
            return self.id
        elif filter_name in ('addresses.private-ip-address', 'private-ip-address'):
            return self.private_ip_address
        elif filter_name == 'subnet-id':
            return self.subnet.id
        elif filter_name == 'vpc-id':
            return self.subnet.vpc_id
        elif filter_name == 'group-id':
            return [group.id for group in self._group_set]
        elif filter_name == 'availability-zone':
            return self.subnet.availability_zone
        else:
            return super(NetworkInterface, self).get_filter_value(
                filter_name, 'DescribeNetworkInterfaces')


class NetworkInterfaceBackend(object):
    def __init__(self):
        self.enis = {}
        super(NetworkInterfaceBackend, self).__init__()

    def create_network_interface(self, subnet, private_ip_address, group_ids=None, **kwargs):
        eni = NetworkInterface(
            self, subnet, private_ip_address, group_ids=group_ids, **kwargs)
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
        enis = self.enis.values()

        if filters:
            for (_filter, _filter_value) in filters.items():
                if _filter == 'network-interface-id':
                    _filter = 'id'
                    enis = [eni for eni in enis if getattr(
                        eni, _filter) in _filter_value]
                elif _filter == 'group-id':
                    original_enis = enis
                    enis = []
                    for eni in original_enis:
                        for group in eni.group_set:
                            if group.id in _filter_value:
                                enis.append(eni)
                                break
                else:
                    self.raise_not_implemented_error(
                        "The filter '{0}' for DescribeNetworkInterfaces".format(_filter))
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

    def modify_network_interface_attribute(self, eni_id, group_id):
        eni = self.get_network_interface(eni_id)
        group = self.get_security_group_from_id(group_id)
        eni._group_set = [group]

    def get_all_network_interfaces(self, eni_ids=None, filters=None):
        enis = self.enis.values()

        if eni_ids:
            enis = [eni for eni in enis if eni.id in eni_ids]
            if len(enis) != len(eni_ids):
                invalid_id = list(set(eni_ids).difference(
                    set([eni.id for eni in enis])))[0]
                raise InvalidNetworkInterfaceIdError(invalid_id)

        return generic_filter(filters, enis)


class Instance(TaggedEC2Resource, BotoInstance):
    def __init__(self, ec2_backend, image_id, user_data, security_groups, **kwargs):
        super(Instance, self).__init__()
        self.ec2_backend = ec2_backend
        self.id = random_instance_id()
        self.image_id = image_id
        self._state = InstanceState("running", 16)
        self._reason = ""
        self._state_reason = StateReason()
        self.user_data = user_data
        self.security_groups = security_groups
        self.instance_type = kwargs.get("instance_type", "m1.small")
        self.region_name = kwargs.get("region_name", "us-east-1")
        placement = kwargs.get("placement", None)
        self.vpc_id = None
        self.subnet_id = kwargs.get("subnet_id")
        in_ec2_classic = not bool(self.subnet_id)
        self.key_name = kwargs.get("key_name")
        self.ebs_optimized = kwargs.get("ebs_optimized", False)
        self.source_dest_check = "true"
        self.launch_time = utc_date_and_time()
        self.disable_api_termination = kwargs.get("disable_api_termination", False)
        self._spot_fleet_id = kwargs.get("spot_fleet_id", None)
        associate_public_ip = kwargs.get("associate_public_ip", False)
        if in_ec2_classic:
            # If we are in EC2-Classic, autoassign a public IP
            associate_public_ip = True

        amis = self.ec2_backend.describe_images(filters={'image-id': image_id})
        ami = amis[0] if amis else None
        if ami is None:
            warnings.warn('Could not find AMI with image-id:{0}, '
                          'in the near future this will '
                          'cause an error.\n'
                          'Use ec2_backend.describe_images() to'
                          'find suitable image for your test'.format(image_id),
                          PendingDeprecationWarning)

        self.platform = ami.platform if ami else None
        self.virtualization_type = ami.virtualization_type if ami else 'paravirtual'
        self.architecture = ami.architecture if ami else 'x86_64'

        # handle weird bug around user_data -- something grabs the repr(), so
        # it must be clean
        if isinstance(self.user_data, list) and len(self.user_data) > 0:
            if six.PY3 and isinstance(self.user_data[0], six.binary_type):
                # string will have a "b" prefix -- need to get rid of it
                self.user_data[0] = self.user_data[0].decode('utf-8')
            elif six.PY2 and isinstance(self.user_data[0], six.text_type):
                # string will have a "u" prefix -- need to get rid of it
                self.user_data[0] = self.user_data[0].encode('utf-8')

        if self.subnet_id:
            subnet = ec2_backend.get_subnet(self.subnet_id)
            self.vpc_id = subnet.vpc_id
            self._placement.zone = subnet.availability_zone

            if associate_public_ip is None:
                # Mapping public ip hasnt been explicitly enabled or disabled
                associate_public_ip = subnet.map_public_ip_on_launch == 'true'
        elif placement:
            self._placement.zone = placement
        else:
            self._placement.zone = ec2_backend.region_name + 'a'

        self.block_device_mapping = BlockDeviceMapping()

        self._private_ips = set()
        self.prep_nics(
            kwargs.get("nics", {}),
            private_ip=kwargs.get("private_ip"),
            associate_public_ip=associate_public_ip
        )

    def __del__(self):
        try:
            subnet = self.ec2_backend.get_subnet(self.subnet_id)
            for ip in self._private_ips:
                subnet.del_subnet_ip(ip)
        except Exception:
            # Its not "super" critical we clean this up, as reset will do this
            # worst case we'll get IP address exaustion... rarely
            pass

    def setup_defaults(self):
        # Default have an instance with root volume should you not wish to
        # override with attach volume cmd.
        volume = self.ec2_backend.create_volume(8, 'us-east-1a')
        self.ec2_backend.attach_volume(volume.id, self.id, '/dev/sda1')

    def teardown_defaults(self):
        volume_id = self.block_device_mapping['/dev/sda1'].volume_id
        self.ec2_backend.detach_volume(volume_id, self.id, '/dev/sda1')
        self.ec2_backend.delete_volume(volume_id)

    @property
    def get_block_device_mapping(self):
        return self.block_device_mapping.items()

    @property
    def private_ip(self):
        return self.nics[0].private_ip_address

    @property
    def private_dns(self):
        formatted_ip = self.private_ip.replace('.', '-')
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
            formatted_ip = self.public_ip.replace('.', '-')
            if self.region_name == "us-east-1":
                return "ec2-{0}.compute-1.amazonaws.com".format(formatted_ip)
            else:
                return "ec2-{0}.{1}.compute.amazonaws.com".format(formatted_ip, self.region_name)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        ec2_backend = ec2_backends[region_name]
        security_group_ids = properties.get('SecurityGroups', [])
        group_names = [ec2_backend.get_security_group_from_id(
            group_id).name for group_id in security_group_ids]

        reservation = ec2_backend.add_instances(
            image_id=properties['ImageId'],
            user_data=properties.get('UserData'),
            count=1,
            security_group_names=group_names,
            instance_type=properties.get("InstanceType", "m1.small"),
            subnet_id=properties.get("SubnetId"),
            key_name=properties.get("KeyName"),
            private_ip=properties.get('PrivateIpAddress'),
        )
        instance = reservation.instances[0]
        for tag in properties.get("Tags", []):
            instance.add_tag(tag["Key"], tag["Value"])
        return instance

    @classmethod
    def delete_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        ec2_backend = ec2_backends[region_name]
        all_instances = ec2_backend.all_instances()

        # the resource_name for instances is the stack name, logical id, and random suffix separated
        # by hyphens.  So to lookup the instances using the 'aws:cloudformation:logical-id' tag, we need to
        # extract the logical-id from the resource_name
        logical_id = resource_name.split('-')[1]

        for instance in all_instances:
            instance_tags = instance.get_tags()
            for tag in instance_tags:
                if tag['key'] == 'aws:cloudformation:logical-id' and tag['value'] == logical_id:
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
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))
        self._state_reason = StateReason("Client.UserInitiatedShutdown: User initiated shutdown",
                                         "Client.UserInitiatedShutdown")

    def delete(self, region):
        self.terminate()

    def terminate(self, *args, **kwargs):
        for nic in self.nics.values():
            nic.stop()

        self.teardown_defaults()

        if self._spot_fleet_id:
            spot_fleet = self.ec2_backend.get_spot_fleet_request(self._spot_fleet_id)
            for spec in spot_fleet.launch_specs:
                if spec.instance_type == self.instance_type and spec.subnet_id == self.subnet_id:
                    break
            spot_fleet.fulfilled_capacity -= spec.weighted_capacity
            spot_fleet.spot_requests = [req for req in spot_fleet.spot_requests if req.instance != self]

        self._state.name = "terminated"
        self._state.code = 48

        self._reason = "User initiated ({0})".format(
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))
        self._state_reason = StateReason("Client.UserInitiatedShutdown: User initiated shutdown",
                                         "Client.UserInitiatedShutdown")

    def reboot(self, *args, **kwargs):
        self._state.name = "running"
        self._state.code = 16

        self._reason = ""
        self._state_reason = StateReason()

    @property
    def dynamic_group_list(self):
        if self.nics:
            groups = []
            for nic in self.nics.values():
                for group in nic.group_set:
                    groups.append(group)
            return groups
        else:
            return self.security_groups

    def prep_nics(self, nic_spec, private_ip=None, associate_public_ip=None):
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
        primary_nic = {'SubnetId': self.subnet_id,
                       'PrivateIpAddress': private_ip,
                       'AssociatePublicIpAddress': associate_public_ip}
        primary_nic = dict((k, v) for k, v in primary_nic.items() if v)

        # If empty NIC spec but primary NIC values provided, create NIC from
        # them.
        if primary_nic and not nic_spec:
            nic_spec[0] = primary_nic
            nic_spec[0]['DeviceIndex'] = 0

        # Flesh out data structures and associations
        for nic in nic_spec.values():
            device_index = int(nic.get('DeviceIndex'))

            nic_id = nic.get('NetworkInterfaceId')
            if nic_id:
                # If existing NIC found, use it.
                use_nic = self.ec2_backend.get_network_interface(nic_id)
                use_nic.device_index = device_index
                use_nic.public_ip_auto_assign = False

            else:
                # If primary NIC values provided, use them for the primary NIC.
                if device_index == 0 and primary_nic:
                    nic.update(primary_nic)

                if 'SubnetId' in nic:
                    subnet = self.ec2_backend.get_subnet(nic['SubnetId'])
                else:
                    subnet = None

                group_id = nic.get('SecurityGroupId')
                group_ids = [group_id] if group_id else []

                use_nic = self.ec2_backend.create_network_interface(subnet,
                                                                    nic.get(
                                                                        'PrivateIpAddress'),
                                                                    device_index=device_index,
                                                                    public_ip_auto_assign=nic.get(
                                                                        'AssociatePublicIpAddress', False),
                                                                    group_ids=group_ids)

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

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'AvailabilityZone':
            return self.placement
        elif attribute_name == 'PrivateDnsName':
            return self.private_dns
        elif attribute_name == 'PublicDnsName':
            return self.public_dns
        elif attribute_name == 'PrivateIp':
            return self.private_ip
        elif attribute_name == 'PublicIp':
            return self.public_ip
        raise UnformattedGetAttTemplateException()


class InstanceBackend(object):
    def __init__(self):
        self.reservations = OrderedDict()
        super(InstanceBackend, self).__init__()

    def get_instance(self, instance_id):
        for instance in self.all_instances():
            if instance.id == instance_id:
                return instance
        raise InvalidInstanceIdError(instance_id)

    def add_instances(self, image_id, count, user_data, security_group_names,
                      **kwargs):
        new_reservation = Reservation()
        new_reservation.id = random_reservation_id()

        security_groups = [self.get_security_group_from_name(name)
                           for name in security_group_names]
        security_groups.extend(self.get_security_group_from_id(sg_id)
                               for sg_id in kwargs.pop("security_group_ids", []))
        self.reservations[new_reservation.id] = new_reservation

        tags = kwargs.pop("tags", {})
        instance_tags = tags.get('instance', {})

        for index in range(count):
            new_instance = Instance(
                self,
                image_id,
                user_data,
                security_groups,
                **kwargs
            )
            new_reservation.instances.append(new_instance)
            new_instance.add_tags(instance_tags)
            new_instance.setup_defaults()
        return new_reservation

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
                "InvalidParameterCombination", "No instances specified")
        for instance in self.get_multi_instances_by_id(instance_ids):
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

    def modify_instance_security_groups(self, instance_id, new_group_list):
        instance = self.get_instance(instance_id)
        setattr(instance, 'security_groups', new_group_list)
        return instance

    def describe_instance_attribute(self, instance_id, key):
        if key == 'group_set':
            key = 'security_groups'
        instance = self.get_instance(instance_id)
        value = getattr(instance, key)
        return instance, value

    def all_instances(self):
        instances = []
        for reservation in self.all_reservations():
            for instance in reservation.instances:
                instances.append(instance)
        return instances

    def all_running_instances(self):
        instances = []
        for reservation in self.all_reservations():
            for instance in reservation.instances:
                if instance.state_code == 16:
                    instances.append(instance)
        return instances

    def get_multi_instances_by_id(self, instance_ids):
        """
        :param instance_ids: A string list with instance ids
        :return: A list with instance objects
        """
        result = []

        for reservation in self.all_reservations():
            for instance in reservation.instances:
                if instance.id in instance_ids:
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
        """ Go through all of the reservations and filter to only return those
        associated with the given instance_ids.
        """
        reservations = []
        for reservation in self.all_reservations():
            reservation_instance_ids = [
                instance.id for instance in reservation.instances]
            matching_reservation = any(
                instance_id in reservation_instance_ids for instance_id in instance_ids)
            if matching_reservation:
                reservation.instances = [
                    instance for instance in reservation.instances if instance.id in instance_ids]
                reservations.append(reservation)
        found_instance_ids = [
            instance.id for reservation in reservations for instance in reservation.instances]
        if len(found_instance_ids) != len(instance_ids):
            invalid_id = list(set(instance_ids).difference(
                set(found_instance_ids)))[0]
            raise InvalidInstanceIdError(invalid_id)
        if filters is not None:
            reservations = filter_reservations(reservations, filters)
        return reservations

    def all_reservations(self, filters=None):
        reservations = [copy.copy(reservation) for reservation in self.reservations.values()]
        if filters is not None:
            reservations = filter_reservations(reservations, filters)
        return reservations


class KeyPair(object):
    def __init__(self, name, fingerprint, material):
        self.name = name
        self.fingerprint = fingerprint
        self.material = material

    def get_filter_value(self, filter_name):
        if filter_name == 'key-name':
            return self.name
        elif filter_name == 'fingerprint':
            return self.fingerprint
        else:
            raise FilterNotImplementedError(filter_name, 'DescribeKeyPairs')


class KeyPairBackend(object):
    def __init__(self):
        self.keypairs = {}
        super(KeyPairBackend, self).__init__()

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
            results = [keypair for keypair in self.keypairs.values()
                       if keypair.name in key_names]
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
        keypair = KeyPair(key_name, **random_key_pair())
        self.keypairs[key_name] = keypair
        return keypair


class TagBackend(object):
    VALID_TAG_FILTERS = ['key',
                         'resource-id',
                         'resource-type',
                         'value']

    VALID_TAG_RESOURCE_FILTER_TYPES = ['customer-gateway',
                                       'dhcp-options',
                                       'image',
                                       'instance',
                                       'internet-gateway',
                                       'network-acl',
                                       'network-interface',
                                       'reserved-instances',
                                       'route-table',
                                       'security-group',
                                       'snapshot',
                                       'spot-instances-request',
                                       'subnet',
                                       'volume',
                                       'vpc',
                                       'vpc-peering-connection'
                                       'vpn-connection',
                                       'vpn-gateway']

    def __init__(self):
        self.tags = defaultdict(dict)
        super(TagBackend, self).__init__()

    def create_tags(self, resource_ids, tags):
        if None in set([tags[tag] for tag in tags]):
            raise InvalidParameterValueErrorTagNull()
        for resource_id in resource_ids:
            if resource_id in self.tags:
                if len(self.tags[resource_id]) + len([tag for tag in tags if not tag.startswith("aws:")]) > 50:
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
        import re
        results = []
        key_filters = []
        resource_id_filters = []
        resource_type_filters = []
        value_filters = []
        if filters is not None:
            for tag_filter in filters:
                if tag_filter in self.VALID_TAG_FILTERS:
                    if tag_filter == 'key':
                        for value in filters[tag_filter]:
                            key_filters.append(re.compile(
                                simple_aws_filter_to_re(value)))
                    if tag_filter == 'resource-id':
                        for value in filters[tag_filter]:
                            resource_id_filters.append(
                                re.compile(simple_aws_filter_to_re(value)))
                    if tag_filter == 'resource-type':
                        for value in filters[tag_filter]:
                            resource_type_filters.append(value)
                    if tag_filter == 'value':
                        for value in filters[tag_filter]:
                            value_filters.append(re.compile(
                                simple_aws_filter_to_re(value)))
        for resource_id, tags in self.tags.items():
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
                            if EC2_PREFIX_TO_RESOURCE[get_prefix(resource_id)] == resource_type:
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
                        'resource_id': resource_id,
                        'key': key,
                        'value': value,
                        'resource_type': EC2_PREFIX_TO_RESOURCE[get_prefix(resource_id)],
                    }
                    results.append(result)
        return results


class Ami(TaggedEC2Resource):
    def __init__(self, ec2_backend, ami_id, instance=None, source_ami=None,
                 name=None, description=None, owner_id=111122223333,
                 public=False, virtualization_type=None, architecture=None,
                 state='available', creation_date=None, platform=None,
                 image_type='machine', image_location=None, hypervisor=None,
                 root_device_type='standard', root_device_name='/dev/sda1', sriov='simple',
                 region_name='us-east-1a'
                 ):
        self.ec2_backend = ec2_backend
        self.id = ami_id
        self.state = state
        self.name = name
        self.image_type = image_type
        self.image_location = image_location
        self.owner_id = owner_id
        self.description = description
        self.virtualization_type = virtualization_type
        self.architecture = architecture
        self.kernel_id = None
        self.platform = platform
        self.hypervisor = hypervisor
        self.root_device_name = root_device_name
        self.root_device_type = root_device_type
        self.sriov = sriov
        self.creation_date = utc_date_and_time() if creation_date is None else creation_date

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
            self.launch_permission_groups.add('all')

        # AWS auto-creates these, we should reflect the same.
        volume = self.ec2_backend.create_volume(15, region_name)
        self.ebs_snapshot = self.ec2_backend.create_snapshot(
            volume.id, "Auto-created snapshot for AMI %s" % self.id, owner_id)
        self.ec2_backend.delete_volume(volume.id)

    @property
    def is_public(self):
        return 'all' in self.launch_permission_groups

    @property
    def is_public_string(self):
        return str(self.is_public).lower()

    def get_filter_value(self, filter_name):
        if filter_name == 'virtualization-type':
            return self.virtualization_type
        elif filter_name == 'kernel-id':
            return self.kernel_id
        elif filter_name in ['architecture', 'platform']:
            return getattr(self, filter_name)
        elif filter_name == 'image-id':
            return self.id
        elif filter_name == 'is-public':
            return str(self.is_public)
        elif filter_name == 'state':
            return self.state
        elif filter_name == 'name':
            return self.name
        elif filter_name == 'owner-id':
            return self.owner_id
        else:
            return super(Ami, self).get_filter_value(
                filter_name, 'DescribeImages')


class AmiBackend(object):

    AMI_REGEX = re.compile("ami-[a-z0-9]+")

    def __init__(self):
        self.amis = {}

        self._load_amis()

        super(AmiBackend, self).__init__()

    def _load_amis(self):
        for ami in AMIS:
            ami_id = ami['ami_id']
            self.amis[ami_id] = Ami(self, **ami)

    def create_image(self, instance_id, name=None, description=None, context=None):
        # TODO: check that instance exists and pull info from it.
        ami_id = random_ami_id()
        instance = self.get_instance(instance_id)

        ami = Ami(self, ami_id, instance=instance, source_ami=None,
                  name=name, description=description,
                  owner_id=context.get_current_user() if context else '111122223333')
        self.amis[ami_id] = ami
        return ami

    def copy_image(self, source_image_id, source_region, name=None, description=None):
        source_ami = ec2_backends[source_region].describe_images(
            ami_ids=[source_image_id])[0]
        ami_id = random_ami_id()
        ami = Ami(self, ami_id, instance=None, source_ami=source_ami,
                  name=name, description=description)
        self.amis[ami_id] = ami
        return ami

    def describe_images(self, ami_ids=(), filters=None, exec_users=None, owners=None,
                        context=None):
        images = self.amis.values()

        if len(ami_ids):
            # boto3 seems to default to just searching based on ami ids if that parameter is passed
            # and if no images are found, it raises an errors
            malformed_ami_ids = [ami_id for ami_id in ami_ids if not ami_id.startswith('ami-')]
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
                owners = list(map(
                    lambda o: context.get_current_user()
                    if context and o == 'self' else o,
                    owners))
                images = [ami for ami in images if ami.owner_id in owners]

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

        if group and group != 'all':
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
    def __init__(self, name, endpoint):
        self.name = name
        self.endpoint = endpoint


class Zone(object):
    def __init__(self, name, region_name):
        self.name = name
        self.region_name = region_name


class RegionsAndZonesBackend(object):
    regions = [Region(ri.name, ri.endpoint) for ri in boto.ec2.regions()]

    zones = dict(
        (region, [Zone(region + c, region) for c in 'abc'])
        for region in [r.name for r in regions])

    def describe_regions(self, region_names=[]):
        if len(region_names) == 0:
            return self.regions
        ret = []
        for name in region_names:
            for region in self.regions:
                if region.name == name:
                    ret.append(region)
        return ret

    def describe_availability_zones(self):
        return self.zones[self.region_name]

    def get_zone_by_name(self, name):
        for zone in self.zones[self.region_name]:
            if zone.name == name:
                return zone


class SecurityRule(object):
    def __init__(self, ip_protocol, from_port, to_port, ip_ranges, source_groups):
        self.ip_protocol = ip_protocol
        self.from_port = from_port
        self.to_port = to_port
        self.ip_ranges = ip_ranges or []
        self.source_groups = source_groups

    @property
    def unique_representation(self):
        return "{0}-{1}-{2}-{3}-{4}".format(
            self.ip_protocol,
            self.from_port,
            self.to_port,
            self.ip_ranges,
            self.source_groups
        )

    def __eq__(self, other):
        return self.unique_representation == other.unique_representation


class SecurityGroup(TaggedEC2Resource):
    def __init__(self, ec2_backend, group_id, name, description, vpc_id=None):
        self.ec2_backend = ec2_backend
        self.id = group_id
        self.name = name
        self.description = description
        self.ingress_rules = []
        self.egress_rules = [SecurityRule(-1, None, None, ['0.0.0.0/0'], [])]
        self.enis = {}
        self.vpc_id = vpc_id
        self.owner_id = "123456789012"

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        ec2_backend = ec2_backends[region_name]
        vpc_id = properties.get('VpcId')
        security_group = ec2_backend.create_security_group(
            name=resource_name,
            description=properties.get('GroupDescription'),
            vpc_id=vpc_id,
        )

        for tag in properties.get("Tags", []):
            tag_key = tag["Key"]
            tag_value = tag["Value"]
            security_group.add_tag(tag_key, tag_value)

        for ingress_rule in properties.get('SecurityGroupIngress', []):
            source_group_id = ingress_rule.get('SourceSecurityGroupId')

            ec2_backend.authorize_security_group_ingress(
                group_name_or_id=security_group.id,
                ip_protocol=ingress_rule['IpProtocol'],
                from_port=ingress_rule['FromPort'],
                to_port=ingress_rule['ToPort'],
                ip_ranges=ingress_rule.get('CidrIp'),
                source_group_ids=[source_group_id],
                vpc_id=vpc_id,
            )

        return security_group

    @classmethod
    def update_from_cloudformation_json(cls, original_resource, new_resource_name, cloudformation_json, region_name):
        cls._delete_security_group_given_vpc_id(
            original_resource.name, original_resource.vpc_id, region_name)
        return cls.create_from_cloudformation_json(new_resource_name, cloudformation_json, region_name)

    @classmethod
    def delete_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']
        vpc_id = properties.get('VpcId')
        cls._delete_security_group_given_vpc_id(
            resource_name, vpc_id, region_name)

    @classmethod
    def _delete_security_group_given_vpc_id(cls, resource_name, vpc_id, region_name):
        ec2_backend = ec2_backends[region_name]
        security_group = ec2_backend.get_security_group_from_name(
            resource_name, vpc_id)
        if security_group:
            security_group.delete(region_name)

    def delete(self, region_name):
        ''' Not exposed as part of the ELB API - used for CloudFormation. '''
        self.ec2_backend.delete_security_group(group_id=self.id)

    @property
    def physical_resource_id(self):
        return self.id

    def matches_filter(self, key, filter_value):
        def to_attr(filter_name):
            attr = None

            if filter_name == 'group-name':
                attr = 'name'
            elif filter_name == 'group-id':
                attr = 'id'
            elif filter_name == 'vpc-id':
                attr = 'vpc_id'
            else:
                attr = filter_name.replace('-', '_')

            return attr

        if key.startswith('ip-permission'):
            match = re.search(r"ip-permission.(*)", key)
            ingress_attr = to_attr(match.groups()[0])

            for ingress in self.ingress_rules:
                if getattr(ingress, ingress_attr) in filter_value:
                    return True
        elif is_tag_filter(key):
            tag_value = self.get_filter_value(key)
            if isinstance(filter_value, list):
                return tag_filter_matches(self, key, filter_value)
            return tag_value in filter_value
        else:
            attr_name = to_attr(key)
            return getattr(self, attr_name) in filter_value

        return False

    def matches_filters(self, filters):
        for key, value in filters.items():
            if not self.matches_filter(key, value):
                return False
        return True

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'GroupId':
            return self.id
        raise UnformattedGetAttTemplateException()

    def add_ingress_rule(self, rule):
        if rule in self.ingress_rules:
            raise InvalidPermissionDuplicateError()
        else:
            self.ingress_rules.append(rule)

    def add_egress_rule(self, rule):
        self.egress_rules.append(rule)

    def get_number_of_ingress_rules(self):
        return sum(
            len(rule.ip_ranges) + len(rule.source_groups)
            for rule in self.ingress_rules)

    def get_number_of_egress_rules(self):
        return sum(
            len(rule.ip_ranges) + len(rule.source_groups)
            for rule in self.egress_rules)


class SecurityGroupBackend(object):
    def __init__(self):
        # the key in the dict group is the vpc_id or None (non-vpc)
        self.groups = defaultdict(dict)

        # Create the default security group
        self.create_security_group("default", "default group")

        super(SecurityGroupBackend, self).__init__()

    def create_security_group(self, name, description, vpc_id=None, force=False):
        if not description:
            raise MissingParameterError('GroupDescription')

        group_id = random_security_group_id()
        if not force:
            existing_group = self.get_security_group_from_name(name, vpc_id)
            if existing_group:
                raise InvalidSecurityGroupDuplicateError(name)
        group = SecurityGroup(self, group_id, name, description, vpc_id=vpc_id)

        self.groups[vpc_id][group_id] = group
        return group

    def describe_security_groups(self, group_ids=None, groupnames=None, filters=None):
        matches = itertools.chain(*[x.values()
                                    for x in self.groups.values()])
        if group_ids:
            matches = [grp for grp in matches
                       if grp.id in group_ids]
            if len(group_ids) > len(matches):
                unknown_ids = set(group_ids) - set(matches)
                raise InvalidSecurityGroupNotFoundError(unknown_ids)
        if groupnames:
            matches = [grp for grp in matches
                       if grp.name in groupnames]
            if len(groupnames) > len(matches):
                unknown_names = set(groupnames) - set(matches)
                raise InvalidSecurityGroupNotFoundError(unknown_names)
        if filters:
            matches = [grp for grp in matches
                       if grp.matches_filters(filters)]

        return matches

    def _delete_security_group(self, vpc_id, group_id):
        if self.groups[vpc_id][group_id].enis:
            raise DependencyViolationError(
                "{0} is being utilized by {1}".format(group_id, 'ENIs'))
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
            group = self.get_security_group_from_name(name)
            if group:
                return self._delete_security_group(None, group.id)
            raise InvalidSecurityGroupNotFoundError(name)

    def get_security_group_from_id(self, group_id):
        # 2 levels of chaining necessary since it's a complex structure
        all_groups = itertools.chain.from_iterable(
            [x.values() for x in self.groups.values()])
        for group in all_groups:
            if group.id == group_id:
                return group

    def get_security_group_from_name(self, name, vpc_id=None):
        for group_id, group in self.groups[vpc_id].items():
            if group.name == name:
                return group

    def get_security_group_by_name_or_id(self, group_name_or_id, vpc_id):
        # try searching by id, fallbacks to name search
        group = self.get_security_group_from_id(group_name_or_id)
        if group is None:
            group = self.get_security_group_from_name(group_name_or_id, vpc_id)
        return group

    def authorize_security_group_ingress(self,
                                         group_name_or_id,
                                         ip_protocol,
                                         from_port,
                                         to_port,
                                         ip_ranges,
                                         source_group_names=None,
                                         source_group_ids=None,
                                         vpc_id=None):
        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)
        if ip_ranges and not isinstance(ip_ranges, list):
            ip_ranges = [ip_ranges]
        if ip_ranges:
            for cidr in ip_ranges:
                if not is_valid_cidr(cidr):
                    raise InvalidCIDRSubnetError(cidr=cidr)

        self._verify_group_will_respect_rule_count_limit(
            group, group.get_number_of_ingress_rules(),
            ip_ranges, source_group_names, source_group_ids)

        source_group_names = source_group_names if source_group_names else []
        source_group_ids = source_group_ids if source_group_ids else []

        source_groups = []
        for source_group_name in source_group_names:
            source_group = self.get_security_group_from_name(
                source_group_name, vpc_id)
            if source_group:
                source_groups.append(source_group)

        # for VPCs
        for source_group_id in source_group_ids:
            source_group = self.get_security_group_from_id(source_group_id)
            if source_group:
                source_groups.append(source_group)

        security_rule = SecurityRule(
            ip_protocol, from_port, to_port, ip_ranges, source_groups)
        group.add_ingress_rule(security_rule)

    def revoke_security_group_ingress(self,
                                      group_name_or_id,
                                      ip_protocol,
                                      from_port,
                                      to_port,
                                      ip_ranges,
                                      source_group_names=None,
                                      source_group_ids=None,
                                      vpc_id=None):

        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)

        source_groups = []
        for source_group_name in source_group_names:
            source_group = self.get_security_group_from_name(
                source_group_name, vpc_id)
            if source_group:
                source_groups.append(source_group)

        for source_group_id in source_group_ids:
            source_group = self.get_security_group_from_id(source_group_id)
            if source_group:
                source_groups.append(source_group)

        security_rule = SecurityRule(
            ip_protocol, from_port, to_port, ip_ranges, source_groups)
        if security_rule in group.ingress_rules:
            group.ingress_rules.remove(security_rule)
            return security_rule
        raise InvalidPermissionNotFoundError()

    def authorize_security_group_egress(self,
                                        group_name_or_id,
                                        ip_protocol,
                                        from_port,
                                        to_port,
                                        ip_ranges,
                                        source_group_names=None,
                                        source_group_ids=None,
                                        vpc_id=None):

        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)
        if ip_ranges and not isinstance(ip_ranges, list):
            ip_ranges = [ip_ranges]
        if ip_ranges:
            for cidr in ip_ranges:
                if not is_valid_cidr(cidr):
                    raise InvalidCIDRSubnetError(cidr=cidr)

        self._verify_group_will_respect_rule_count_limit(
            group, group.get_number_of_egress_rules(),
            ip_ranges, source_group_names, source_group_ids)

        source_group_names = source_group_names if source_group_names else []
        source_group_ids = source_group_ids if source_group_ids else []

        source_groups = []
        for source_group_name in source_group_names:
            source_group = self.get_security_group_from_name(
                source_group_name, vpc_id)
            if source_group:
                source_groups.append(source_group)

        # for VPCs
        for source_group_id in source_group_ids:
            source_group = self.get_security_group_from_id(source_group_id)
            if source_group:
                source_groups.append(source_group)

        security_rule = SecurityRule(
            ip_protocol, from_port, to_port, ip_ranges, source_groups)
        group.add_egress_rule(security_rule)

    def revoke_security_group_egress(self,
                                     group_name_or_id,
                                     ip_protocol,
                                     from_port,
                                     to_port,
                                     ip_ranges,
                                     source_group_names=None,
                                     source_group_ids=None,
                                     vpc_id=None):

        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)

        source_groups = []
        for source_group_name in source_group_names:
            source_group = self.get_security_group_from_name(
                source_group_name, vpc_id)
            if source_group:
                source_groups.append(source_group)

        for source_group_id in source_group_ids:
            source_group = self.get_security_group_from_id(source_group_id)
            if source_group:
                source_groups.append(source_group)

        security_rule = SecurityRule(
            ip_protocol, from_port, to_port, ip_ranges, source_groups)
        if security_rule in group.egress_rules:
            group.egress_rules.remove(security_rule)
            return security_rule
        raise InvalidPermissionNotFoundError()

    def _verify_group_will_respect_rule_count_limit(
            self, group, current_rule_nb,
            ip_ranges, source_group_names=None, source_group_ids=None):
        max_nb_rules = 50 if group.vpc_id else 100
        future_group_nb_rules = current_rule_nb
        if ip_ranges:
            future_group_nb_rules += len(ip_ranges)
        if source_group_ids:
            future_group_nb_rules += len(source_group_ids)
        if source_group_names:
            future_group_nb_rules += len(source_group_names)
        if future_group_nb_rules > max_nb_rules:
            raise RulesPerSecurityGroupLimitExceededError


class SecurityGroupIngress(object):
    def __init__(self, security_group, properties):
        self.security_group = security_group
        self.properties = properties

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        ec2_backend = ec2_backends[region_name]
        group_name = properties.get('GroupName')
        group_id = properties.get('GroupId')
        ip_protocol = properties.get("IpProtocol")
        cidr_ip = properties.get("CidrIp")
        cidr_ipv6 = properties.get("CidrIpv6")
        from_port = properties.get("FromPort")
        source_security_group_id = properties.get("SourceSecurityGroupId")
        source_security_group_name = properties.get("SourceSecurityGroupName")
        # source_security_owner_id =
        # properties.get("SourceSecurityGroupOwnerId")  # IGNORED AT THE MOMENT
        to_port = properties.get("ToPort")

        assert group_id or group_name
        assert source_security_group_name or cidr_ip or cidr_ipv6 or source_security_group_id
        assert ip_protocol

        if source_security_group_id:
            source_security_group_ids = [source_security_group_id]
        else:
            source_security_group_ids = None
        if source_security_group_name:
            source_security_group_names = [source_security_group_name]
        else:
            source_security_group_names = None
        if cidr_ip:
            ip_ranges = [cidr_ip]
        else:
            ip_ranges = []

        if group_id:
            security_group = ec2_backend.describe_security_groups(group_ids=[group_id])[
                0]
        else:
            security_group = ec2_backend.describe_security_groups(
                groupnames=[group_name])[0]

        ec2_backend.authorize_security_group_ingress(
            group_name_or_id=security_group.id,
            ip_protocol=ip_protocol,
            from_port=from_port,
            to_port=to_port,
            ip_ranges=ip_ranges,
            source_group_ids=source_security_group_ids,
            source_group_names=source_security_group_names,
        )

        return cls(security_group, properties)


class VolumeAttachment(object):
    def __init__(self, volume, instance, device, status):
        self.volume = volume
        self.attach_time = utc_date_and_time()
        self.instance = instance
        self.device = device
        self.status = status

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        instance_id = properties['InstanceId']
        volume_id = properties['VolumeId']

        ec2_backend = ec2_backends[region_name]
        attachment = ec2_backend.attach_volume(
            volume_id=volume_id,
            instance_id=instance_id,
            device_path=properties['Device'],
        )
        return attachment


class Volume(TaggedEC2Resource):
    def __init__(self, ec2_backend, volume_id, size, zone, snapshot_id=None, encrypted=False):
        self.id = volume_id
        self.size = size
        self.zone = zone
        self.create_time = utc_date_and_time()
        self.attachment = None
        self.snapshot_id = snapshot_id
        self.ec2_backend = ec2_backend
        self.encrypted = encrypted

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        ec2_backend = ec2_backends[region_name]
        volume = ec2_backend.create_volume(
            size=properties.get('Size'),
            zone_name=properties.get('AvailabilityZone'),
        )
        return volume

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def status(self):
        if self.attachment:
            return 'in-use'
        else:
            return 'available'

    def get_filter_value(self, filter_name):
        if filter_name.startswith('attachment') and not self.attachment:
            return None
        elif filter_name == 'attachment.attach-time':
            return self.attachment.attach_time
        elif filter_name == 'attachment.device':
            return self.attachment.device
        elif filter_name == 'attachment.instance-id':
            return self.attachment.instance.id
        elif filter_name == 'attachment.status':
            return self.attachment.status
        elif filter_name == 'create-time':
            return self.create_time
        elif filter_name == 'size':
            return self.size
        elif filter_name == 'snapshot-id':
            return self.snapshot_id
        elif filter_name == 'status':
            return self.status
        elif filter_name == 'volume-id':
            return self.id
        elif filter_name == 'encrypted':
            return str(self.encrypted).lower()
        elif filter_name == 'availability-zone':
            return self.zone.name
        else:
            return super(Volume, self).get_filter_value(
                filter_name, 'DescribeVolumes')


class Snapshot(TaggedEC2Resource):
    def __init__(self, ec2_backend, snapshot_id, volume, description, encrypted=False, owner_id='123456789012'):
        self.id = snapshot_id
        self.volume = volume
        self.description = description
        self.start_time = utc_date_and_time()
        self.create_volume_permission_groups = set()
        self.ec2_backend = ec2_backend
        self.status = 'completed'
        self.encrypted = encrypted
        self.owner_id = owner_id

    def get_filter_value(self, filter_name):
        if filter_name == 'description':
            return self.description
        elif filter_name == 'snapshot-id':
            return self.id
        elif filter_name == 'start-time':
            return self.start_time
        elif filter_name == 'volume-id':
            return self.volume.id
        elif filter_name == 'volume-size':
            return self.volume.size
        elif filter_name == 'encrypted':
            return str(self.encrypted).lower()
        elif filter_name == 'status':
            return self.status
        else:
            return super(Snapshot, self).get_filter_value(
                filter_name, 'DescribeSnapshots')


class EBSBackend(object):
    def __init__(self):
        self.volumes = {}
        self.attachments = {}
        self.snapshots = {}
        super(EBSBackend, self).__init__()

    def create_volume(self, size, zone_name, snapshot_id=None, encrypted=False):
        volume_id = random_volume_id()
        zone = self.get_zone_by_name(zone_name)
        if snapshot_id:
            snapshot = self.get_snapshot(snapshot_id)
            if size is None:
                size = snapshot.volume.size
            if snapshot.encrypted:
                encrypted = snapshot.encrypted
        volume = Volume(self, volume_id, size, zone, snapshot_id, encrypted)
        self.volumes[volume_id] = volume
        return volume

    def describe_volumes(self, volume_ids=None, filters=None):
        matches = self.volumes.values()
        if volume_ids:
            matches = [vol for vol in matches
                       if vol.id in volume_ids]
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
            return self.volumes.pop(volume_id)
        raise InvalidVolumeIdError(volume_id)

    def attach_volume(self, volume_id, instance_id, device_path):
        volume = self.get_volume(volume_id)
        instance = self.get_instance(instance_id)

        if not volume or not instance:
            return False

        volume.attachment = VolumeAttachment(
            volume, instance, device_path, 'attached')
        # Modify instance to capture mount of block device.
        bdt = BlockDeviceType(volume_id=volume_id, status=volume.status, size=volume.size,
                              attach_time=utc_date_and_time())
        instance.block_device_mapping[device_path] = bdt
        return volume.attachment

    def detach_volume(self, volume_id, instance_id, device_path):
        volume = self.get_volume(volume_id)
        self.get_instance(instance_id)

        old_attachment = volume.attachment
        if not old_attachment:
            raise InvalidVolumeAttachmentError(volume_id, instance_id)
        old_attachment.status = 'detached'

        volume.attachment = None
        return old_attachment

    def create_snapshot(self, volume_id, description, owner_id=None):
        snapshot_id = random_snapshot_id()
        volume = self.get_volume(volume_id)
        params = [self, snapshot_id, volume, description, volume.encrypted]
        if owner_id:
            params.append(owner_id)
        snapshot = Snapshot(*params)
        self.snapshots[snapshot_id] = snapshot
        return snapshot

    def describe_snapshots(self, snapshot_ids=None, filters=None):
        matches = self.snapshots.values()
        if snapshot_ids:
            matches = [snap for snap in matches
                       if snap.id in snapshot_ids]
            if len(snapshot_ids) > len(matches):
                unknown_ids = set(snapshot_ids) - set(matches)
                raise InvalidSnapshotIdError(unknown_ids)
        if filters:
            matches = generic_filter(filters, matches)
        return matches

    def copy_snapshot(self, source_snapshot_id, source_region, description=None):
        source_snapshot = ec2_backends[source_region].describe_snapshots(
            snapshot_ids=[source_snapshot_id])[0]
        snapshot_id = random_snapshot_id()
        snapshot = Snapshot(self, snapshot_id, volume=source_snapshot.volume,
            description=description, encrypted=source_snapshot.encrypted)
        self.snapshots[snapshot_id] = snapshot
        return snapshot

    def get_snapshot(self, snapshot_id):
        snapshot = self.snapshots.get(snapshot_id, None)
        if not snapshot:
            raise InvalidSnapshotIdError(snapshot_id)
        return snapshot

    def delete_snapshot(self, snapshot_id):
        if snapshot_id in self.snapshots:
            return self.snapshots.pop(snapshot_id)
        raise InvalidSnapshotIdError(snapshot_id)

    def get_create_volume_permission_groups(self, snapshot_id):
        snapshot = self.get_snapshot(snapshot_id)
        return snapshot.create_volume_permission_groups

    def add_create_volume_permission(self, snapshot_id, user_id=None, group=None):
        if user_id:
            self.raise_not_implemented_error(
                "The UserId parameter for ModifySnapshotAttribute")

        if group != 'all':
            raise InvalidAMIAttributeItemValueError("UserGroup", group)
        snapshot = self.get_snapshot(snapshot_id)
        snapshot.create_volume_permission_groups.add(group)
        return True

    def remove_create_volume_permission(self, snapshot_id, user_id=None, group=None):
        if user_id:
            self.raise_not_implemented_error(
                "The UserId parameter for ModifySnapshotAttribute")

        if group != 'all':
            raise InvalidAMIAttributeItemValueError("UserGroup", group)
        snapshot = self.get_snapshot(snapshot_id)
        snapshot.create_volume_permission_groups.discard(group)
        return True


class VPC(TaggedEC2Resource):
    def __init__(self, ec2_backend, vpc_id, cidr_block, is_default, instance_tenancy='default',
                 amazon_provided_ipv6_cidr_block=False):

        self.ec2_backend = ec2_backend
        self.id = vpc_id
        self.cidr_block = cidr_block
        self.cidr_block_association_set = {}
        self.dhcp_options = None
        self.state = 'available'
        self.instance_tenancy = instance_tenancy
        self.is_default = 'true' if is_default else 'false'
        self.enable_dns_support = 'true'
        # This attribute is set to 'true' only for default VPCs
        # or VPCs created using the wizard of the VPC console
        self.enable_dns_hostnames = 'true' if is_default else 'false'

        self.associate_vpc_cidr_block(cidr_block)
        if amazon_provided_ipv6_cidr_block:
            self.associate_vpc_cidr_block(cidr_block, amazon_provided_ipv6_cidr_block=amazon_provided_ipv6_cidr_block)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        ec2_backend = ec2_backends[region_name]
        vpc = ec2_backend.create_vpc(
            cidr_block=properties['CidrBlock'],
            instance_tenancy=properties.get('InstanceTenancy', 'default')
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
        if filter_name in ('vpc-id', 'vpcId'):
            return self.id
        elif filter_name in ('cidr', 'cidr-block', 'cidrBlock'):
            return self.cidr_block
        elif filter_name in ('cidr-block-association.cidr-block', 'ipv6-cidr-block-association.ipv6-cidr-block'):
            return [c['cidr_block'] for c in self.get_cidr_block_association_set(ipv6='ipv6' in filter_name)]
        elif filter_name in ('cidr-block-association.association-id', 'ipv6-cidr-block-association.association-id'):
            return self.cidr_block_association_set.keys()
        elif filter_name in ('cidr-block-association.state', 'ipv6-cidr-block-association.state'):
            return [c['cidr_block_state']['state'] for c in self.get_cidr_block_association_set(ipv6='ipv6' in filter_name)]
        elif filter_name in ('instance_tenancy', 'InstanceTenancy'):
            return self.instance_tenancy
        elif filter_name in ('is-default', 'isDefault'):
            return self.is_default
        elif filter_name == 'state':
            return self.state
        elif filter_name in ('dhcp-options-id', 'dhcpOptionsId'):
            if not self.dhcp_options:
                return None
            return self.dhcp_options.id
        else:
            return super(VPC, self).get_filter_value(filter_name, 'DescribeVpcs')

    def associate_vpc_cidr_block(self, cidr_block, amazon_provided_ipv6_cidr_block=False):
        max_associations = 5 if not amazon_provided_ipv6_cidr_block else 1

        if len(self.get_cidr_block_association_set(amazon_provided_ipv6_cidr_block)) >= max_associations:
            raise CidrLimitExceeded(self.id, max_associations)

        association_id = random_vpc_cidr_association_id()

        association_set = {
            'association_id': association_id,
            'cidr_block_state': {'state': 'associated', 'StatusMessage': ''}
        }

        association_set['cidr_block'] = random_ipv6_cidr() if amazon_provided_ipv6_cidr_block else cidr_block
        self.cidr_block_association_set[association_id] = association_set
        return association_set

    def disassociate_vpc_cidr_block(self, association_id):
        if self.cidr_block == self.cidr_block_association_set.get(association_id, {}).get('cidr_block'):
            raise OperationNotPermitted(association_id)

        response = self.cidr_block_association_set.pop(association_id, {})
        if response:
            response['vpc_id'] = self.id
            response['cidr_block_state']['state'] = 'disassociating'
        return response

    def get_cidr_block_association_set(self, ipv6=False):
        return [c for c in self.cidr_block_association_set.values() if ('::/' if ipv6 else '.') in c.get('cidr_block')]


class VPCBackend(object):
    def __init__(self):
        self.vpcs = {}
        super(VPCBackend, self).__init__()

    def create_vpc(self, cidr_block, instance_tenancy='default', amazon_provided_ipv6_cidr_block=False):
        vpc_id = random_vpc_id()
        vpc = VPC(self, vpc_id, cidr_block, len(self.vpcs) == 0, instance_tenancy, amazon_provided_ipv6_cidr_block)
        self.vpcs[vpc_id] = vpc

        # AWS creates a default main route table and security group.
        self.create_route_table(vpc_id, main=True)

        # AWS creates a default Network ACL
        self.create_network_acl(vpc_id, default=True)

        default = self.get_security_group_from_name('default', vpc_id=vpc_id)
        if not default:
            self.create_security_group(
                'default', 'default VPC security group', vpc_id=vpc_id)

        return vpc

    def get_vpc(self, vpc_id):
        if vpc_id not in self.vpcs:
            raise InvalidVPCIdError(vpc_id)
        return self.vpcs.get(vpc_id)

    def get_all_vpcs(self, vpc_ids=None, filters=None):
        matches = self.vpcs.values()
        if vpc_ids:
            matches = [vpc for vpc in matches
                       if vpc.id in vpc_ids]
            if len(vpc_ids) > len(matches):
                unknown_ids = set(vpc_ids) - set(matches)
                raise InvalidVPCIdError(unknown_ids)
        if filters:
            matches = generic_filter(filters, matches)
        return matches

    def delete_vpc(self, vpc_id):
        # Delete route table if only main route table remains.
        route_tables = self.get_all_route_tables(filters={'vpc-id': vpc_id})
        if len(route_tables) > 1:
            raise DependencyViolationError(
                "The vpc {0} has dependencies and cannot be deleted.".format(vpc_id)
            )
        for route_table in route_tables:
            self.delete_route_table(route_table.id)

        # Delete default security group if exists.
        default = self.get_security_group_from_name('default', vpc_id=vpc_id)
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
        if attr_name in ('enable_dns_support', 'enable_dns_hostnames'):
            return getattr(vpc, attr_name)
        else:
            raise InvalidParameterValueError(attr_name)

    def modify_vpc_attribute(self, vpc_id, attr_name, attr_value):
        vpc = self.get_vpc(vpc_id)
        if attr_name in ('enable_dns_support', 'enable_dns_hostnames'):
            setattr(vpc, attr_name, attr_value)
        else:
            raise InvalidParameterValueError(attr_name)

    def disassociate_vpc_cidr_block(self, association_id):
        for vpc in self.vpcs.values():
            response = vpc.disassociate_vpc_cidr_block(association_id)
            if response:
                return response
        else:
            raise InvalidVpcCidrBlockAssociationIdError(association_id)

    def associate_vpc_cidr_block(self, vpc_id, cidr_block, amazon_provided_ipv6_cidr_block):
        vpc = self.get_vpc(vpc_id)
        return vpc.associate_vpc_cidr_block(cidr_block, amazon_provided_ipv6_cidr_block)


class VPCPeeringConnectionStatus(object):
    def __init__(self, code='initiating-request', message=''):
        self.code = code
        self.message = message

    def initiating(self):
        self.code = 'initiating-request'
        self.message = 'Initiating Request to {accepter ID}'

    def pending(self):
        self.code = 'pending-acceptance'
        self.message = 'Pending Acceptance by {accepter ID}'

    def accept(self):
        self.code = 'active'
        self.message = 'Active'

    def reject(self):
        self.code = 'rejected'
        self.message = 'Inactive'


class VPCPeeringConnection(TaggedEC2Resource):
    def __init__(self, vpc_pcx_id, vpc, peer_vpc):
        self.id = vpc_pcx_id
        self.vpc = vpc
        self.peer_vpc = peer_vpc
        self._status = VPCPeeringConnectionStatus()

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        ec2_backend = ec2_backends[region_name]
        vpc = ec2_backend.get_vpc(properties['VpcId'])
        peer_vpc = ec2_backend.get_vpc(properties['PeerVpcId'])

        vpc_pcx = ec2_backend.create_vpc_peering_connection(vpc, peer_vpc)

        return vpc_pcx

    @property
    def physical_resource_id(self):
        return self.id


class VPCPeeringConnectionBackend(object):
    def __init__(self):
        self.vpc_pcxs = {}
        super(VPCPeeringConnectionBackend, self).__init__()

    def create_vpc_peering_connection(self, vpc, peer_vpc):
        vpc_pcx_id = random_vpc_peering_connection_id()
        vpc_pcx = VPCPeeringConnection(vpc_pcx_id, vpc, peer_vpc)
        vpc_pcx._status.pending()
        self.vpc_pcxs[vpc_pcx_id] = vpc_pcx
        return vpc_pcx

    def get_all_vpc_peering_connections(self):
        return self.vpc_pcxs.values()

    def get_vpc_peering_connection(self, vpc_pcx_id):
        if vpc_pcx_id not in self.vpc_pcxs:
            raise InvalidVPCPeeringConnectionIdError(vpc_pcx_id)
        return self.vpc_pcxs.get(vpc_pcx_id)

    def delete_vpc_peering_connection(self, vpc_pcx_id):
        deleted = self.vpc_pcxs.pop(vpc_pcx_id, None)
        if not deleted:
            raise InvalidVPCPeeringConnectionIdError(vpc_pcx_id)
        return deleted

    def accept_vpc_peering_connection(self, vpc_pcx_id):
        vpc_pcx = self.get_vpc_peering_connection(vpc_pcx_id)
        if vpc_pcx._status.code != 'pending-acceptance':
            raise InvalidVPCPeeringConnectionStateTransitionError(vpc_pcx.id)
        vpc_pcx._status.accept()
        return vpc_pcx

    def reject_vpc_peering_connection(self, vpc_pcx_id):
        vpc_pcx = self.get_vpc_peering_connection(vpc_pcx_id)
        if vpc_pcx._status.code != 'pending-acceptance':
            raise InvalidVPCPeeringConnectionStateTransitionError(vpc_pcx.id)
        vpc_pcx._status.reject()
        return vpc_pcx


class Subnet(TaggedEC2Resource):
    def __init__(self, ec2_backend, subnet_id, vpc_id, cidr_block, availability_zone, default_for_az,
                 map_public_ip_on_launch):
        self.ec2_backend = ec2_backend
        self.id = subnet_id
        self.vpc_id = vpc_id
        self.cidr_block = cidr_block
        self.cidr = ipaddress.ip_network(six.text_type(self.cidr_block))
        self._availability_zone = availability_zone
        self.default_for_az = default_for_az
        self.map_public_ip_on_launch = map_public_ip_on_launch

        # Theory is we assign ip's as we go (as 16,777,214 usable IPs in a /8)
        self._subnet_ip_generator = self.cidr.hosts()
        self.reserved_ips = [six.next(self._subnet_ip_generator) for _ in range(0, 3)]  # Reserved by AWS
        self._unused_ips = set()  # if instance is destroyed hold IP here for reuse
        self._subnet_ips = {}  # has IP: instance

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        vpc_id = properties['VpcId']
        cidr_block = properties['CidrBlock']
        availability_zone = properties.get('AvailabilityZone')
        ec2_backend = ec2_backends[region_name]
        subnet = ec2_backend.create_subnet(
            vpc_id=vpc_id,
            cidr_block=cidr_block,
            availability_zone=availability_zone,
        )
        for tag in properties.get("Tags", []):
            tag_key = tag["Key"]
            tag_value = tag["Value"]
            subnet.add_tag(tag_key, tag_value)

        return subnet

    @property
    def availability_zone(self):
        return self._availability_zone

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
        if filter_name in ('cidr', 'cidrBlock', 'cidr-block'):
            return self.cidr_block
        elif filter_name in ('vpc-id', 'vpcId'):
            return self.vpc_id
        elif filter_name == 'subnet-id':
            return self.id
        elif filter_name in ('availabilityZone', 'availability-zone'):
            return self.availability_zone
        elif filter_name in ('defaultForAz', 'default-for-az'):
            return self.default_for_az
        else:
            return super(Subnet, self).get_filter_value(
                filter_name, 'DescribeSubnets')

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'AvailabilityZone':
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "AvailabilityZone" ]"')
        raise UnformattedGetAttTemplateException()

    def get_available_subnet_ip(self, instance):
        try:
            new_ip = self._unused_ips.pop()
        except KeyError:
            new_ip = six.next(self._subnet_ip_generator)

            # Skips any IP's if they've been manually specified
            while str(new_ip) in self._subnet_ips:
                new_ip = six.next(self._subnet_ip_generator)

            if new_ip == self.cidr.broadcast_address:
                raise StopIteration()  # Broadcast address cant be used obviously
        # TODO StopIteration will be raised if no ip's available, not sure how aws handles this.

        new_ip = str(new_ip)
        self._subnet_ips[new_ip] = instance

        return new_ip

    def request_ip(self, ip, instance):
        if ipaddress.ip_address(ip) not in self.cidr:
            raise Exception('IP does not fall in the subnet CIDR of {0}'.format(self.cidr))

        if ip in self._subnet_ips:
            raise Exception('IP already in use')
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


class SubnetBackend(object):
    def __init__(self):
        # maps availability zone to dict of (subnet_id, subnet)
        self.subnets = defaultdict(dict)
        super(SubnetBackend, self).__init__()

    def get_subnet(self, subnet_id):
        for subnets in self.subnets.values():
            if subnet_id in subnets:
                return subnets[subnet_id]
        raise InvalidSubnetIdError(subnet_id)

    def create_subnet(self, vpc_id, cidr_block, availability_zone):
        subnet_id = random_subnet_id()
        self.get_vpc(vpc_id)  # Validate VPC exists

        # if this is the first subnet for an availability zone,
        # consider it the default
        default_for_az = str(availability_zone not in self.subnets).lower()
        map_public_ip_on_launch = default_for_az
        subnet = Subnet(self, subnet_id, vpc_id, cidr_block, availability_zone,
                        default_for_az, map_public_ip_on_launch)

        # AWS associates a new subnet with the default Network ACL
        self.associate_default_network_acl_with_subnet(subnet_id)
        self.subnets[availability_zone][subnet_id] = subnet
        return subnet

    def get_all_subnets(self, subnet_ids=None, filters=None):
        # Extract a list of all subnets
        matches = itertools.chain(*[x.values()
                                    for x in self.subnets.values()])
        if subnet_ids:
            matches = [sn for sn in matches
                       if sn.id in subnet_ids]
            if len(subnet_ids) > len(matches):
                unknown_ids = set(subnet_ids) - set(matches)
                raise InvalidSubnetIdError(unknown_ids)
        if filters:
            matches = generic_filter(filters, matches)

        return matches

    def delete_subnet(self, subnet_id):
        for subnets in self.subnets.values():
            if subnet_id in subnets:
                return subnets.pop(subnet_id, None)
        raise InvalidSubnetIdError(subnet_id)

    def modify_subnet_attribute(self, subnet_id, map_public_ip):
        subnet = self.get_subnet(subnet_id)
        if map_public_ip not in ('true', 'false'):
            raise InvalidParameterValueError(map_public_ip)
        subnet.map_public_ip_on_launch = map_public_ip


class SubnetRouteTableAssociation(object):
    def __init__(self, route_table_id, subnet_id):
        self.route_table_id = route_table_id
        self.subnet_id = subnet_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        route_table_id = properties['RouteTableId']
        subnet_id = properties['SubnetId']

        ec2_backend = ec2_backends[region_name]
        subnet_association = ec2_backend.create_subnet_association(
            route_table_id=route_table_id,
            subnet_id=subnet_id,
        )
        return subnet_association


class SubnetRouteTableAssociationBackend(object):
    def __init__(self):
        self.subnet_associations = {}
        super(SubnetRouteTableAssociationBackend, self).__init__()

    def create_subnet_association(self, route_table_id, subnet_id):
        subnet_association = SubnetRouteTableAssociation(
            route_table_id, subnet_id)
        self.subnet_associations["{0}:{1}".format(
            route_table_id, subnet_id)] = subnet_association
        return subnet_association


class RouteTable(TaggedEC2Resource):
    def __init__(self, ec2_backend, route_table_id, vpc_id, main=False):
        self.ec2_backend = ec2_backend
        self.id = route_table_id
        self.vpc_id = vpc_id
        self.main = main
        self.associations = {}
        self.routes = {}

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        vpc_id = properties['VpcId']
        ec2_backend = ec2_backends[region_name]
        route_table = ec2_backend.create_route_table(
            vpc_id=vpc_id,
        )
        return route_table

    @property
    def physical_resource_id(self):
        return self.id

    def get_filter_value(self, filter_name):
        if filter_name == "association.main":
            # Note: Boto only supports 'true'.
            # https://github.com/boto/boto/issues/1742
            if self.main:
                return 'true'
            else:
                return 'false'
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
            return super(RouteTable, self).get_filter_value(
                filter_name, 'DescribeRouteTables')


class RouteTableBackend(object):
    def __init__(self):
        self.route_tables = {}
        super(RouteTableBackend, self).__init__()

    def create_route_table(self, vpc_id, main=False):
        route_table_id = random_route_table_id()
        vpc = self.get_vpc(vpc_id)  # Validate VPC exists
        route_table = RouteTable(self, route_table_id, vpc_id, main=main)
        self.route_tables[route_table_id] = route_table

        # AWS creates a default local route.
        self.create_route(route_table_id, vpc.cidr_block, local=True)

        return route_table

    def get_route_table(self, route_table_id):
        route_table = self.route_tables.get(route_table_id, None)
        if not route_table:
            raise InvalidRouteTableIdError(route_table_id)
        return route_table

    def get_all_route_tables(self, route_table_ids=None, filters=None):
        route_tables = self.route_tables.values()

        if route_table_ids:
            route_tables = [
                route_table for route_table in route_tables if route_table.id in route_table_ids]
            if len(route_tables) != len(route_table_ids):
                invalid_id = list(set(route_table_ids).difference(
                    set([route_table.id for route_table in route_tables])))[0]
                raise InvalidRouteTableIdError(invalid_id)

        return generic_filter(filters, route_tables)

    def delete_route_table(self, route_table_id):
        route_table = self.get_route_table(route_table_id)
        if route_table.associations:
            raise DependencyViolationError(
                "The routeTable '{0}' has dependencies and cannot be deleted.".format(route_table_id)
            )
        self.route_tables.pop(route_table_id)
        return True

    def associate_route_table(self, route_table_id, subnet_id):
        # Idempotent if association already exists.
        route_tables_by_subnet = self.get_all_route_tables(
            filters={'association.subnet-id': [subnet_id]})
        if route_tables_by_subnet:
            for association_id, check_subnet_id in route_tables_by_subnet[0].associations.items():
                if subnet_id == check_subnet_id:
                    return association_id

        # Association does not yet exist, so create it.
        route_table = self.get_route_table(route_table_id)
        self.get_subnet(subnet_id)  # Validate subnet exists
        association_id = random_subnet_association_id()
        route_table.associations[association_id] = subnet_id
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
        route_tables_by_association_id = self.get_all_route_tables(
            filters={'association.route-table-association-id': [association_id]})
        if not route_tables_by_association_id:
            raise InvalidAssociationIdError(association_id)

        # Remove existing association, create new one.
        previous_route_table = route_tables_by_association_id[0]
        subnet_id = previous_route_table.associations.pop(association_id, None)
        return self.associate_route_table(route_table_id, subnet_id)


class Route(object):
    def __init__(self, route_table, destination_cidr_block, local=False,
                 gateway=None, instance=None, interface=None, vpc_pcx=None):
        self.id = generate_route_id(route_table.id, destination_cidr_block)
        self.route_table = route_table
        self.destination_cidr_block = destination_cidr_block
        self.local = local
        self.gateway = gateway
        self.instance = instance
        self.interface = interface
        self.vpc_pcx = vpc_pcx

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        gateway_id = properties.get('GatewayId')
        instance_id = properties.get('InstanceId')
        interface_id = properties.get('NetworkInterfaceId')
        pcx_id = properties.get('VpcPeeringConnectionId')

        route_table_id = properties['RouteTableId']
        ec2_backend = ec2_backends[region_name]
        route_table = ec2_backend.create_route(
            route_table_id=route_table_id,
            destination_cidr_block=properties.get('DestinationCidrBlock'),
            gateway_id=gateway_id,
            instance_id=instance_id,
            interface_id=interface_id,
            vpc_peering_connection_id=pcx_id,
        )
        return route_table


class RouteBackend(object):
    def __init__(self):
        super(RouteBackend, self).__init__()

    def create_route(self, route_table_id, destination_cidr_block, local=False,
                     gateway_id=None, instance_id=None, interface_id=None,
                     vpc_peering_connection_id=None):
        route_table = self.get_route_table(route_table_id)

        if interface_id:
            self.raise_not_implemented_error(
                "CreateRoute to NetworkInterfaceId")

        gateway = None
        if gateway_id:
            if EC2_RESOURCE_TO_PREFIX['vpn-gateway'] in gateway_id:
                gateway = self.get_vpn_gateway(gateway_id)
            elif EC2_RESOURCE_TO_PREFIX['internet-gateway'] in gateway_id:
                gateway = self.get_internet_gateway(gateway_id)

        route = Route(route_table, destination_cidr_block, local=local,
                      gateway=gateway,
                      instance=self.get_instance(
                          instance_id) if instance_id else None,
                      interface=None,
                      vpc_pcx=self.get_vpc_peering_connection(
                          vpc_peering_connection_id) if vpc_peering_connection_id else None)
        route_table.routes[route.id] = route
        return route

    def replace_route(self, route_table_id, destination_cidr_block,
                      gateway_id=None, instance_id=None, interface_id=None,
                      vpc_peering_connection_id=None):
        route_table = self.get_route_table(route_table_id)
        route_id = generate_route_id(route_table.id, destination_cidr_block)
        route = route_table.routes[route_id]

        if interface_id:
            self.raise_not_implemented_error(
                "ReplaceRoute to NetworkInterfaceId")

        route.gateway = None
        if gateway_id:
            if EC2_RESOURCE_TO_PREFIX['vpn-gateway'] in gateway_id:
                route.gateway = self.get_vpn_gateway(gateway_id)
            elif EC2_RESOURCE_TO_PREFIX['internet-gateway'] in gateway_id:
                route.gateway = self.get_internet_gateway(gateway_id)

        route.instance = self.get_instance(
            instance_id) if instance_id else None
        route.interface = None
        route.vpc_pcx = self.get_vpc_peering_connection(
            vpc_peering_connection_id) if vpc_peering_connection_id else None

        route_table.routes[route.id] = route
        return route

    def get_route(self, route_id):
        route_table_id, destination_cidr_block = split_route_id(route_id)
        route_table = self.get_route_table(route_table_id)
        return route_table.get(route_id)

    def delete_route(self, route_table_id, destination_cidr_block):
        route_table = self.get_route_table(route_table_id)
        route_id = generate_route_id(route_table_id, destination_cidr_block)
        deleted = route_table.routes.pop(route_id, None)
        if not deleted:
            raise InvalidRouteError(route_table_id, destination_cidr_block)
        return deleted


class InternetGateway(TaggedEC2Resource):
    def __init__(self, ec2_backend):
        self.ec2_backend = ec2_backend
        self.id = random_internet_gateway_id()
        self.vpc = None

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
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
        super(InternetGatewayBackend, self).__init__()

    def create_internet_gateway(self):
        igw = InternetGateway(self)
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
        return True

    def get_internet_gateway(self, internet_gateway_id):
        igw_ids = [internet_gateway_id]
        return self.describe_internet_gateways(internet_gateway_ids=igw_ids)[0]


class VPCGatewayAttachment(BaseModel):
    def __init__(self, gateway_id, vpc_id):
        self.gateway_id = gateway_id
        self.vpc_id = vpc_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        ec2_backend = ec2_backends[region_name]
        attachment = ec2_backend.create_vpc_gateway_attachment(
            gateway_id=properties['InternetGatewayId'],
            vpc_id=properties['VpcId'],
        )
        ec2_backend.attach_internet_gateway(
            properties['InternetGatewayId'], properties['VpcId'])
        return attachment

    @property
    def physical_resource_id(self):
        return self.vpc_id


class VPCGatewayAttachmentBackend(object):
    def __init__(self):
        self.gateway_attachments = {}
        super(VPCGatewayAttachmentBackend, self).__init__()

    def create_vpc_gateway_attachment(self, vpc_id, gateway_id):
        attachment = VPCGatewayAttachment(vpc_id, gateway_id)
        self.gateway_attachments[gateway_id] = attachment
        return attachment


class SpotInstanceRequest(BotoSpotRequest, TaggedEC2Resource):
    def __init__(self, ec2_backend, spot_request_id, price, image_id, type,
                 valid_from, valid_until, launch_group, availability_zone_group,
                 key_name, security_groups, user_data, instance_type, placement,
                 kernel_id, ramdisk_id, monitoring_enabled, subnet_id, spot_fleet_id,
                 **kwargs):
        super(SpotInstanceRequest, self).__init__(**kwargs)
        ls = LaunchSpecification()
        self.ec2_backend = ec2_backend
        self.launch_specification = ls
        self.id = spot_request_id
        self.state = "open"
        self.price = price
        self.type = type
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

        if security_groups:
            for group_name in security_groups:
                group = self.ec2_backend.get_security_group_from_name(
                    group_name)
                if group:
                    ls.groups.append(group)
        else:
            # If not security groups, add the default
            default_group = self.ec2_backend.get_security_group_from_name(
                "default")
            ls.groups.append(default_group)

        self.instance = self.launch_instance()

    def get_filter_value(self, filter_name):
        if filter_name == 'state':
            return self.state
        elif filter_name == 'spot-instance-request-id':
            return self.id
        else:
            return super(SpotInstanceRequest, self).get_filter_value(
                filter_name, 'DescribeSpotInstanceRequests')

    def launch_instance(self):
        reservation = self.ec2_backend.add_instances(
            image_id=self.launch_specification.image_id, count=1, user_data=self.user_data,
            instance_type=self.launch_specification.instance_type,
            subnet_id=self.launch_specification.subnet_id,
            key_name=self.launch_specification.key_name,
            security_group_names=[],
            security_group_ids=self.launch_specification.groups,
            spot_fleet_id=self.spot_fleet_id,
        )
        instance = reservation.instances[0]
        return instance


@six.add_metaclass(Model)
class SpotRequestBackend(object):
    def __init__(self):
        self.spot_instance_requests = {}
        super(SpotRequestBackend, self).__init__()

    def request_spot_instances(self, price, image_id, count, type, valid_from,
                               valid_until, launch_group, availability_zone_group,
                               key_name, security_groups, user_data,
                               instance_type, placement, kernel_id, ramdisk_id,
                               monitoring_enabled, subnet_id, spot_fleet_id=None):
        requests = []
        for _ in range(count):
            spot_request_id = random_spot_request_id()
            request = SpotInstanceRequest(self,
                                          spot_request_id, price, image_id, type, valid_from, valid_until,
                                          launch_group, availability_zone_group, key_name, security_groups,
                                          user_data, instance_type, placement, kernel_id, ramdisk_id,
                                          monitoring_enabled, subnet_id, spot_fleet_id)
            self.spot_instance_requests[spot_request_id] = request
            requests.append(request)
        return requests

    @Model.prop('SpotInstanceRequest')
    def describe_spot_instance_requests(self, filters=None):
        requests = self.spot_instance_requests.values()

        return generic_filter(filters, requests)

    def cancel_spot_instance_requests(self, request_ids):
        requests = []
        for request_id in request_ids:
            requests.append(self.spot_instance_requests.pop(request_id))
        return requests


class SpotFleetLaunchSpec(object):
    def __init__(self, ebs_optimized, group_set, iam_instance_profile, image_id,
                 instance_type, key_name, monitoring, spot_price, subnet_id, user_data,
                 weighted_capacity):
        self.ebs_optimized = ebs_optimized
        self.group_set = group_set
        self.iam_instance_profile = iam_instance_profile
        self.image_id = image_id
        self.instance_type = instance_type
        self.key_name = key_name
        self.monitoring = monitoring
        self.spot_price = spot_price
        self.subnet_id = subnet_id
        self.user_data = user_data
        self.weighted_capacity = float(weighted_capacity)


class SpotFleetRequest(TaggedEC2Resource):
    def __init__(self, ec2_backend, spot_fleet_request_id, spot_price,
                 target_capacity, iam_fleet_role, allocation_strategy, launch_specs):

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
            self.launch_specs.append(SpotFleetLaunchSpec(
                ebs_optimized=spec['ebs_optimized'],
                group_set=[val for key, val in spec.items(
                ) if key.startswith("group_set")],
                iam_instance_profile=spec.get('iam_instance_profile._arn'),
                image_id=spec['image_id'],
                instance_type=spec['instance_type'],
                key_name=spec.get('key_name'),
                monitoring=spec.get('monitoring._enabled'),
                spot_price=spec.get('spot_price', self.spot_price),
                subnet_id=spec['subnet_id'],
                user_data=spec.get('user_data'),
                weighted_capacity=spec['weighted_capacity'],
            )
            )

        self.spot_requests = []
        self.create_spot_requests(self.target_capacity)

    @property
    def physical_resource_id(self):
        return self.id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json[
            'Properties']['SpotFleetRequestConfigData']
        ec2_backend = ec2_backends[region_name]

        spot_price = properties.get('SpotPrice')
        target_capacity = properties['TargetCapacity']
        iam_fleet_role = properties['IamFleetRole']
        allocation_strategy = properties['AllocationStrategy']
        launch_specs = properties["LaunchSpecifications"]
        launch_specs = [
            dict([(camelcase_to_underscores(key), val)
                  for key, val in launch_spec.items()])
            for launch_spec
            in launch_specs
        ]

        spot_fleet_request = ec2_backend.request_spot_fleet(spot_price,
                                                            target_capacity, iam_fleet_role, allocation_strategy,
                                                            launch_specs)

        return spot_fleet_request

    def get_launch_spec_counts(self, weight_to_add):
        weight_map = defaultdict(int)

        weight_so_far = 0
        if self.allocation_strategy == 'diversified':
            launch_spec_index = 0
            while True:
                launch_spec = self.launch_specs[
                    launch_spec_index % len(self.launch_specs)]
                weight_map[launch_spec] += 1
                weight_so_far += launch_spec.weighted_capacity
                if weight_so_far >= weight_to_add:
                    break
                launch_spec_index += 1
        else:  # lowestPrice
            cheapest_spec = sorted(
                # FIXME: change `+inf` to the on demand price scaled to weighted capacity when it's not present
                self.launch_specs, key=lambda spec: float(spec.spot_price or '+inf'))[0]
            weight_so_far = weight_to_add + (weight_to_add % cheapest_spec.weighted_capacity)
            weight_map[cheapest_spec] = int(
                weight_so_far // cheapest_spec.weighted_capacity)

        return weight_map, weight_so_far

    def create_spot_requests(self, weight_to_add):
        weight_map, added_weight = self.get_launch_spec_counts(weight_to_add)
        for launch_spec, count in weight_map.items():
            requests = self.ec2_backend.request_spot_instances(
                price=launch_spec.spot_price,
                image_id=launch_spec.image_id,
                count=count,
                type="persistent",
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
                if spec.instance_type == instance.instance_type and spec.subnet_id == instance.subnet_id:
                    break

            if new_fulfilled_capacity - spec.weighted_capacity < self.target_capacity:
                continue
            new_fulfilled_capacity -= spec.weighted_capacity
            instance_ids.append(instance.id)

        self.spot_requests = [req for req in self.spot_requests if req.instance.id not in instance_ids]
        self.ec2_backend.terminate_instances(instance_ids)


class SpotFleetBackend(object):
    def __init__(self):
        self.spot_fleet_requests = {}
        super(SpotFleetBackend, self).__init__()

    def request_spot_fleet(self, spot_price, target_capacity, iam_fleet_role,
                           allocation_strategy, launch_specs):

        spot_fleet_request_id = random_spot_fleet_request_id()
        request = SpotFleetRequest(self, spot_fleet_request_id, spot_price,
                                   target_capacity, iam_fleet_role, allocation_strategy, launch_specs)
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
                request for request in requests if request.id in spot_fleet_request_ids]

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

    def modify_spot_fleet_request(self, spot_fleet_request_id, target_capacity, terminate_instances):
        if target_capacity < 0:
            raise ValueError('Cannot reduce spot fleet capacity below 0')
        spot_fleet_request = self.spot_fleet_requests[spot_fleet_request_id]
        delta = target_capacity - spot_fleet_request.fulfilled_capacity
        spot_fleet_request.target_capacity = target_capacity
        if delta > 0:
            spot_fleet_request.create_spot_requests(delta)
        elif delta < 0 and terminate_instances == 'Default':
            spot_fleet_request.terminate_instances()
        return True


class ElasticAddress(object):
    def __init__(self, domain, address=None):
        if address:
            self.public_ip = address
        else:
            self.public_ip = random_ip()
        self.allocation_id = random_eip_allocation_id() if domain == "vpc" else None
        self.domain = domain
        self.instance = None
        self.eni = None
        self.association_id = None

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        ec2_backend = ec2_backends[region_name]

        properties = cloudformation_json.get('Properties')
        instance_id = None
        if properties:
            domain = properties.get('Domain')
            eip = ec2_backend.allocate_address(
                domain=domain if domain else 'standard')
            instance_id = properties.get('InstanceId')
        else:
            eip = ec2_backend.allocate_address(domain='standard')

        if instance_id:
            instance = ec2_backend.get_instance_by_id(instance_id)
            ec2_backend.associate_address(instance, address=eip.public_ip)

        return eip

    @property
    def physical_resource_id(self):
        return self.public_ip

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'AllocationId':
            return self.allocation_id
        raise UnformattedGetAttTemplateException()

    def get_filter_value(self, filter_name):
        if filter_name == 'allocation-id':
            return self.allocation_id
        elif filter_name == 'association-id':
            return self.association_id
        elif filter_name == 'domain':
            return self.domain
        elif filter_name == 'instance-id' and self.instance:
            return self.instance.id
        elif filter_name == 'network-interface-id' and self.eni:
            return self.eni.id
        elif filter_name == 'private-ip-address' and self.eni:
            return self.eni.private_ip_address
        elif filter_name == 'public-ip':
            return self.public_ip
        else:
            # TODO: implement network-interface-owner-id
            raise FilterNotImplementedError(filter_name, 'DescribeAddresses')


class ElasticAddressBackend(object):
    def __init__(self):
        self.addresses = []
        super(ElasticAddressBackend, self).__init__()

    def allocate_address(self, domain, address=None):
        if domain not in ['standard', 'vpc']:
            raise InvalidDomainError(domain)
        if address:
            address = ElasticAddress(domain, address)
        else:
            address = ElasticAddress(domain)
        self.addresses.append(address)
        return address

    def address_by_ip(self, ips):
        eips = [address for address in self.addresses
                if address.public_ip in ips]

        # TODO: Trim error message down to specific invalid address.
        if not eips or len(ips) > len(eips):
            raise InvalidAddressError(ips)

        return eips

    def address_by_allocation(self, allocation_ids):
        eips = [address for address in self.addresses
                if address.allocation_id in allocation_ids]

        # TODO: Trim error message down to specific invalid id.
        if not eips or len(allocation_ids) > len(eips):
            raise InvalidAllocationIdError(allocation_ids)

        return eips

    def address_by_association(self, association_ids):
        eips = [address for address in self.addresses
                if address.association_id in association_ids]

        # TODO: Trim error message down to specific invalid id.
        if not eips or len(association_ids) > len(eips):
            raise InvalidAssociationIdError(association_ids)

        return eips

    def associate_address(self, instance=None, eni=None, address=None, allocation_id=None, reassociate=False):
        eips = []
        if address:
            eips = self.address_by_ip([address])
        elif allocation_id:
            eips = self.address_by_allocation([allocation_id])
        eip = eips[0]

        new_instance_association = bool(instance and (
            not eip.instance or eip.instance.id == instance.id))
        new_eni_association = bool(
            eni and (not eip.eni or eni.id == eip.eni.id))

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
        matches = self.addresses
        if allocation_ids:
            matches = [addr for addr in matches
                       if addr.allocation_id in allocation_ids]
            if len(allocation_ids) > len(matches):
                unknown_ids = set(allocation_ids) - set(matches)
                raise InvalidAllocationIdError(unknown_ids)
        if public_ips:
            matches = [addr for addr in matches
                       if addr.public_ip in public_ips]
            if len(public_ips) > len(matches):
                unknown_ips = set(allocation_ids) - set(matches)
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
    def __init__(self, ec2_backend, domain_name_servers=None, domain_name=None,
                 ntp_servers=None, netbios_name_servers=None,
                 netbios_node_type=None):
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
        if filter_name == 'dhcp-options-id':
            return self.id
        elif filter_name == 'key':
            return list(self._options.keys())
        elif filter_name == 'value':
            values = [item for item in list(self._options.values()) if item]
            return itertools.chain(*values)
        else:
            return super(DHCPOptionsSet, self).get_filter_value(
                filter_name, 'DescribeDhcpOptions')

    @property
    def options(self):
        return self._options


class DHCPOptionsSetBackend(object):
    def __init__(self):
        self.dhcp_options_sets = {}
        super(DHCPOptionsSetBackend, self).__init__()

    def associate_dhcp_options(self, dhcp_options, vpc):
        dhcp_options.vpc = vpc
        vpc.dhcp_options = dhcp_options

    def create_dhcp_options(
            self, domain_name_servers=None, domain_name=None,
            ntp_servers=None, netbios_name_servers=None,
            netbios_node_type=None):

        NETBIOS_NODE_TYPES = [1, 2, 4, 8]

        for field_value in domain_name_servers, ntp_servers, netbios_name_servers:
            if field_value and len(field_value) > 4:
                raise InvalidParameterValueError(",".join(field_value))

        if netbios_node_type and int(netbios_node_type[0]) not in NETBIOS_NODE_TYPES:
            raise InvalidParameterValueError(netbios_node_type)

        options = DHCPOptionsSet(
            self, domain_name_servers, domain_name, ntp_servers,
            netbios_name_servers, netbios_node_type
        )
        self.dhcp_options_sets[options.id] = options
        return options

    def describe_dhcp_options(self, options_ids=None):
        options_sets = []
        for option_id in options_ids or []:
            if option_id in self.dhcp_options_sets:
                options_sets.append(self.dhcp_options_sets[option_id])
            else:
                raise InvalidDHCPOptionsIdError(option_id)
        return options_sets or self.dhcp_options_sets.values()

    def delete_dhcp_options_set(self, options_id):
        if not (options_id and options_id.startswith('dopt-')):
            raise MalformedDHCPOptionsIdError(options_id)

        if options_id in self.dhcp_options_sets:
            if self.dhcp_options_sets[options_id].vpc:
                raise DependencyViolationError(
                    "Cannot delete assigned DHCP options.")
            self.dhcp_options_sets.pop(options_id)
        else:
            raise InvalidDHCPOptionsIdError(options_id)
        return True

    def get_all_dhcp_options(self, dhcp_options_ids=None, filters=None):
        dhcp_options_sets = self.dhcp_options_sets.values()

        if dhcp_options_ids:
            dhcp_options_sets = [
                dhcp_options_set for dhcp_options_set in dhcp_options_sets if dhcp_options_set.id in dhcp_options_ids]
            if len(dhcp_options_sets) != len(dhcp_options_ids):
                invalid_id = list(set(dhcp_options_ids).difference(
                    set([dhcp_options_set.id for dhcp_options_set in dhcp_options_sets])))[0]
                raise InvalidDHCPOptionsIdError(invalid_id)

        return generic_filter(filters, dhcp_options_sets)


class VPNConnection(TaggedEC2Resource):
    def __init__(self, ec2_backend, id, type,
                 customer_gateway_id, vpn_gateway_id):
        self.ec2_backend = ec2_backend
        self.id = id
        self.state = 'available'
        self.customer_gateway_configuration = {}
        self.type = type
        self.customer_gateway_id = customer_gateway_id
        self.vpn_gateway_id = vpn_gateway_id
        self.tunnels = None
        self.options = None
        self.static_routes = None

    def get_filter_value(self, filter_name):
            return super(VPNConnection, self).get_filter_value(
                filter_name, 'DescribeVpnConnections')


class VPNConnectionBackend(object):
    def __init__(self):
        self.vpn_connections = {}
        super(VPNConnectionBackend, self).__init__()

    def create_vpn_connection(self, type, customer_gateway_id,
                              vpn_gateway_id,
                              static_routes_only=None):
        vpn_connection_id = random_vpn_connection_id()
        if static_routes_only:
            pass
        vpn_connection = VPNConnection(
            self, id=vpn_connection_id, type=type,
            customer_gateway_id=customer_gateway_id,
            vpn_gateway_id=vpn_gateway_id
        )
        self.vpn_connections[vpn_connection.id] = vpn_connection
        return vpn_connection

    def delete_vpn_connection(self, vpn_connection_id):

        if vpn_connection_id in self.vpn_connections:
            self.vpn_connections.pop(vpn_connection_id)
        else:
            raise InvalidVpnConnectionIdError(vpn_connection_id)
        return True

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
            vpn_connections = [vpn_connection for vpn_connection in vpn_connections
                               if vpn_connection.id in vpn_connection_ids]
            if len(vpn_connections) != len(vpn_connection_ids):
                invalid_id = list(set(vpn_connection_ids).difference(
                    set([vpn_connection.id for vpn_connection in vpn_connections])))[0]
                raise InvalidVpnConnectionIdError(invalid_id)

        return generic_filter(filters, vpn_connections)


class NetworkAclBackend(object):
    def __init__(self):
        self.network_acls = {}
        super(NetworkAclBackend, self).__init__()

    def get_network_acl(self, network_acl_id):
        network_acl = self.network_acls.get(network_acl_id, None)
        if not network_acl:
            raise InvalidNetworkAclIdError(network_acl_id)
        return network_acl

    def create_network_acl(self, vpc_id, default=False):
        network_acl_id = random_network_acl_id()
        self.get_vpc(vpc_id)
        network_acl = NetworkAcl(self, network_acl_id, vpc_id, default)
        self.network_acls[network_acl_id] = network_acl
        return network_acl

    def get_all_network_acls(self, network_acl_ids=None, filters=None):
        network_acls = self.network_acls.values()

        if network_acl_ids:
            network_acls = [network_acl for network_acl in network_acls
                            if network_acl.id in network_acl_ids]
            if len(network_acls) != len(network_acl_ids):
                invalid_id = list(set(network_acl_ids).difference(
                    set([network_acl.id for network_acl in network_acls])))[0]
                raise InvalidRouteTableIdError(invalid_id)

        return generic_filter(filters, network_acls)

    def delete_network_acl(self, network_acl_id):
        deleted = self.network_acls.pop(network_acl_id, None)
        if not deleted:
            raise InvalidNetworkAclIdError(network_acl_id)
        return deleted

    def create_network_acl_entry(self, network_acl_id, rule_number,
                                 protocol, rule_action, egress, cidr_block,
                                 icmp_code, icmp_type, port_range_from,
                                 port_range_to):

        network_acl_entry = NetworkAclEntry(self, network_acl_id, rule_number,
                                            protocol, rule_action, egress,
                                            cidr_block, icmp_code, icmp_type,
                                            port_range_from, port_range_to)

        network_acl = self.get_network_acl(network_acl_id)
        network_acl.network_acl_entries.append(network_acl_entry)
        return network_acl_entry

    def delete_network_acl_entry(self, network_acl_id, rule_number, egress):
        network_acl = self.get_network_acl(network_acl_id)
        entry = next(entry for entry in network_acl.network_acl_entries
                     if entry.egress == egress and entry.rule_number == rule_number)
        if entry is not None:
            network_acl.network_acl_entries.remove(entry)
        return entry

    def replace_network_acl_entry(self, network_acl_id, rule_number, protocol, rule_action, egress,
                                  cidr_block, icmp_code, icmp_type, port_range_from, port_range_to):

        self.delete_network_acl_entry(network_acl_id, rule_number, egress)
        network_acl_entry = self.create_network_acl_entry(network_acl_id, rule_number,
                                      protocol, rule_action, egress,
                                      cidr_block, icmp_code, icmp_type,
                                      port_range_from, port_range_to)
        return network_acl_entry

    def replace_network_acl_association(self, association_id,
                                        network_acl_id):

        # lookup existing association for subnet and delete it
        default_acl = next(value for key, value in self.network_acls.items()
                           if association_id in value.associations.keys())

        subnet_id = None
        for key, value in default_acl.associations.items():
            if key == association_id:
                subnet_id = default_acl.associations[key].subnet_id
                del default_acl.associations[key]
                break

        new_assoc_id = random_network_acl_subnet_association_id()
        association = NetworkAclAssociation(self,
                                            new_assoc_id,
                                            subnet_id,
                                            network_acl_id)
        new_acl = self.get_network_acl(network_acl_id)
        new_acl.associations[new_assoc_id] = association
        return association

    def associate_default_network_acl_with_subnet(self, subnet_id):
        association_id = random_network_acl_subnet_association_id()
        acl = next(acl for acl in self.network_acls.values() if acl.default)
        acl.associations[association_id] = NetworkAclAssociation(self, association_id,
                                                                 subnet_id, acl.id)


class NetworkAclAssociation(object):
    def __init__(self, ec2_backend, new_association_id,
                 subnet_id, network_acl_id):
        self.ec2_backend = ec2_backend
        self.id = new_association_id
        self.new_association_id = new_association_id
        self.subnet_id = subnet_id
        self.network_acl_id = network_acl_id
        super(NetworkAclAssociation, self).__init__()


class NetworkAcl(TaggedEC2Resource):
    def __init__(self, ec2_backend, network_acl_id, vpc_id, default=False):
        self.ec2_backend = ec2_backend
        self.id = network_acl_id
        self.vpc_id = vpc_id
        self.network_acl_entries = []
        self.associations = {}
        self.default = 'true' if default is True else 'false'

    def get_filter_value(self, filter_name):
        if filter_name == "default":
            return self.default
        elif filter_name == "vpc-id":
            return self.vpc_id
        elif filter_name == "association.network-acl-id":
            return self.id
        elif filter_name == "association.subnet-id":
            return [assoc.subnet_id for assoc in self.associations.values()]
        else:
            return super(NetworkAcl, self).get_filter_value(
                filter_name, 'DescribeNetworkAcls')


class NetworkAclEntry(TaggedEC2Resource):
    def __init__(self, ec2_backend, network_acl_id, rule_number,
                 protocol, rule_action, egress, cidr_block,
                 icmp_code, icmp_type, port_range_from,
                 port_range_to):
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


class VpnGateway(TaggedEC2Resource):
    def __init__(self, ec2_backend, id, type):
        self.ec2_backend = ec2_backend
        self.id = id
        self.type = type
        self.attachments = {}
        super(VpnGateway, self).__init__()

    def get_filter_value(self, filter_name):
            return super(VpnGateway, self).get_filter_value(
                filter_name, 'DescribeVpnGateways')


class VpnGatewayAttachment(object):
    def __init__(self, vpc_id, state):
        self.vpc_id = vpc_id
        self.state = state
        super(VpnGatewayAttachment, self).__init__()


class VpnGatewayBackend(object):
    def __init__(self):
        self.vpn_gateways = {}
        super(VpnGatewayBackend, self).__init__()

    def create_vpn_gateway(self, type='ipsec.1'):
        vpn_gateway_id = random_vpn_gateway_id()
        vpn_gateway = VpnGateway(self, vpn_gateway_id, type)
        self.vpn_gateways[vpn_gateway_id] = vpn_gateway
        return vpn_gateway

    def get_all_vpn_gateways(self, filters=None):
        vpn_gateways = self.vpn_gateways.values()
        return generic_filter(filters, vpn_gateways)

    def get_vpn_gateway(self, vpn_gateway_id):
        vpn_gateway = self.vpn_gateways.get(vpn_gateway_id, None)
        if not vpn_gateway:
            raise InvalidVpnGatewayIdError(vpn_gateway_id)
        return vpn_gateway

    def attach_vpn_gateway(self, vpn_gateway_id, vpc_id):
        vpn_gateway = self.get_vpn_gateway(vpn_gateway_id)
        self.get_vpc(vpc_id)
        attachment = VpnGatewayAttachment(vpc_id, state='attached')
        vpn_gateway.attachments[vpc_id] = attachment
        return attachment

    def delete_vpn_gateway(self, vpn_gateway_id):
        deleted = self.vpn_gateways.pop(vpn_gateway_id, None)
        if not deleted:
            raise InvalidVpnGatewayIdError(vpn_gateway_id)
        return deleted

    def detach_vpn_gateway(self, vpn_gateway_id, vpc_id):
        vpn_gateway = self.get_vpn_gateway(vpn_gateway_id)
        self.get_vpc(vpc_id)
        detached = vpn_gateway.attachments.pop(vpc_id, None)
        if not detached:
            raise InvalidVPCIdError(vpc_id)
        return detached


class CustomerGateway(TaggedEC2Resource):
    def __init__(self, ec2_backend, id, type, ip_address, bgp_asn):
        self.ec2_backend = ec2_backend
        self.id = id
        self.type = type
        self.ip_address = ip_address
        self.bgp_asn = bgp_asn
        self.attachments = {}
        super(CustomerGateway, self).__init__()

    def get_filter_value(self, filter_name):
            return super(CustomerGateway, self).get_filter_value(
                filter_name, 'DescribeCustomerGateways')


class CustomerGatewayBackend(object):
    def __init__(self):
        self.customer_gateways = {}
        super(CustomerGatewayBackend, self).__init__()

    def create_customer_gateway(self, type='ipsec.1', ip_address=None, bgp_asn=None):
        customer_gateway_id = random_customer_gateway_id()
        customer_gateway = CustomerGateway(
            self, customer_gateway_id, type, ip_address, bgp_asn)
        self.customer_gateways[customer_gateway_id] = customer_gateway
        return customer_gateway

    def get_all_customer_gateways(self, filters=None):
        customer_gateways = self.customer_gateways.values()
        return generic_filter(filters, customer_gateways)

    def get_customer_gateway(self, customer_gateway_id):
        customer_gateway = self.customer_gateways.get(
            customer_gateway_id, None)
        if not customer_gateway:
            raise InvalidCustomerGatewayIdError(customer_gateway_id)
        return customer_gateway

    def delete_customer_gateway(self, customer_gateway_id):
        deleted = self.customer_gateways.pop(customer_gateway_id, None)
        if not deleted:
            raise InvalidCustomerGatewayIdError(customer_gateway_id)
        return deleted


class NatGateway(object):
    def __init__(self, backend, subnet_id, allocation_id):
        # public properties
        self.id = random_nat_gateway_id()
        self.subnet_id = subnet_id
        self.allocation_id = allocation_id
        self.state = 'available'
        self.private_ip = random_private_ip()

        # protected properties
        self._created_at = datetime.utcnow()
        self._backend = backend
        # NOTE: this is the core of NAT Gateways creation
        self._eni = self._backend.create_network_interface(
            backend.get_subnet(self.subnet_id), self.private_ip)

        # associate allocation with ENI
        self._backend.associate_address(
            eni=self._eni, allocation_id=self.allocation_id)

    @property
    def vpc_id(self):
        subnet = self._backend.get_subnet(self.subnet_id)
        return subnet.vpc_id

    @property
    def create_time(self):
        return iso_8601_datetime_with_milliseconds(self._created_at)

    @property
    def network_interface_id(self):
        return self._eni.id

    @property
    def public_ip(self):
        eips = self._backend.address_by_allocation([self.allocation_id])
        return eips[0].public_ip

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        ec2_backend = ec2_backends[region_name]
        nat_gateway = ec2_backend.create_nat_gateway(
            cloudformation_json['Properties']['SubnetId'],
            cloudformation_json['Properties']['AllocationId'],
        )
        return nat_gateway


class NatGatewayBackend(object):
    def __init__(self):
        self.nat_gateways = {}
        super(NatGatewayBackend, self).__init__()

    def get_all_nat_gateways(self, filters):
        return self.nat_gateways.values()

    def create_nat_gateway(self, subnet_id, allocation_id):
        nat_gateway = NatGateway(self, subnet_id, allocation_id)
        self.nat_gateways[nat_gateway.id] = nat_gateway
        return nat_gateway

    def delete_nat_gateway(self, nat_gateway_id):
        return self.nat_gateways.pop(nat_gateway_id)


class EC2Backend(BaseBackend, InstanceBackend, TagBackend, EBSBackend,
                 RegionsAndZonesBackend, SecurityGroupBackend, AmiBackend,
                 VPCBackend, SubnetBackend, SubnetRouteTableAssociationBackend,
                 NetworkInterfaceBackend, VPNConnectionBackend,
                 VPCPeeringConnectionBackend,
                 RouteTableBackend, RouteBackend, InternetGatewayBackend,
                 VPCGatewayAttachmentBackend, SpotFleetBackend,
                 SpotRequestBackend, ElasticAddressBackend, KeyPairBackend,
                 DHCPOptionsSetBackend, NetworkAclBackend, VpnGatewayBackend,
                 CustomerGatewayBackend, NatGatewayBackend):
    def __init__(self, region_name):
        self.region_name = region_name
        super(EC2Backend, self).__init__()

        # Default VPC exists by default, which is the current behavior
        # of EC2-VPC. See for detail:
        #
        #   docs.aws.amazon.com/AmazonVPC/latest/UserGuide/default-vpc.html
        #
        if not self.vpcs:
            vpc = self.create_vpc('172.31.0.0/16')
        else:
            # For now this is included for potential
            # backward-compatibility issues
            vpc = self.vpcs.values()[0]

        # Create default subnet for each availability zone
        ip, _ = vpc.cidr_block.split('/')
        ip = ip.split('.')
        ip[2] = 0

        for zone in self.describe_availability_zones():
            az_name = zone.name
            cidr_block = '.'.join(str(i) for i in ip) + '/20'
            self.create_subnet(vpc.id, cidr_block, availability_zone=az_name)
            ip[2] += 16

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    # Use this to generate a proper error template response when in a response
    # handler.
    def raise_error(self, code, message):
        raise EC2ClientError(code, message)

    def raise_not_implemented_error(self, blurb):
        raise MotoNotImplementedError(blurb)

    def do_resources_exist(self, resource_ids):
        for resource_id in resource_ids:
            resource_prefix = get_prefix(resource_id)
            if resource_prefix == EC2_RESOURCE_TO_PREFIX['customer-gateway']:
                self.get_customer_gateway(customer_gateway_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['dhcp-options']:
                self.describe_dhcp_options(options_ids=[resource_id])
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['image']:
                self.describe_images(ami_ids=[resource_id])
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['instance']:
                self.get_instance_by_id(instance_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['internet-gateway']:
                self.describe_internet_gateways(
                    internet_gateway_ids=[resource_id])
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['network-acl']:
                self.get_all_network_acls()
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['network-interface']:
                self.describe_network_interfaces(
                    filters={'network-interface-id': resource_id})
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['reserved-instance']:
                self.raise_not_implemented_error('DescribeReservedInstances')
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['route-table']:
                self.get_route_table(route_table_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['security-group']:
                self.describe_security_groups(group_ids=[resource_id])
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['snapshot']:
                self.get_snapshot(snapshot_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['spot-instance-request']:
                self.describe_spot_instance_requests(
                    filters={'spot-instance-request-id': resource_id})
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['subnet']:
                self.get_subnet(subnet_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['volume']:
                self.get_volume(volume_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['vpc']:
                self.get_vpc(vpc_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['vpc-peering-connection']:
                self.get_vpc_peering_connection(vpc_pcx_id=resource_id)
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['vpn-connection']:
                self.describe_vpn_connections(vpn_connection_ids=[resource_id])
            elif resource_prefix == EC2_RESOURCE_TO_PREFIX['vpn-gateway']:
                self.get_vpn_gateway(vpn_gateway_id=resource_id)
        return True


ec2_backends = {region.name: EC2Backend(region.name)
                for region in RegionsAndZonesBackend.regions}
