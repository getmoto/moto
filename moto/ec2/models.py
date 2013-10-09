import copy
from collections import defaultdict

from boto.ec2.instance import Instance as BotoInstance, Reservation

from moto.core import BaseBackend
from .exceptions import InvalidIdError
from .utils import (
    random_ami_id,
    random_instance_id,
    random_reservation_id,
    random_security_group_id,
    random_snapshot_id,
    random_spot_request_id,
    random_subnet_id,
    random_volume_id,
    random_vpc_id,
    random_eip_association_id,
    random_eip_allocation_id,
    random_ip,
)


class InstanceState(object):
    def __init__(self, name='pending', code=0):
        self.name = name
        self.code = code


class Instance(BotoInstance):
    def __init__(self, image_id, user_data):
        super(Instance, self).__init__()
        self.id = random_instance_id()
        self.image_id = image_id
        self._state = InstanceState("running", 16)
        self.user_data = user_data

    def start(self):
        self._state.name = "running"
        self._state.code = 16

    def stop(self):
        self._state.name = "stopped"
        self._state.code = 80

    def terminate(self):
        self._state.name = "terminated"
        self._state.code = 48

    def reboot(self):
        self._state.name = "running"
        self._state.code = 16

    def get_tags(self):
        tags = ec2_backend.describe_tags(self.id)
        return tags


class InstanceBackend(object):

    def __init__(self):
        self.reservations = {}
        super(InstanceBackend, self).__init__()

    def get_instance(self, instance_id):
        for instance in self.all_instances():
            if instance.id == instance_id:
                return instance

    def add_instances(self, image_id, count, user_data):
        new_reservation = Reservation()
        new_reservation.id = random_reservation_id()
        for index in range(count):
            new_instance = Instance(
                image_id,
                user_data,
            )
            new_reservation.instances.append(new_instance)
        self.reservations[new_reservation.id] = new_reservation
        return new_reservation

    def start_instances(self, instance_ids):
        started_instances = []
        for instance in self.all_instances():
            if instance.id in instance_ids:
                instance.start()
                started_instances.append(instance)

        return started_instances

    def stop_instances(self, instance_ids):
        stopped_instances = []
        for instance in self.all_instances():
            if instance.id in instance_ids:
                instance.stop()
                stopped_instances.append(instance)

        return stopped_instances

    def terminate_instances(self, instance_ids):
        terminated_instances = []
        for instance in self.all_instances():
            if instance.id in instance_ids:
                instance.terminate()
                terminated_instances.append(instance)

        return terminated_instances

    def reboot_instances(self, instance_ids):
        rebooted_instances = []
        for instance in self.all_instances():
            if instance.id in instance_ids:
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
            raise InvalidIdError(invalid_id)
        return reservations

    def all_reservations(self, make_copy=False):
        if make_copy:
            # Return copies so that other functions can modify them with changing
            # the originals
            return [copy.deepcopy(reservation) for reservation in self.reservations.values()]
        else:
            return [reservation for reservation in self.reservations.values()]


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
        ami = Ami(ami_id, instance, name, description)
        self.amis[ami_id] = ami
        return ami

    def describe_images(self, ami_ids=None):
        if ami_ids:
            images = [image for image in self.amis.values() if image.id in ami_ids]
        else:
            images = self.amis.values()
        return images

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

    def create_security_group(self, name, description, force=False):
        group_id = random_security_group_id()
        if not force:
            existing_group = self.get_security_group_from_name(name)
            if existing_group:
                return None
        group = SecurityGroup(group_id, name, description)
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

        if name == 'default':
            # If the request is for the default group and it does not exist, create it
            default_group = ec2_backend.create_security_group("default", "The default security group", force=True)
            return default_group

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


class VPC(object):
    def __init__(self, vpc_id, cidr_block):
        self.id = vpc_id
        self.cidr_block = cidr_block


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
        return self.vpcs.get(vpc_id)

    def get_all_vpcs(self):
        return self.vpcs.values()

    def delete_vpc(self, vpc_id):
        return self.vpcs.pop(vpc_id, None)


class Subnet(object):
    def __init__(self, subnet_id, vpc, cidr_block):
        self.id = subnet_id
        self.vpc = vpc
        self.cidr_block = cidr_block


class SubnetBackend(object):
    def __init__(self):
        self.subnets = {}
        super(SubnetBackend, self).__init__()

    def create_subnet(self, vpc_id, cidr_block):
        subnet_id = random_subnet_id()
        vpc = self.get_vpc(vpc_id)
        subnet = Subnet(subnet_id, vpc, cidr_block)
        self.subnets[subnet_id] = subnet
        return subnet

    def get_all_subnets(self):
        return self.subnets.values()

    def delete_subnet(self, subnet_id):
        return self.subnets.pop(subnet_id, None)


class SpotInstanceRequest(object):
    def __init__(self, spot_request_id, price, image_id, type, valid_from,
                 valid_until, launch_group, availability_zone_group, key_name,
                 security_groups, user_data, instance_type, placement, kernel_id,
                 ramdisk_id, monitoring_enabled, subnet_id):
        self.id = spot_request_id
        self.state = "open"
        self.price = price
        self.image_id = image_id
        self.type = type
        self.valid_from = valid_from
        self.valid_until = valid_until
        self.launch_group = launch_group
        self.availability_zone_group = availability_zone_group
        self.key_name = key_name
        self.user_data = user_data
        self.instance_type = instance_type
        self.placement = placement
        self.kernel_id = kernel_id
        self.ramdisk_id = ramdisk_id
        self.monitoring_enabled = monitoring_enabled
        self.subnet_id = subnet_id

        self.security_groups = []
        if security_groups:
            for group_name in security_groups:
                group = ec2_backend.get_security_group_from_name(group_name)
                if group:
                    self.security_groups.append(group)
        else:
            # If not security groups, add the default
            default_group = ec2_backend.get_security_group_from_name("default")
            self.security_groups.append(default_group)


class SpotRequestBackend(object):
    def __init__(self):
        self.spot_instance_requests = {}
        super(SpotRequestBackend, self).__init__()

    def request_spot_instances(self, price, image_id, count, type, valid_from,
                               valid_until, launch_group, availability_zone_group,
                               key_name, security_groups, user_data,
                               instance_type, placement, kernel_id, ramdisk_id,
                               monitoring_enabled, subnet_id):
        requests = []
        for index in range(count):
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

    def describe_spot_instance_requests(self):
        return self.spot_instance_requests.values()

    def cancel_spot_instance_requests(self, request_ids):
        requests = []
        for request_id in request_ids:
            requests.append(self.spot_instance_requests.pop(request_id))
        return requests


class ElasticAddress():
    def __init__(self, domain):
        self.public_ip = random_ip()
        self.allocation_id = random_eip_allocation_id() if domain == "vpc" else None
        self.domain = domain
        self.instance = None
        self.association_id = None


class ElasticAddressBackend(object):

    def __init__(self):
        self.addresses = []
        super(ElasticAddressBackend, self).__init__()

    def allocate_address(self, domain):
        address = ElasticAddress(domain)
        self.addresses.append(address)
        return address

    def address_by_ip(self, ips):
        return [address for address in self.addresses
                if address.public_ip in ips]

    def address_by_allocation(self, allocation_ids):
        return [address for address in self.addresses
                if address.allocation_id in allocation_ids]

    def address_by_association(self, association_ids):
        return [address for address in self.addresses
                if address.association_id in association_ids]

    def associate_address(self, instance, address=None, allocation_id=None, reassociate=False):
        eips = []
        if address:
            eips = self.address_by_ip([address])
        elif allocation_id:
            eips = self.address_by_allocation([allocation_id])
        eip = eips[0] if len(eips) > 0 else None

        if eip and eip.instance is None or reassociate:
            eip.instance = instance
            if eip.domain == "vpc":
                eip.association_id = random_eip_association_id()
            return eip
        else:
            return None

    def describe_addresses(self):
        return self.addresses

    def disassociate_address(self, address=None, association_id=None):
        eips = []
        if address:
            eips = self.address_by_ip([address])
        elif association_id:
            eips = self.address_by_association([association_id])

        if eips:
            eip = eips[0]
            eip.instance = None
            eip.association_id = None
            return True
        else:
            return False

    def release_address(self, address=None, allocation_id=None):
        eips = []
        if address:
            eips = self.address_by_ip([address])
        elif allocation_id:
            eips = self.address_by_allocation([allocation_id])

        if eips:
            eip = eips[0]
            self.disassociate_address(address=eip.public_ip)
            eip.allocation_id = None
            self.addresses.remove(eip)
            return True
        else:
            return False


class EC2Backend(BaseBackend, InstanceBackend, TagBackend, AmiBackend,
                 RegionsAndZonesBackend, SecurityGroupBackend, EBSBackend,
                 VPCBackend, SubnetBackend, SpotRequestBackend, ElasticAddressBackend):
    pass


ec2_backend = EC2Backend()
