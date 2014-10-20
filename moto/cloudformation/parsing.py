from __future__ import unicode_literals
import collections
import logging

from moto.autoscaling import models as autoscaling_models
from moto.ec2 import models as ec2_models
from moto.elb import models as elb_models
from moto.iam import models as iam_models
from moto.sqs import models as sqs_models
from .utils import random_suffix

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
    "AWS::EC2::Volume": ec2_models.Volume,
    "AWS::EC2::VolumeAttachment": ec2_models.VolumeAttachment,
    "AWS::EC2::VPC": ec2_models.VPC,
    "AWS::EC2::VPCGatewayAttachment": ec2_models.VPCGatewayAttachment,
    "AWS::ElasticLoadBalancing::LoadBalancer": elb_models.FakeLoadBalancer,
    "AWS::IAM::InstanceProfile": iam_models.InstanceProfile,
    "AWS::IAM::Role": iam_models.Role,
    "AWS::SQS::Queue": sqs_models.Queue,
}

# http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-name.html
NAME_TYPE_MAP = {
    "AWS::CloudWatch::Alarm": "Alarm",
    "AWS::DynamoDB::Table": "TableName",
    "AWS::ElastiCache::CacheCluster": "ClusterName",
    "AWS::ElasticBeanstalk::Application": "ApplicationName",
    "AWS::ElasticBeanstalk::Environment": "EnvironmentName",
    "AWS::ElasticLoadBalancing::LoadBalancer": "LoadBalancerName",
    "AWS::RDS::DBInstance": "DBInstanceIdentifier",
    "AWS::S3::Bucket": "BucketName",
    "AWS::SNS::Topic": "TopicName",
    "AWS::SQS::Queue": "QueueName"
}

# Just ignore these models types for now
NULL_MODELS = [
    "AWS::CloudFormation::WaitCondition",
    "AWS::CloudFormation::WaitConditionHandle",
]

logger = logging.getLogger("moto")


def clean_json(resource_json, resources_map):
    """
    Cleanup the a resource dict. For now, this just means replacing any Ref node
    with the corresponding physical_resource_id.

    Eventually, this is where we would add things like function parsing (fn::)
    """
    if isinstance(resource_json, dict):
        if 'Ref' in resource_json:
            # Parse resource reference
            resource = resources_map[resource_json['Ref']]
            if hasattr(resource, 'physical_resource_id'):
                return resource.physical_resource_id
            else:
                return resource

        cleaned_json = {}
        for key, value in resource_json.items():
            cleaned_json[key] = clean_json(value, resources_map)
        return cleaned_json
    elif isinstance(resource_json, list):
        return [clean_json(val, resources_map) for val in resource_json]
    else:
        return resource_json


def resource_class_from_type(resource_type):
    if resource_type in NULL_MODELS:
        return None
    if resource_type not in MODEL_MAP:
        logger.warning("No Moto CloudFormation support for %s", resource_type)
        return None
    return MODEL_MAP.get(resource_type)


def resource_name_property_from_type(resource_type):
    if resource_type not in NAME_TYPE_MAP:
        return None
    return NAME_TYPE_MAP.get(resource_type)


def parse_resource(logical_id, resource_json, resources_map):
    resource_type = resource_json['Type']
    resource_class = resource_class_from_type(resource_type)
    if not resource_class:
        return None

    resource_json = clean_json(resource_json, resources_map)
    resource_name_property = resource_name_property_from_type(resource_type)
    if resource_name_property:
        if not 'Properties' in resource_json:
            resource_json['Properties'] = dict()
        if not resource_name_property in resource_json['Properties']:
            resource_json['Properties'][resource_name_property] = '{0}-{1}-{2}'.format(
                resources_map.get('AWS::StackName'),
                logical_id,
                random_suffix())
        resource_name = resource_json['Properties'][resource_name_property]
    else:
        resource_name = '{0}-{1}-{2}'.format(resources_map.get('AWS::StackName'),
                                             logical_id,
                                             random_suffix())

    resource = resource_class.create_from_cloudformation_json(resource_name, resource_json)
    resource.type = resource_type
    resource.logical_resource_id = logical_id
    return resource


class ResourceMap(collections.Mapping):
    """
    This is a lazy loading map for resources. This allows us to create resources
    without needing to create a full dependency tree. Upon creation, each
    each resources is passed this lazy map that it can grab dependencies from.
    """

    def __init__(self, stack_id, stack_name, template):
        self._template = template
        self._resource_json_map = template['Resources']

        # Create the default resources
        self._parsed_resources = {
            "AWS::AccountId": "123456789012",
            "AWS::Region": "us-east-1",
            "AWS::StackId": stack_id,
            "AWS::StackName": stack_name,
        }

    def __getitem__(self, key):
        resource_logical_id = key

        if resource_logical_id in self._parsed_resources:
            return self._parsed_resources[resource_logical_id]
        else:
            resource_json = self._resource_json_map.get(resource_logical_id)
            new_resource = parse_resource(resource_logical_id, resource_json, self)
            self._parsed_resources[resource_logical_id] = new_resource
            return new_resource

    def __iter__(self):
        return iter(self.resources)

    def __len__(self):
        return len(self._resource_json_map)

    @property
    def resources(self):
        return self._resource_json_map.keys()

    def load_parameters(self):
        parameters = self._template.get('Parameters', {})
        for parameter_name, parameter in parameters.items():
            # Just initialize parameters to empty string for now.
            self._parsed_resources[parameter_name] = ""

    def create(self):
        self.load_parameters()

        # Since this is a lazy map, to create every object we just need to
        # iterate through self.
        tags = {'aws:cloudformation:stack-name': self.get('AWS::StackName'),
                'aws:cloudformation:stack-id': self.get('AWS::StackId')}
        for resource in self.resources:
            self[resource]
            if isinstance(self[resource], ec2_models.TaggedEC2Resource):
                tags['aws:cloudformation:logical-id'] = resource
                ec2_models.ec2_backend.create_tags([self[resource].physical_resource_id],tags)
