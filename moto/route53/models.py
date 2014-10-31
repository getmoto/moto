from __future__ import unicode_literals
from moto.core import BaseBackend
from moto.core.utils import get_random_hex


class FakeZone(object):

    def __init__(self, name, id_):
        self.name = name
        self.id = id_
        self.rrsets = {}

    def add_rrset(self, name, rrset):
        self.rrsets[name] = rrset

    def delete_rrset(self, name):
        self.rrsets.pop(name, None)


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

    def delete_hosted_zone(self, id_):
        zone = self.zones.get(id_)
        if zone:
            del self.zones[id_]
            return zone
        return None


route53_backend = Route53Backend()
