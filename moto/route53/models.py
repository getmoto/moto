from moto.core import BaseBackend
from moto.core.utils import get_random_hex


class FakeZone:

    def __init__(self, name, id):
        self.name = name
        self.id = id
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

    def get_hosted_zone(self, id):
        return self.zones.get(id)

    def delete_hosted_zone(self, id):
        zone = self.zones.get(id)
        if zone:
            del self.zones[id]
            return zone
        return None


route53_backend = Route53Backend()
