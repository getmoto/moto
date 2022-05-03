import pathlib

from os import listdir

from moto.utilities.utils import load_resource
from ..exceptions import InvalidInstanceTypeError

INSTANCE_TYPES = load_resource(__name__, "../resources/instance_types.json")
INSTANCE_FAMILIES = list(set([i.split(".")[0] for i in INSTANCE_TYPES.keys()]))

root = pathlib.Path(__file__).parent
offerings_path = "../resources/instance_type_offerings"
INSTANCE_TYPE_OFFERINGS = {}
for location_type in listdir(root / offerings_path):
    INSTANCE_TYPE_OFFERINGS[location_type] = {}
    for _region in listdir(root / offerings_path / location_type):
        full_path = offerings_path + "/" + location_type + "/" + _region
        res = load_resource(__name__, full_path)
        for instance in res:
            instance["LocationType"] = location_type
        INSTANCE_TYPE_OFFERINGS[location_type][_region.replace(".json", "")] = res


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
