from collections import defaultdict

from boto.ec2.instance import Instance, InstanceState, Reservation

from moto.core import BaseBackend
from .utils import random_instance_id, random_reservation_id


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


class EC2Backend(BaseBackend, InstanceBackend, TagBackend):
    pass


ec2_backend = EC2Backend()
