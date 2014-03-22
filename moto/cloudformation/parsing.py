import collections

from moto.ec2.models import Instance
from moto.elb.models import FakeLoadBalancer
from moto.sqs.models import Queue


MODEL_MAP = {
    "AWS::EC2::Instance": Instance,
    "AWS::ElasticLoadBalancing::LoadBalancer": FakeLoadBalancer,
    "AWS::SQS::Queue": Queue,
}


def resource_class_from_type(resource_type):
    if resource_type not in MODEL_MAP:
        raise NotImplemented("No Moto CloudFormation support for %s", resource_type)
    return MODEL_MAP.get(resource_type)


def parse_resource(resource_name, resource_json, resource_map):
    resource_type = resource_json['Type']

    resource_class = resource_class_from_type(resource_type)
    resource = resource_class.create_from_cloudformation_json(resource_json, resource_map)
    resource.type = resource_type
    resource.logical_resource_id = resource_name
    return resource


class ResourceMap(collections.Mapping):

    def __init__(self, template):
        self._template = template
        self._resource_json_map = template['Resources']

        self._parsed_resources = dict()

    def __getitem__(self, key):
        resource_name = key

        if resource_name in self._parsed_resources:
            return self._parsed_resources[resource_name]
        else:
            resource_json = self._resource_json_map.get(resource_name)
            new_resource = parse_resource(resource_name, resource_json, self)
            self._parsed_resources[resource_name] = new_resource
            return new_resource

    def __iter__(self):
        return iter(self.resource_names)

    def __len__(self):
        return len(self._resource_json_map)

    @property
    def resource_names(self):
        return self._resource_json_map.keys()

    def create(self):
        # Since this is a lazy map, to create every object we just need to
        # iterate through self.
        for resource_name in self.resource_names:
            self[resource_name]
