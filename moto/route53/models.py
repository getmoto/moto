from __future__ import unicode_literals
from moto.core import BaseBackend
from moto.core.utils import get_random_hex


class FakeZone(object):

    def __init__(self, name, id_):
        self.name = name
        self.id = id_
        self.rrsets = []

    def add_rrset(self, name, rrset):
        self.rrsets.append(rrset)

    def delete_rrset(self, name):
        self.rrsets = [record_set for record_set in self.rrsets if record_set['Name'] != name]

    @property
    def physical_resource_id(self):
        return self.name

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']
        name = properties["Name"]

        hosted_zone = route53_backend.create_hosted_zone(name)
        return hosted_zone


class RecordSetGroup(object):
    def __init__(self, record_sets):
        self.record_sets = record_sets

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        zone_name = properties["HostedZoneName"]
        hosted_zone = route53_backend.get_hosted_zone_by_name(zone_name)
        record_sets = properties["RecordSets"]
        for record_set in record_sets:
            hosted_zone.add_rrset(record_set["Name"], record_set)

        record_set_group = RecordSetGroup(record_sets)
        return record_set_group


class Route53Backend(BaseBackend):

    def __init__(self):
        self.zones = {}

    def create_hosted_zone(self, name):
        new_id = get_random_hex()
        new_zone = FakeZone(name, new_id)
        self.zones[new_id] = new_zone
        return new_zone

    def get_all_hosted_zones(self):
        return self.zones.values()

    def get_hosted_zone(self, id_):
        return self.zones.get(id_)

    def get_hosted_zone_by_name(self, name):
        for zone in self.get_all_hosted_zones():
            if zone.name == name:
                return zone

    def delete_hosted_zone(self, id_):
        zone = self.zones.get(id_)
        if zone:
            del self.zones[id_]
            return zone


route53_backend = Route53Backend()
