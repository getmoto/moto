from collections import defaultdict

from boto.ec2.instance import Instance, InstanceState, Reservation

from moto.core import BaseBackend
from .utils import (
    random_ami_id,
    random_instance_id,
    random_reservation_id,
    random_security_group_id,
    random_snapshot_id,
    random_volume_id,
)


class InstanceBackend(object):

    def __init__(self):
        self.reservations = {}
        super(InstanceBackend, self).__init__()

    def get_instance(self, instance_id):
        for instance in self.all_instances():
            if instance.id == instance_id:
                return instance

    def add_instances(self, count):
        new_reservation = Reservation()
        new_reservation.id = random_reservation_id()
        for index in range(count):
            new_instance = Instance()
            new_instance.id = random_instance_id()
            new_instance._state = InstanceState(0, "pending")
            new_reservation.instances.append(new_instance)
        self.reservations[new_reservation.id] = new_reservation
        return new_reservation

    def start_instances(self, instance_ids):
        started_instances = []
        for instance in self.all_instances():
            if instance.id in instance_ids:
                instance._state = InstanceState(0, 'pending')
                started_instances.append(instance)

        return started_instances

    def stop_instances(self, instance_ids):
        stopped_instances = []
        for instance in self.all_instances():
            if instance.id in instance_ids:
                instance._state = InstanceState(64, 'stopping')
                stopped_instances.append(instance)

        return stopped_instances

    def terminate_instances(self, instance_ids):
        terminated_instances = []
        for instance in self.all_instances():
            if instance.id in instance_ids:
                instance._state = InstanceState(32, 'shutting-down')
                terminated_instances.append(instance)

        return terminated_instances

    def reboot_instances(self, instance_ids):
        rebooted_instances = []
        for instance in self.all_instances():
            if instance.id in instance_ids:
                # TODO double check instances go to pending when reboot
                instance._state = InstanceState(0, 'pending')
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

    def all_reservations(self):
        return self.reservations.values()


class TagBackend(object):

    def __init__(self):
        self.tags = defaultdict(dict)
        super(TagBackend, self).__init__()

    def create_tag(self, resource_id, key, value):
        self.tags[resource_id][key] = value
        return value

    def delete_tag(self, resource_id, key):
        return self.tags[resource_id].pop(key)

    def describe_tags(self):
        results = []
        for resource_id, tags in self.tags.iteritems():
            ami = 'ami' in resource_id
            for key, value in tags.iteritems():
                result = {
                    'resource_id': resource_id,
                    'key': key,
                    'value': value,
                    'resource_type': 'image' if ami else 'instance',
                }
                results.append(result)
        return results


class Ami(object):
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
        if not instance:
            return None
        ami =  Ami(ami_id, instance, name, description)
        self.amis[ami_id] = ami
        return ami

    def describe_images(self):
        return self.amis.values()

    def deregister_image(self, ami_id):
        if ami_id in self.amis:
            self.amis.pop(ami_id)
            return True
        return False


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
        return "{}-{}-{}-{}-{}".format(
                self.ip_protocol,
                self.from_port,
                self.to_port,
                self.ip_ranges,
                self.source_groups
            )

    def __eq__(self, other):
        return self.unique_representation == other.unique_representation


class SecurityGroup(object):
    def __init__(self, group_id, name, description):
        self.id = group_id
        self.name = name
        self.description = description
        self.ingress_rules = []
        self.egress_rules = []


class SecurityGroupBackend(object):

    def __init__(self):
        self.groups = {}
        super(SecurityGroupBackend, self).__init__()

    def create_security_group(self, name, description):
        group_id = random_security_group_id()
        existing_group = self.get_security_group_from_name(name)
        if existing_group:
            return None
        group =  SecurityGroup(group_id, name, description)
        self.groups[group_id] = group
        return group

    def describe_security_groups(self):
        return self.groups.values()

    def delete_security_group(self, name_or_group_id):
        if name_or_group_id in self.groups:
            # Group Id
            return self.groups.pop(name_or_group_id)
        else:
            # Group Name
            group = self.get_security_group_from_name(name_or_group_id)
            if group:
                return self.groups.pop(group.id)

    def get_security_group_from_name(self, name):
        for group_id, group in self.groups.iteritems():
            if group.name == name:
                return group

    def authorize_security_group_ingress(self, group_name, ip_protocol, from_port, to_port, ip_ranges=None, source_group_names=None):
        group = self.get_security_group_from_name(group_name)
        source_groups = []
        for source_group_name in source_group_names:
            source_groups.append(self.get_security_group_from_name(source_group_name))

        security_rule = SecurityRule(ip_protocol, from_port, to_port, ip_ranges, source_groups)
        group.ingress_rules.append(security_rule)

    def revoke_security_group_ingress(self, group_name, ip_protocol, from_port, to_port, ip_ranges=None, source_group_names=None):
        group = self.get_security_group_from_name(group_name)
        source_groups = []
        for source_group_name in source_group_names:
            source_groups.append(self.get_security_group_from_name(source_group_name))

        security_rule = SecurityRule(ip_protocol, from_port, to_port, ip_ranges, source_groups)
        if security_rule in group.ingress_rules:
            group.ingress_rules.remove(security_rule)
            return security_rule
        return False


class VolumeAttachment(object):
    def __init__(self, volume, instance, device):
        self.volume = volume
        self.instance = instance
        self.device = device


class Volume(object):
    def __init__(self, volume_id, size, zone):
        self.id = volume_id
        self.size = size
        self.zone = zone
        self.attachment = None

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

    def delete_volume(self, volume_id):
        if volume_id in self.volumes:
            return self.volumes.pop(volume_id)
        return False

    def attach_volume(self, volume_id, instance_id, device_path):
        volume = self.volumes.get(volume_id)
        instance = self.get_instance(instance_id)

        if not volume or not instance:
            return False

        volume.attachment = VolumeAttachment(volume, instance, device_path)
        return volume.attachment

    def detach_volume(self, volume_id, instance_id, device_path):
        volume = self.volumes.get(volume_id)
        instance = self.get_instance(instance_id)

        if not volume or not instance:
            return False

        old_attachment = volume.attachment
        volume.attachment = None
        return old_attachment

    def create_snapshot(self, volume_id, description):
        snapshot_id = random_snapshot_id()
        volume = self.volumes.get(volume_id)
        snapshot = Snapshot(snapshot_id, volume, description)
        self.snapshots[snapshot_id] = snapshot
        return snapshot

    def describe_snapshots(self):
        return self.snapshots.values()

    def delete_snapshot(self, snapshot_id):
        if snapshot_id in self.snapshots:
            return self.snapshots.pop(snapshot_id)
        return False


class EC2Backend(BaseBackend, InstanceBackend, TagBackend, AmiBackend, RegionsAndZonesBackend, SecurityGroupBackend, EBSBackend):
    pass


ec2_backend = EC2Backend()

