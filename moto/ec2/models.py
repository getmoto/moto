import copy
import itertools
from collections import defaultdict

from boto.ec2.instance import Instance as BotoInstance, Reservation
from boto.ec2.blockdevicemapping import BlockDeviceMapping, BlockDeviceType
from boto.ec2.spotinstancerequest import SpotInstanceRequest as BotoSpotRequest
from boto.ec2.launchspecification import LaunchSpecification

from moto.core import BaseBackend
from moto.core.models import Model
from .exceptions import (
    EC2ClientError,
    DependencyViolationError,
    MissingParameterError,
    InvalidParameterValueError,
    InvalidDHCPOptionsIdError,
    MalformedDHCPOptionsIdError,
    InvalidKeyPairNameError,
    InvalidKeyPairDuplicateError,
    InvalidInternetGatewayIdError,
    GatewayNotAttachedError,
    ResourceAlreadyAssociatedError,
    InvalidVPCIdError,
    InvalidSubnetIdError,
    InvalidSecurityGroupDuplicateError,
    InvalidSecurityGroupNotFoundError,
    InvalidPermissionNotFoundError,
    InvalidInstanceIdError,
    InvalidAMIIdError,
    InvalidSnapshotIdError,
    InvalidVolumeIdError,
    InvalidVolumeAttachmentError,
    InvalidDomainError,
    InvalidAddressError,
    InvalidAllocationIdError,
    InvalidAssociationIdError,
    InvalidVPCPeeringConnectionIdError,
    InvalidVPCPeeringConnectionStateTransitionError
)
from .utils import (
    random_ami_id,
    random_dhcp_option_id,
    random_eip_allocation_id,
    random_eip_association_id,
    random_internet_gateway_id,
    random_instance_id,
    random_internet_gateway_id,
    random_ip,
    random_key_pair,
    random_reservation_id,
    random_route_table_id,
    random_security_group_id,
    random_snapshot_id,
    random_spot_request_id,
    random_subnet_id,
    random_volume_id,
    random_vpc_id,
    random_vpc_peering_connection_id,
)


class InstanceState(object):
    def __init__(self, name='pending', code=0):
        self.name = name
        self.code = code


class TaggedEC2Instance(object):
    def get_tags(self, *args, **kwargs):
        tags = ec2_backend.describe_tags(self.id)
        return tags


class Instance(BotoInstance, TaggedEC2Instance):
    def __init__(self, image_id, user_data, security_groups, **kwargs):
        super(Instance, self).__init__()
        self.id = random_instance_id()
        self.image_id = image_id
        self._state = InstanceState("running", 16)
        self.user_data = user_data
        self.security_groups = security_groups
        self.instance_type = kwargs.get("instance_type", "m1.small")
        self.subnet_id = kwargs.get("subnet_id")
        self.key_name = kwargs.get("key_name")

        self.block_device_mapping = BlockDeviceMapping()
        self.block_device_mapping['/dev/sda1'] = BlockDeviceType()

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        security_group_ids = properties.get('SecurityGroups', [])
        group_names = [ec2_backend.get_security_group_from_id(group_id).name for group_id in security_group_ids]

        reservation = ec2_backend.add_instances(
            image_id=properties['ImageId'],
            user_data=properties.get('UserData'),
            count=1,
            security_group_names=group_names,
            instance_type=properties.get("InstanceType", "m1.small"),
            subnet_id=properties.get("SubnetId"),
            key_name=properties.get("KeyName"),
        )
        return reservation.instances[0]

    @property
    def physical_resource_id(self):
        return self.id

    def start(self, *args, **kwargs):
        self._state.name = "running"
        self._state.code = 16

    def stop(self, *args, **kwargs):
        self._state.name = "stopped"
        self._state.code = 80

    def terminate(self, *args, **kwargs):
        self._state.name = "terminated"
        self._state.code = 48

    def reboot(self, *args, **kwargs):
        self._state.name = "running"
        self._state.code = 16


class InstanceBackend(object):

    def __init__(self):
        self.reservations = {}
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
        for index in range(count):
            new_instance = Instance(
                image_id,
                user_data,
                security_groups,
                **kwargs
            )
            new_reservation.instances.append(new_instance)
        self.reservations[new_reservation.id] = new_reservation
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

    def describe_instance_attribute(self, instance_id, key):
        instance = self.get_instance(instance_id)
        value = getattr(instance, key)
        return instance, value

    def all_instances(self):
        instances = []
        for reservation in self.all_reservations():
            for instance in reservation.instances:
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

    def get_reservations_by_instance_ids(self, instance_ids):
        """ Go through all of the reservations and filter to only return those
        associated with the given instance_ids.
        """
        reservations = []
        for reservation in self.all_reservations(make_copy=True):
            reservation_instance_ids = [instance.id for instance in reservation.instances]
            matching_reservation = any(instance_id in reservation_instance_ids for instance_id in instance_ids)
            if matching_reservation:
                # We need to make a copy of the reservation because we have to modify the
                # instances to limit to those requested
                reservation.instances = [instance for instance in reservation.instances if instance.id in instance_ids]
                reservations.append(reservation)
        found_instance_ids = [instance.id for reservation in reservations for instance in reservation.instances]
        if len(found_instance_ids) != len(instance_ids):
            invalid_id = list(set(instance_ids).difference(set(found_instance_ids)))[0]
            raise InvalidInstanceIdError(invalid_id)
        return reservations

    def all_reservations(self, make_copy=False):
        if make_copy:
            # Return copies so that other functions can modify them with changing
            # the originals
            return [copy.deepcopy(reservation) for reservation in self.reservations.values()]
        else:
            return [reservation for reservation in self.reservations.values()]


class KeyPairBackend(object):

    def __init__(self):
        self.keypairs = defaultdict(dict)
        super(KeyPairBackend, self).__init__()

    def create_key_pair(self, name):
        if name in self.keypairs:
            raise InvalidKeyPairDuplicateError(name)
        self.keypairs[name] = keypair = random_key_pair()
        keypair['name'] = name
        return keypair

    def delete_key_pair(self, name):
        if name in self.keypairs:
            self.keypairs.pop(name)
        return True

    def describe_key_pairs(self, filter_names=None):
        results = []
        for name, keypair in self.keypairs.iteritems():
            if not filter_names or name in filter_names:
                keypair['name'] = name
                results.append(keypair)

        # TODO: Trim error message down to specific invalid name.
        if filter_names and len(filter_names) > len(results):
            raise InvalidKeyPairNameError(filter_names)

        return results


class TagBackend(object):

    def __init__(self):
        self.tags = defaultdict(dict)
        super(TagBackend, self).__init__()

    def create_tag(self, resource_id, key, value):
        self.tags[resource_id][key] = value
        return value

    def delete_tag(self, resource_id, key):
        return self.tags[resource_id].pop(key)

    def describe_tags(self, filter_resource_ids=None):
        results = []
        for resource_id, tags in self.tags.iteritems():
            ami = 'ami' in resource_id
            for key, value in tags.iteritems():
                if not filter_resource_ids or resource_id in filter_resource_ids:
                    # If we're not filtering, or we are filtering and this
                    # resource id is in the filter list, add this tag
                    result = {
                        'resource_id': resource_id,
                        'key': key,
                        'value': value,
                        'resource_type': 'image' if ami else 'instance',
                    }
                    results.append(result)
        return results


class Ami(TaggedEC2Instance):
    def __init__(self, ami_id, instance, name, description):
        self.id = ami_id
        self.instance = instance
        self.instance_id = instance.id
        self.name = name
        self.description = description

        self.virtualization_type = instance.virtualization_type
        self.kernel_id = instance.kernel


class AmiBackend(object):
    def __init__(self):
        self.amis = {}
        super(AmiBackend, self).__init__()

    def create_image(self, instance_id, name, description):
        # TODO: check that instance exists and pull info from it.
        ami_id = random_ami_id()
        instance = self.get_instance(instance_id)
        ami = Ami(ami_id, instance, name, description)
        self.amis[ami_id] = ami
        return ami

    def describe_images(self, ami_ids=()):
        images = []
        for ami_id in ami_ids:
            if ami_id in self.amis:
                images.append(self.amis[ami_id])
            else:
                raise InvalidAMIIdError(ami_id)
        return images or self.amis.values()

    def deregister_image(self, ami_id):
        if ami_id in self.amis:
            self.amis.pop(ami_id)
            return True
        raise InvalidAMIIdError(ami_id)


class Region(object):
    def __init__(self, name, endpoint):
        self.name = name
        self.endpoint = endpoint


class Zone(object):
    def __init__(self, name, region_name):
        self.name = name
        self.region_name = region_name


class RegionsAndZonesBackend(object):
    regions = [
        Region("eu-west-1", "ec2.eu-west-1.amazonaws.com"),
        Region("sa-east-1", "ec2.sa-east-1.amazonaws.com"),
        Region("us-east-1", "ec2.us-east-1.amazonaws.com"),
        Region("ap-northeast-1", "ec2.ap-northeast-1.amazonaws.com"),
        Region("us-west-2", "ec2.us-west-2.amazonaws.com"),
        Region("us-west-1", "ec2.us-west-1.amazonaws.com"),
        Region("ap-southeast-1", "ec2.ap-southeast-1.amazonaws.com"),
        Region("ap-southeast-2", "ec2.ap-southeast-2.amazonaws.com"),
    ]

    # TODO: cleanup. For now, pretend everything is us-east-1. 'merica.
    zones = [
        Zone("us-east-1a", "us-east-1"),
        Zone("us-east-1b", "us-east-1"),
        Zone("us-east-1c", "us-east-1"),
        Zone("us-east-1d", "us-east-1"),
        Zone("us-east-1e", "us-east-1"),
    ]

    def describe_regions(self):
        return self.regions

    def describe_availability_zones(self):
        return self.zones

    def get_zone_by_name(self, name):
        for zone in self.zones:
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


class SecurityGroup(object):
    def __init__(self, group_id, name, description, vpc_id=None):
        self.id = group_id
        self.name = name
        self.description = description
        self.ingress_rules = []
        self.egress_rules = []
        self.vpc_id = vpc_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        vpc_id = properties.get('VpcId')
        security_group = ec2_backend.create_security_group(
            name=resource_name,
            description=properties.get('GroupDescription'),
            vpc_id=vpc_id,
        )

        for ingress_rule in properties.get('SecurityGroupIngress', []):
            source_group_id = ingress_rule.get('SourceSecurityGroupId')

            ec2_backend.authorize_security_group_ingress(
                group_name=security_group.name,
                group_id=security_group.id,
                ip_protocol=ingress_rule['IpProtocol'],
                from_port=ingress_rule['FromPort'],
                to_port=ingress_rule['ToPort'],
                ip_ranges=ingress_rule.get('CidrIp'),
                source_group_ids=[source_group_id],
                vpc_id=vpc_id,
            )

        return security_group

    @property
    def physical_resource_id(self):
        return self.id


class SecurityGroupBackend(object):

    def __init__(self):
        # the key in the dict group is the vpc_id or None (non-vpc)
        self.groups = defaultdict(dict)
        super(SecurityGroupBackend, self).__init__()

    def create_security_group(self, name, description, vpc_id=None, force=False):
        if not description:
            raise MissingParameterError('GroupDescription')

        group_id = random_security_group_id()
        if not force:
            existing_group = self.get_security_group_from_name(name, vpc_id)
            if existing_group:
                raise InvalidSecurityGroupDuplicateError(name)
        group = SecurityGroup(group_id, name, description, vpc_id=vpc_id)

        self.groups[vpc_id][group_id] = group
        return group

    def describe_security_groups(self):
        return itertools.chain(*[x.values() for x in self.groups.values()])

    def delete_security_group(self, name=None, group_id=None):
        if group_id:
            # loop over all the SGs, find the right one
            for vpc in self.groups.values():
                if group_id in vpc:
                    return vpc.pop(group_id)
            raise InvalidSecurityGroupNotFoundError(group_id)
        elif name:
            # Group Name.  Has to be in standard EC2, VPC needs to be identified by group_id
            group = self.get_security_group_from_name(name)
            if group:
                return self.groups[None].pop(group.id)
            raise InvalidSecurityGroupNotFoundError(name)

    def get_security_group_from_id(self, group_id):
        # 2 levels of chaining necessary since it's a complex structure
        all_groups = itertools.chain.from_iterable([x.values() for x in self.groups.values()])

        for group in all_groups:
            if group.id == group_id:
                return group

    def get_security_group_from_name(self, name, vpc_id=None):
        for group_id, group in self.groups[vpc_id].iteritems():
            if group.name == name:
                return group

        if name == 'default':
            # If the request is for the default group and it does not exist, create it
            default_group = ec2_backend.create_security_group("default", "The default security group", force=True)
            return default_group

    def authorize_security_group_ingress(self,
                                         group_name,
                                         group_id,
                                         ip_protocol,
                                         from_port,
                                         to_port,
                                         ip_ranges,
                                         source_group_names=None,
                                         source_group_ids=None,
                                         vpc_id=None):
        # to auth a group in a VPC you need the group_id the name isn't enough

        if group_name:
            group = self.get_security_group_from_name(group_name, vpc_id)
        elif group_id:
            group = self.get_security_group_from_id(group_id)

        if ip_ranges and not isinstance(ip_ranges, list):
            ip_ranges = [ip_ranges]

        source_group_names = source_group_names if source_group_names else []
        source_group_ids = source_group_ids if source_group_ids else []

        source_groups = []
        for source_group_name in source_group_names:
            source_group = self.get_security_group_from_name(source_group_name, vpc_id)
            if source_group:
                source_groups.append(source_group)

        # for VPCs
        for source_group_id in source_group_ids:
            source_group = self.get_security_group_from_id(source_group_id)
            if source_group:
                source_groups.append(source_group)

        security_rule = SecurityRule(ip_protocol, from_port, to_port, ip_ranges, source_groups)
        group.ingress_rules.append(security_rule)

    def revoke_security_group_ingress(self,
                                      group_name,
                                      group_id,
                                      ip_protocol,
                                      from_port,
                                      to_port,
                                      ip_ranges,
                                      source_group_names=None,
                                      source_group_ids=None,
                                      vpc_id=None):

        if group_name:
            group = self.get_security_group_from_name(group_name, vpc_id)
        elif group_id:
            group = self.get_security_group_from_id(group_id)

        source_groups = []
        for source_group_name in source_group_names:
            source_group = self.get_security_group_from_name(source_group_name, vpc_id)
            if source_group:
                source_groups.append(source_group)

        for source_group_id in source_group_ids:
            source_group = self.get_security_group_from_id(source_group_id)
            if source_group:
                source_groups.append(source_group)

        security_rule = SecurityRule(ip_protocol, from_port, to_port, ip_ranges, source_groups)
        if security_rule in group.ingress_rules:
            group.ingress_rules.remove(security_rule)
            return security_rule

        raise InvalidPermissionNotFoundError()


class VolumeAttachment(object):
    def __init__(self, volume, instance, device):
        self.volume = volume
        self.instance = instance
        self.device = device

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        instance_id = properties['InstanceId']
        volume_id = properties['VolumeId']

        attachment = ec2_backend.attach_volume(
            volume_id=volume_id,
            instance_id=instance_id,
            device_path=properties['Device'],
        )
        return attachment


class Volume(object):
    def __init__(self, volume_id, size, zone):
        self.id = volume_id
        self.size = size
        self.zone = zone
        self.attachment = None

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

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


class Snapshot(object):
    def __init__(self, snapshot_id, volume, description):
        self.id = snapshot_id
        self.volume = volume
        self.description = description


class EBSBackend(object):
    def __init__(self):
        self.volumes = {}
        self.attachments = {}
        self.snapshots = {}
        super(EBSBackend, self).__init__()

    def create_volume(self, size, zone_name):
        volume_id = random_volume_id()
        zone = self.get_zone_by_name(zone_name)
        volume = Volume(volume_id, size, zone)
        self.volumes[volume_id] = volume
        return volume

    def describe_volumes(self):
        return self.volumes.values()

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

        volume.attachment = VolumeAttachment(volume, instance, device_path)
        return volume.attachment

    def detach_volume(self, volume_id, instance_id, device_path):
        volume = self.get_volume(volume_id)
        instance = self.get_instance(instance_id)

        old_attachment = volume.attachment
        if not old_attachment:
            raise InvalidVolumeAttachmentError(volume_id, instance_id)

        volume.attachment = None
        return old_attachment

    def create_snapshot(self, volume_id, description):
        snapshot_id = random_snapshot_id()
        volume = self.get_volume(volume_id)
        snapshot = Snapshot(snapshot_id, volume, description)
        self.snapshots[snapshot_id] = snapshot
        return snapshot

    def describe_snapshots(self):
        return self.snapshots.values()

    def delete_snapshot(self, snapshot_id):
        if snapshot_id in self.snapshots:
            return self.snapshots.pop(snapshot_id)
        raise InvalidSnapshotIdError(snapshot_id)


class VPC(TaggedEC2Instance):
    def __init__(self, vpc_id, cidr_block):
        self.id = vpc_id
        self.cidr_block = cidr_block
        self.dhcp_options = None

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        vpc = ec2_backend.create_vpc(
            cidr_block=properties['CidrBlock'],
        )
        return vpc

    @property
    def physical_resource_id(self):
        return self.id


class VPCBackend(object):
    def __init__(self):
        self.vpcs = {}
        super(VPCBackend, self).__init__()

    def create_vpc(self, cidr_block):
        vpc_id = random_vpc_id()
        vpc = VPC(vpc_id, cidr_block)
        self.vpcs[vpc_id] = vpc
        return vpc

    def get_vpc(self, vpc_id):
        if vpc_id not in self.vpcs:
            raise InvalidVPCIdError(vpc_id)
        return self.vpcs.get(vpc_id)

    def get_all_vpcs(self):
        return self.vpcs.values()

    def delete_vpc(self, vpc_id):
        vpc = self.vpcs.pop(vpc_id, None)
        if not vpc:
            raise InvalidVPCIdError(vpc_id)
        if vpc.dhcp_options:
            vpc.dhcp_options.vpc = None
            self.delete_dhcp_options_set(vpc.dhcp_options.id)
            vpc.dhcp_options = None
        return vpc


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


class VPCPeeringConnection(TaggedEC2Instance):
    def __init__(self, vpc_pcx_id, vpc, peer_vpc):
        self.id = vpc_pcx_id
        self.vpc = vpc
        self.peer_vpc = peer_vpc
        self._status = VPCPeeringConnectionStatus()

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        vpc = self.get_vpc(properties['VpcId'])
        peer_vpc = self.get_vpc(properties['PeerVpcId'])

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


class Subnet(TaggedEC2Instance):
    def __init__(self, subnet_id, vpc_id, cidr_block):
        self.id = subnet_id
        self.vpc_id = vpc_id
        self.cidr_block = cidr_block

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        vpc_id = properties['VpcId']
        subnet = ec2_backend.create_subnet(
            vpc_id=vpc_id,
            cidr_block=properties['CidrBlock']
        )
        return subnet

    @property
    def physical_resource_id(self):
        return self.id


class SubnetBackend(object):
    def __init__(self):
        self.subnets = {}
        super(SubnetBackend, self).__init__()

    def create_subnet(self, vpc_id, cidr_block):
        subnet_id = random_subnet_id()
        subnet = Subnet(subnet_id, vpc_id, cidr_block)
        self.subnets[subnet_id] = subnet
        return subnet

    def get_all_subnets(self):
        return self.subnets.values()

    def delete_subnet(self, subnet_id):
        deleted = self.subnets.pop(subnet_id, None)
        if not deleted:
            raise InvalidSubnetIdError(subnet_id)
        return deleted


class SubnetRouteTableAssociation(object):
    def __init__(self, route_table_id, subnet_id):
        self.route_table_id = route_table_id
        self.subnet_id = subnet_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        route_table_id = properties['RouteTableId']
        subnet_id = properties['SubnetId']

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
        subnet_association = SubnetRouteTableAssociation(route_table_id, subnet_id)
        self.subnet_associations["{0}:{1}".format(route_table_id, subnet_id)] = subnet_association
        return subnet_association


class RouteTable(object):
    def __init__(self, route_table_id, vpc_id):
        self.id = route_table_id
        self.vpc_id = vpc_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        vpc_id = properties['VpcId']
        route_table = ec2_backend.create_route_table(
            vpc_id=vpc_id,
        )
        return route_table

    @property
    def physical_resource_id(self):
        return self.id


class RouteTableBackend(object):
    def __init__(self):
        self.route_tables = {}
        super(RouteTableBackend, self).__init__()

    def create_route_table(self, vpc_id):
        route_table_id = random_route_table_id()
        route_table = RouteTable(route_table_id, vpc_id)
        self.route_tables[route_table_id] = route_table
        return route_table


class Route(object):
    def __init__(self, route_table_id, destination_cidr_block, gateway_id):
        self.route_table_id = route_table_id
        self.destination_cidr_block = destination_cidr_block
        self.gateway_id = gateway_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        gateway_id = properties.get('GatewayId')
        route_table_id = properties['RouteTableId']
        route_table = ec2_backend.create_route(
            route_table_id=route_table_id,
            destination_cidr_block=properties['DestinationCidrBlock'],
            gateway_id=gateway_id,
        )
        return route_table


class RouteBackend(object):
    def __init__(self):
        self.routes = {}
        super(RouteBackend, self).__init__()

    def create_route(self, route_table_id, destination_cidr_block, gateway_id):
        route = Route(route_table_id, destination_cidr_block, gateway_id)
        self.routes[destination_cidr_block] = route
        return route


class InternetGateway(TaggedEC2Instance):
    def __init__(self):
        self.id = random_internet_gateway_id()
        self.vpc = None

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        return ec2_backend.create_internet_gateway()

    @property
    def physical_resource_id(self):
        return self.id


class InternetGatewayBackend(object):
    def __init__(self):
        self.internet_gateways = {}
        super(InternetGatewayBackend, self).__init__()

    def create_internet_gateway(self):
        igw = InternetGateway()
        self.internet_gateways[igw.id] = igw
        return igw

    def describe_internet_gateways(self, internet_gateway_ids=None):
        igws = []
        for igw_id in internet_gateway_ids or []:
            if igw_id in self.internet_gateways:
                igws.append(self.internet_gateways[igw_id])
            else:
                raise InvalidInternetGatewayIdError(igw_id)
        return igws or self.internet_gateways.values()

    def delete_internet_gateway(self, internet_gateway_id):
        igw_ids = [internet_gateway_id]
        igw = self.describe_internet_gateways(internet_gateway_ids=igw_ids)[0]
        if igw.vpc:
            raise DependencyViolationError(
                "{0} is being utilized by {1}"
                .format(internet_gateway_id, igw.vpc.id)
            )
        self.internet_gateways.pop(internet_gateway_id)
        return True

    def detach_internet_gateway(self, internet_gateway_id, vpc_id):
        igw_ids = [internet_gateway_id]
        igw = self.describe_internet_gateways(internet_gateway_ids=igw_ids)[0]
        if not igw.vpc or igw.vpc.id != vpc_id:
            raise GatewayNotAttachedError(internet_gateway_id, vpc_id)
        igw.vpc = None
        return True

    def attach_internet_gateway(self, internet_gateway_id, vpc_id):
        igw_ids = [internet_gateway_id]
        igw = self.describe_internet_gateways(internet_gateway_ids=igw_ids)[0]
        if igw.vpc:
            raise ResourceAlreadyAssociatedError(internet_gateway_id)
        vpc = self.get_vpc(vpc_id)
        igw.vpc = vpc
        return True


class VPCGatewayAttachment(object):
    def __init__(self, gateway_id, vpc_id):
        self.gateway_id = gateway_id
        self.vpc_id = vpc_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        return ec2_backend.create_vpc_gateway_attachment(
            gateway_id=properties['InternetGatewayId'],
            vpc_id=properties['VpcId'],
        )

    @property
    def physical_resource_id(self):
        return self.id


class VPCGatewayAttachmentBackend(object):
    def __init__(self):
        self.gateway_attachments = {}
        super(VPCGatewayAttachmentBackend, self).__init__()

    def create_vpc_gateway_attachment(self, vpc_id, gateway_id):
        attachment = VPCGatewayAttachment(vpc_id, gateway_id)
        self.gateway_attachments[gateway_id] = attachment
        return attachment


class SpotInstanceRequest(BotoSpotRequest):
    def __init__(self, spot_request_id, price, image_id, type, valid_from,
                 valid_until, launch_group, availability_zone_group, key_name,
                 security_groups, user_data, instance_type, placement, kernel_id,
                 ramdisk_id, monitoring_enabled, subnet_id, **kwargs):
        super(SpotInstanceRequest, self).__init__(**kwargs)
        ls = LaunchSpecification()
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

        if security_groups:
            for group_name in security_groups:
                group = ec2_backend.get_security_group_from_name(group_name)
                if group:
                    ls.groups.append(group)
        else:
            # If not security groups, add the default
            default_group = ec2_backend.get_security_group_from_name("default")
            ls.groups.append(default_group)


class SpotRequestBackend(object):
    __metaclass__ = Model

    def __init__(self):
        self.spot_instance_requests = {}
        super(SpotRequestBackend, self).__init__()

    def request_spot_instances(self, price, image_id, count, type, valid_from,
                               valid_until, launch_group, availability_zone_group,
                               key_name, security_groups, user_data,
                               instance_type, placement, kernel_id, ramdisk_id,
                               monitoring_enabled, subnet_id):
        requests = []
        for _ in range(count):
            spot_request_id = random_spot_request_id()
            request = SpotInstanceRequest(
                spot_request_id, price, image_id, type, valid_from, valid_until,
                launch_group, availability_zone_group, key_name, security_groups,
                user_data, instance_type, placement, kernel_id, ramdisk_id,
                monitoring_enabled, subnet_id
            )
            self.spot_instance_requests[spot_request_id] = request
            requests.append(request)
        return requests

    @Model.prop('SpotInstanceRequest')
    def describe_spot_instance_requests(self):
        return self.spot_instance_requests.values()

    def cancel_spot_instance_requests(self, request_ids):
        requests = []
        for request_id in request_ids:
            requests.append(self.spot_instance_requests.pop(request_id))
        return requests


class ElasticAddress(object):
    def __init__(self, domain):
        self.public_ip = random_ip()
        self.allocation_id = random_eip_allocation_id() if domain == "vpc" else None
        self.domain = domain
        self.instance = None
        self.association_id = None

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        eip = ec2_backend.allocate_address(
            domain=properties['Domain']
        )

        instance_id = properties.get('InstanceId')
        if instance_id:
            instance = ec2_backend.get_instance_by_id(instance_id)
            ec2_backend.associate_address(instance, eip.public_ip)

        return eip

    @property
    def physical_resource_id(self):
        return self.allocation_id


class ElasticAddressBackend(object):

    def __init__(self):
        self.addresses = []
        super(ElasticAddressBackend, self).__init__()

    def allocate_address(self, domain):
        if domain not in ['standard', 'vpc']:
            raise InvalidDomainError(domain)

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

    def associate_address(self, instance, address=None, allocation_id=None, reassociate=False):
        eips = []
        if address:
            eips = self.address_by_ip([address])
        elif allocation_id:
            eips = self.address_by_allocation([allocation_id])
        eip = eips[0]

        if eip.instance and not reassociate:
            raise ResourceAlreadyAssociatedError(eip.public_ip)

        eip.instance = instance
        if eip.domain == "vpc":
            eip.association_id = random_eip_association_id()
        return eip

    def describe_addresses(self):
        return self.addresses

    def disassociate_address(self, address=None, association_id=None):
        eips = []
        if address:
            eips = self.address_by_ip([address])
        elif association_id:
            eips = self.address_by_association([association_id])
        eip = eips[0]

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


class DHCPOptionsSet(TaggedEC2Instance):
    def __init__(self, domain_name_servers=None, domain_name=None,
                 ntp_servers=None, netbios_name_servers=None,
                 netbios_node_type=None):
        self._options = {
            "domain-name-servers": domain_name_servers,
            "domain-name": domain_name,
            "ntp-servers": ntp_servers,
            "netbios-name-servers": netbios_name_servers,
            "netbios-node-type": netbios_node_type,
        }
        self.id = random_dhcp_option_id()
        self.vpc = None

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

        if netbios_node_type and netbios_node_type[0] not in NETBIOS_NODE_TYPES:
            raise InvalidParameterValueError(netbios_node_type)

        options = DHCPOptionsSet(
            domain_name_servers, domain_name, ntp_servers,
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
                raise DependencyViolationError("Cannot delete assigned DHCP options.")
            self.dhcp_options_sets.pop(options_id)
        else:
            raise InvalidDHCPOptionsIdError(options_id)
        return True


class EC2Backend(BaseBackend, InstanceBackend, TagBackend, AmiBackend,
                 RegionsAndZonesBackend, SecurityGroupBackend, EBSBackend,
                 VPCBackend, SubnetBackend, SubnetRouteTableAssociationBackend,
                 VPCPeeringConnectionBackend,
                 RouteTableBackend, RouteBackend, InternetGatewayBackend,
                 VPCGatewayAttachmentBackend, SpotRequestBackend,
                 ElasticAddressBackend, KeyPairBackend, DHCPOptionsSetBackend):

    # Use this to generate a proper error template response when in a response handler.
    def raise_error(self, code, message):
        raise EC2ClientError(code, message)


ec2_backend = EC2Backend()
