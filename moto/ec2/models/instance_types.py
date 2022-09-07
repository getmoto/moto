import pathlib

from os import listdir
from ..utils import generic_filter

from moto.utilities.utils import load_resource
from ..exceptions import FilterNotImplementedError, InvalidInstanceTypeError

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


class InstanceType(dict):
    def __init__(self, name):
        self.name = name
        self.update(INSTANCE_TYPES[name])

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def __repr__(self):
        return "<InstanceType: %s>" % self.name

    def get_filter_value(self, filter_name):
        if filter_name in ("instance-type"):
            return self.get("InstanceType")
        elif filter_name in ("vcpu-info.default-vcpus"):
            return str(self.get("VCpuInfo").get("DefaultVCpus"))
        elif filter_name in ("memory-info.size-in-mib"):
            return str(self.get("MemoryInfo").get("SizeInMiB"))
        elif filter_name in ("bare-metal"):
            return str(self.get("BareMetal")).lower()
        elif filter_name in ("burstable-performance-supported"):
            return str(self.get("BurstablePerformanceSupported")).lower()
        elif filter_name in ("current-generation"):
            return str(self.get("CurrentGeneration")).lower()
        else:
            return FilterNotImplementedError(filter_name, "DescribeInstanceTypes")


class InstanceTypeBackend:
    instance_types = list(map(InstanceType, INSTANCE_TYPES.keys()))

    def describe_instance_types(self, instance_types=None, filters=None):
        matches = self.instance_types
        if instance_types:
            matches = [t for t in matches if t.get("InstanceType") in instance_types]
            if len(instance_types) > len(matches):
                unknown_ids = set(instance_types) - set(
                    t.get("InstanceType") for t in matches
                )
                raise InvalidInstanceTypeError(unknown_ids)
        if filters:
            matches = generic_filter(filters, matches)
        return matches


class InstanceTypeOfferingBackend:
    def describe_instance_type_offerings(self, location_type=None, filters=None):
        location_type = location_type or "region"
        matches = INSTANCE_TYPE_OFFERINGS[location_type]
        matches = matches.get(self.region_name, [])
        matches = [
            o for o in matches if self.matches_filters(o, filters or {}, location_type)
        ]
        return matches

    def matches_filters(self, offering, filters, location_type):
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
