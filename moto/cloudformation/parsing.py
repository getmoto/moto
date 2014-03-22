from moto.ec2.models import Instance
from moto.elb.models import FakeLoadBalancer
from moto.sqs.models import Queue


MODEL_MAP = {
    "AWS::EC2::Instance": Instance,
    "AWS::ElasticLoadBalancing::LoadBalancer": FakeLoadBalancer,
    "AWS::SQS::Queue": Queue,
}


def resource_class_from_type(resource_type):
    return MODEL_MAP.get(resource_type)


def parse_resource(resource_name, resource_json):
    resource_type = resource_json['Type']
    resource_properties = resource_json['Properties']

    resource_class = resource_class_from_type(resource_type)
    resource = resource_class.create_from_cloudformation_json(resource_properties)
    resource.type = resource_type
    resource.logical_resource_id = resource_name
    return resource


def parse_resources(template):
    resource_map = {}

    resource_json_map = template['Resources']

    for resource_name, resource_json in resource_json_map.items():
        resource_map[resource_name] = parse_resource(resource_name, resource_json)

    return resource_map
