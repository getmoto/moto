from collections import defaultdict

from boto.ec2.instance import Instance, InstanceState, Reservation

from moto.core import BaseBackend
from .utils import random_instance_id, random_reservation_id, random_ami_id, random_security_group_id


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

    def get_image(self, ami_id):
        return self.amis[ami_id]

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


class SecurityGroup(object):
    def __init__(self, group_id, name, description):
        self.id = group_id
        self.name = name
        self.description = description


class SecurityGroupBackend(object):

    def __init__(self):
        self.groups = {}

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

class EC2Backend(BaseBackend, InstanceBackend, TagBackend, AmiBackend, RegionsAndZonesBackend, SecurityGroupBackend):
    pass


ec2_backend = EC2Backend()



# {
# #'Instances': ['DescribeInstanceAttribute', 'DescribeInstances', '\n\t\t\tDescribeInstanceStatus\n\t\t', 'ImportInstance', 'ModifyInstanceAttribute', 'RebootInstances', 'ReportInstanceStatus', 'ResetInstanceAttribute', 'RunInstances', 'StartInstances', 'StopInstances', 'TerminateInstances'],
# #'Tags': ['CreateTags', 'DeleteTags', 'DescribeTags'],
# 'IP Addresses': ['AssignPrivateIpAddresses', 'UnassignPrivateIpAddresses'],
# 'Monitoring': ['MonitorInstances', 'UnmonitorInstances'],
# 'Reserved Instances': ['CancelReservedInstancesListing', 'CreateReservedInstancesListing', 'DescribeReservedInstances', 'DescribeReservedInstancesListings', 'DescribeReservedInstancesOfferings', 'PurchaseReservedInstancesOffering'],
# 'VPN Connections (Amazon VPC)': ['CreateVpnConnection', 'DeleteVpnConnection', 'DescribeVpnConnections'],
# 'DHCP Options (Amazon VPC)': ['AssociateDhcpOptions', 'CreateDhcpOptions', 'DeleteDhcpOptions', 'DescribeDhcpOptions'],
# 'Network ACLs (Amazon VPC)': ['CreateNetworkAcl', 'CreateNetworkAclEntry', 'DeleteNetworkAcl', 'DeleteNetworkAclEntry', 'DescribeNetworkAcls', 'ReplaceNetworkAclAssociation', 'ReplaceNetworkAclEntry'],
# 'Elastic Block Store': ['AttachVolume', 'CopySnapshot', 'CreateSnapshot', 'CreateVolume', 'DeleteSnapshot', 'DeleteVolume', 'DescribeSnapshotAttribute', 'DescribeSnapshots', 'DescribeVolumes', 'DescribeVolumeAttribute', 'DescribeVolumeStatus', 'DetachVolume', 'EnableVolumeIO', 'ImportVolume', 'ModifySnapshotAttribute', 'ModifyVolumeAttribute', 'ResetSnapshotAttribute'],
# 'Customer Gateways (Amazon VPC)': ['CreateCustomerGateway', 'DeleteCustomerGateway', 'DescribeCustomerGateways'],
# 'Subnets (Amazon VPC)': ['CreateSubnet', 'DeleteSubnet', 'DescribeSubnets'],
# 'AMIs': ['CreateImage', 'DeregisterImage', 'DescribeImageAttribute', 'DescribeImages', 'ModifyImageAttribute', 'RegisterImage', 'ResetImageAttribute'],
# 'Virtual Private Gateways (Amazon VPC)': ['AttachVpnGateway', 'CreateVpnGateway', 'DeleteVpnGateway', 'DescribeVpnGateways', 'DetachVpnGateway'],
# 'Availability Zones and Regions': ['DescribeAvailabilityZones', 'DescribeRegions'],
# 'VPCs (Amazon VPC)': ['CreateVpc', 'DeleteVpc', 'DescribeVpcs'],
# 'Windows': ['BundleInstance', 'CancelBundleTask', 'DescribeBundleTasks', 'GetPasswordData'],
# 'VM Import': ['CancelConversionTask', 'DescribeConversionTasks', 'ImportInstance', 'ImportVolume'],
# 'Placement Groups': ['CreatePlacementGroup', 'DeletePlacementGroup', 'DescribePlacementGroups'],
# 'Key Pairs': ['CreateKeyPair', 'DeleteKeyPair', 'DescribeKeyPairs', 'ImportKeyPair'],
# 'Amazon DevPay': ['ConfirmProductInstance'],
# 'Internet Gateways (Amazon VPC)': ['AttachInternetGateway', 'CreateInternetGateway', 'DeleteInternetGateway', 'DescribeInternetGateways', 'DetachInternetGateway'],
# 'Route Tables (Amazon VPC)': ['AssociateRouteTable', 'CreateRoute', 'CreateRouteTable', 'DeleteRoute', 'DeleteRouteTable', 'DescribeRouteTables', 'DisassociateRouteTable', 'ReplaceRoute', 'ReplaceRouteTableAssociation'],
# 'Elastic Network Interfaces (Amazon VPC)': ['AttachNetworkInterface', 'CreateNetworkInterface', 'DeleteNetworkInterface', 'DescribeNetworkInterfaceAttribute', 'DescribeNetworkInterfaces', 'DetachNetworkInterface', 'ModifyNetworkInterfaceAttribute', 'ResetNetworkInterfaceAttribute'],
# 'Elastic IP Addresses': ['AllocateAddress', 'AssociateAddress', 'DescribeAddresses', 'DisassociateAddress', 'ReleaseAddress'],
# 'Security Groups': ['AuthorizeSecurityGroupEgress', 'AuthorizeSecurityGroupIngress', 'CreateSecurityGroup', 'DeleteSecurityGroup', 'DescribeSecurityGroups', 'RevokeSecurityGroupEgress', 'RevokeSecurityGroupIngress'],
# 'General': ['GetConsoleOutput'],
# 'VM Export': ['CancelExportTask', 'CreateInstanceExportTask', 'DescribeExportTasks'],
# 'Spot Instances': ['CancelSpotInstanceRequests', 'CreateSpotDatafeedSubscription', 'DeleteSpotDatafeedSubscription', 'DescribeSpotDatafeedSubscription', 'DescribeSpotInstanceRequests', 'DescribeSpotPriceHistory', 'RequestSpotInstances']
# }