import collections

from moto.autoscaling import models as autoscaling_models
from moto.ec2 import models as ec2_models
from moto.elb import models as elb_models
from moto.iam import models as iam_models
from moto.sqs import models as sqs_models

MODEL_MAP = {
    "AWS::AutoScaling::AutoScalingGroup": autoscaling_models.FakeAutoScalingGroup,
    "AWS::AutoScaling::LaunchConfiguration": autoscaling_models.FakeLaunchConfiguration,
    "AWS::EC2::EIP": ec2_models.ElasticAddress,
    "AWS::EC2::Instance": ec2_models.Instance,
    "AWS::EC2::InternetGateway": ec2_models.InternetGateway,
    "AWS::EC2::Route": ec2_models.Route,
    "AWS::EC2::RouteTable": ec2_models.RouteTable,
    "AWS::EC2::SecurityGroup": ec2_models.SecurityGroup,
    "AWS::EC2::Subnet": ec2_models.Subnet,
    "AWS::EC2::SubnetRouteTableAssociation": ec2_models.SubnetRouteTableAssociation,
    "AWS::EC2::VPC": ec2_models.VPC,
    "AWS::EC2::VPCGatewayAttachment": ec2_models.VPCGatewayAttachment,
    "AWS::ElasticLoadBalancing::LoadBalancer": elb_models.FakeLoadBalancer,
    "AWS::IAM::InstanceProfile": iam_models.InstanceProfile,
    "AWS::IAM::Role": iam_models.Role,
    "AWS::SQS::Queue": sqs_models.Queue,
}

# Just ignore these models types for now
NULL_MODELS = [
    "AWS::CloudFormation::WaitCondition",
    "AWS::CloudFormation::WaitConditionHandle",
]


def resource_class_from_type(resource_type):
    if resource_type in NULL_MODELS:
        return None
    if resource_type not in MODEL_MAP:
        raise NotImplementedError("No Moto CloudFormation support for {0}".format(resource_type))
    return MODEL_MAP.get(resource_type)


def parse_resource(resource_name, resource_json, resources_map):
    resource_type = resource_json['Type']

    resource_class = resource_class_from_type(resource_type)
    if not resource_class:
        return None
    resource = resource_class.create_from_cloudformation_json(resource_name, resource_json, resources_map)
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
