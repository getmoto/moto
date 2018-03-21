from __future__ import unicode_literals
import collections
import functools
import logging
import copy
import warnings
import re

from moto.autoscaling import models as autoscaling_models
from moto.awslambda import models as lambda_models
from moto.batch import models as batch_models
from moto.cloudwatch import models as cloudwatch_models
from moto.datapipeline import models as datapipeline_models
from moto.dynamodb import models as dynamodb_models
from moto.ec2 import models as ec2_models
from moto.ecs import models as ecs_models
from moto.elb import models as elb_models
from moto.elbv2 import models as elbv2_models
from moto.iam import models as iam_models
from moto.kinesis import models as kinesis_models
from moto.kms import models as kms_models
from moto.rds import models as rds_models
from moto.rds2 import models as rds2_models
from moto.redshift import models as redshift_models
from moto.route53 import models as route53_models
from moto.s3 import models as s3_models
from moto.sns import models as sns_models
from moto.sqs import models as sqs_models
from .utils import random_suffix
from .exceptions import MissingParameterError, UnformattedGetAttTemplateException, ValidationError
from boto.cloudformation.stack import Output

MODEL_MAP = {
    "AWS::AutoScaling::AutoScalingGroup": autoscaling_models.FakeAutoScalingGroup,
    "AWS::AutoScaling::LaunchConfiguration": autoscaling_models.FakeLaunchConfiguration,
    "AWS::Batch::JobDefinition": batch_models.JobDefinition,
    "AWS::Batch::JobQueue": batch_models.JobQueue,
    "AWS::Batch::ComputeEnvironment": batch_models.ComputeEnvironment,
    "AWS::DynamoDB::Table": dynamodb_models.Table,
    "AWS::Kinesis::Stream": kinesis_models.Stream,
    "AWS::Lambda::EventSourceMapping": lambda_models.EventSourceMapping,
    "AWS::Lambda::Function": lambda_models.LambdaFunction,
    "AWS::Lambda::Version": lambda_models.LambdaVersion,
    "AWS::EC2::EIP": ec2_models.ElasticAddress,
    "AWS::EC2::Instance": ec2_models.Instance,
    "AWS::EC2::InternetGateway": ec2_models.InternetGateway,
    "AWS::EC2::NatGateway": ec2_models.NatGateway,
    "AWS::EC2::NetworkInterface": ec2_models.NetworkInterface,
    "AWS::EC2::Route": ec2_models.Route,
    "AWS::EC2::RouteTable": ec2_models.RouteTable,
    "AWS::EC2::SecurityGroup": ec2_models.SecurityGroup,
    "AWS::EC2::SecurityGroupIngress": ec2_models.SecurityGroupIngress,
    "AWS::EC2::SpotFleet": ec2_models.SpotFleetRequest,
    "AWS::EC2::Subnet": ec2_models.Subnet,
    "AWS::EC2::SubnetRouteTableAssociation": ec2_models.SubnetRouteTableAssociation,
    "AWS::EC2::Volume": ec2_models.Volume,
    "AWS::EC2::VolumeAttachment": ec2_models.VolumeAttachment,
    "AWS::EC2::VPC": ec2_models.VPC,
    "AWS::EC2::VPCGatewayAttachment": ec2_models.VPCGatewayAttachment,
    "AWS::EC2::VPCPeeringConnection": ec2_models.VPCPeeringConnection,
    "AWS::ECS::Cluster": ecs_models.Cluster,
    "AWS::ECS::TaskDefinition": ecs_models.TaskDefinition,
    "AWS::ECS::Service": ecs_models.Service,
    "AWS::ElasticLoadBalancing::LoadBalancer": elb_models.FakeLoadBalancer,
    "AWS::ElasticLoadBalancingV2::LoadBalancer": elbv2_models.FakeLoadBalancer,
    "AWS::ElasticLoadBalancingV2::TargetGroup": elbv2_models.FakeTargetGroup,
    "AWS::ElasticLoadBalancingV2::Listener": elbv2_models.FakeListener,
    "AWS::DataPipeline::Pipeline": datapipeline_models.Pipeline,
    "AWS::IAM::InstanceProfile": iam_models.InstanceProfile,
    "AWS::IAM::Role": iam_models.Role,
    "AWS::KMS::Key": kms_models.Key,
    "AWS::Logs::LogGroup": cloudwatch_models.LogGroup,
    "AWS::RDS::DBInstance": rds_models.Database,
    "AWS::RDS::DBSecurityGroup": rds_models.SecurityGroup,
    "AWS::RDS::DBSubnetGroup": rds_models.SubnetGroup,
    "AWS::RDS::DBParameterGroup": rds2_models.DBParameterGroup,
    "AWS::Redshift::Cluster": redshift_models.Cluster,
    "AWS::Redshift::ClusterParameterGroup": redshift_models.ParameterGroup,
    "AWS::Redshift::ClusterSubnetGroup": redshift_models.SubnetGroup,
    "AWS::Route53::HealthCheck": route53_models.HealthCheck,
    "AWS::Route53::HostedZone": route53_models.FakeZone,
    "AWS::Route53::RecordSet": route53_models.RecordSet,
    "AWS::Route53::RecordSetGroup": route53_models.RecordSetGroup,
    "AWS::SNS::Topic": sns_models.Topic,
    "AWS::S3::Bucket": s3_models.FakeBucket,
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

DEFAULT_REGION = 'us-east-1'

logger = logging.getLogger("moto")


class LazyDict(dict):

    def __getitem__(self, key):
        val = dict.__getitem__(self, key)
        if callable(val):
            val = val()
            self[key] = val
        return val


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

        if "Fn::FindInMap" in resource_json:
            map_name = resource_json["Fn::FindInMap"][0]
            map_path = resource_json["Fn::FindInMap"][1:]
            result = resources_map[map_name]
            for path in map_path:
                result = result[clean_json(path, resources_map)]
            return result

        if 'Fn::GetAtt' in resource_json:
            resource = resources_map.get(resource_json['Fn::GetAtt'][0])
            if resource is None:
                return resource_json
            try:
                return resource.get_cfn_attribute(resource_json['Fn::GetAtt'][1])
            except NotImplementedError as n:
                logger.warning(str(n).format(
                    resource_json['Fn::GetAtt'][0]))
            except UnformattedGetAttTemplateException:
                raise ValidationError(
                    'Bad Request',
                    UnformattedGetAttTemplateException.description.format(
                        resource_json['Fn::GetAtt'][0], resource_json['Fn::GetAtt'][1]))

        if 'Fn::If' in resource_json:
            condition_name, true_value, false_value = resource_json['Fn::If']
            if resources_map.lazy_condition_map[condition_name]:
                return clean_json(true_value, resources_map)
            else:
                return clean_json(false_value, resources_map)

        if 'Fn::Join' in resource_json:
            join_list = clean_json(resource_json['Fn::Join'][1], resources_map)
            return resource_json['Fn::Join'][0].join([str(x) for x in join_list])

        if 'Fn::Split' in resource_json:
            to_split = clean_json(resource_json['Fn::Split'][1], resources_map)
            return to_split.split(resource_json['Fn::Split'][0])

        if 'Fn::Select' in resource_json:
            select_index = int(resource_json['Fn::Select'][0])
            select_list = clean_json(resource_json['Fn::Select'][1], resources_map)
            return select_list[select_index]

        if 'Fn::Sub' in resource_json:
            if isinstance(resource_json['Fn::Sub'], list):
                warnings.warn(
                    "Tried to parse Fn::Sub with variable mapping but it's not supported by moto's CloudFormation implementation")
            else:
                fn_sub_value = clean_json(resource_json['Fn::Sub'], resources_map)
                to_sub = re.findall('(?=\${)[^!^"]*?}', fn_sub_value)
                literals = re.findall('(?=\${!)[^"]*?}', fn_sub_value)
                for sub in to_sub:
                    if '.' in sub:
                        cleaned_ref = clean_json({'Fn::GetAtt': re.findall('(?<=\${)[^"]*?(?=})', sub)[0].split('.')}, resources_map)
                    else:
                        cleaned_ref = clean_json({'Ref': re.findall('(?<=\${)[^"]*?(?=})', sub)[0]}, resources_map)
                    fn_sub_value = fn_sub_value.replace(sub, cleaned_ref)
                for literal in literals:
                    fn_sub_value = fn_sub_value.replace(literal, literal.replace('!', ''))
                return fn_sub_value
            pass

        if 'Fn::ImportValue' in resource_json:
            cleaned_val = clean_json(resource_json['Fn::ImportValue'], resources_map)
            values = [x.value for x in resources_map.cross_stack_resources.values() if x.name == cleaned_val]
            if any(values):
                return values[0]

        if 'Fn::GetAZs' in resource_json:
            region = resource_json.get('Fn::GetAZs') or DEFAULT_REGION
            result = []
            # TODO: make this configurable, to reflect the real AWS AZs
            for az in ('a', 'b', 'c', 'd'):
                result.append('%s%s' % (region, az))
            return result

        cleaned_json = {}
        for key, value in resource_json.items():
            cleaned_val = clean_json(value, resources_map)
            if cleaned_val is None:
                # If we didn't find anything, don't add this attribute
                continue
            cleaned_json[key] = cleaned_val
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
    return NAME_TYPE_MAP.get(resource_type)


def parse_resource(logical_id, resource_json, resources_map):
    resource_type = resource_json['Type']
    resource_class = resource_class_from_type(resource_type)
    if not resource_class:
        warnings.warn(
            "Tried to parse {0} but it's not supported by moto's CloudFormation implementation".format(resource_type))
        return None

    resource_json = clean_json(resource_json, resources_map)
    resource_name_property = resource_name_property_from_type(resource_type)
    if resource_name_property:
        if 'Properties' not in resource_json:
            resource_json['Properties'] = dict()
        if resource_name_property not in resource_json['Properties']:
            resource_json['Properties'][resource_name_property] = '{0}-{1}-{2}'.format(
                resources_map.get('AWS::StackName'),
                logical_id,
                random_suffix())
        resource_name = resource_json['Properties'][resource_name_property]
    else:
        resource_name = '{0}-{1}-{2}'.format(resources_map.get('AWS::StackName'),
                                             logical_id,
                                             random_suffix())
    return resource_class, resource_json, resource_name


def parse_and_create_resource(logical_id, resource_json, resources_map, region_name):
    condition = resource_json.get('Condition')
    if condition and not resources_map.lazy_condition_map[condition]:
        # If this has a False condition, don't create the resource
        return None

    resource_type = resource_json['Type']
    resource_tuple = parse_resource(logical_id, resource_json, resources_map)
    if not resource_tuple:
        return None
    resource_class, resource_json, resource_name = resource_tuple
    resource = resource_class.create_from_cloudformation_json(
        resource_name, resource_json, region_name)
    resource.type = resource_type
    resource.logical_resource_id = logical_id
    return resource


def parse_and_update_resource(logical_id, resource_json, resources_map, region_name):
    resource_class, new_resource_json, new_resource_name = parse_resource(
        logical_id, resource_json, resources_map)
    original_resource = resources_map[logical_id]
    new_resource = resource_class.update_from_cloudformation_json(
        original_resource=original_resource,
        new_resource_name=new_resource_name,
        cloudformation_json=new_resource_json,
        region_name=region_name
    )
    new_resource.type = resource_json['Type']
    new_resource.logical_resource_id = logical_id
    return new_resource


def parse_and_delete_resource(logical_id, resource_json, resources_map, region_name):
    resource_class, resource_json, resource_name = parse_resource(
        logical_id, resource_json, resources_map)
    resource_class.delete_from_cloudformation_json(
        resource_name, resource_json, region_name)


def parse_condition(condition, resources_map, condition_map):
    if isinstance(condition, bool):
        return condition

    condition_operator = list(condition.keys())[0]

    condition_values = []
    for value in list(condition.values())[0]:
        # Check if we are referencing another Condition
        if 'Condition' in value:
            condition_values.append(condition_map[value['Condition']])
        else:
            condition_values.append(clean_json(value, resources_map))

    if condition_operator == "Fn::Equals":
        return condition_values[0] == condition_values[1]
    elif condition_operator == "Fn::Not":
        return not parse_condition(condition_values[0], resources_map, condition_map)
    elif condition_operator == "Fn::And":
        return all([
            parse_condition(condition_value, resources_map, condition_map)
            for condition_value
            in condition_values])
    elif condition_operator == "Fn::Or":
        return any([
            parse_condition(condition_value, resources_map, condition_map)
            for condition_value
            in condition_values])


def parse_output(output_logical_id, output_json, resources_map):
    output_json = clean_json(output_json, resources_map)
    output = Output()
    output.key = output_logical_id
    output.value = clean_json(output_json['Value'], resources_map)
    output.description = output_json.get('Description')
    return output


class ResourceMap(collections.Mapping):
    """
    This is a lazy loading map for resources. This allows us to create resources
    without needing to create a full dependency tree. Upon creation, each
    each resources is passed this lazy map that it can grab dependencies from.
    """

    def __init__(self, stack_id, stack_name, parameters, tags, region_name, template, cross_stack_resources):
        self._template = template
        self._resource_json_map = template['Resources']
        self._region_name = region_name
        self.input_parameters = parameters
        self.tags = copy.deepcopy(tags)
        self.resolved_parameters = {}
        self.cross_stack_resources = cross_stack_resources

        # Create the default resources
        self._parsed_resources = {
            "AWS::AccountId": "123456789012",
            "AWS::Region": self._region_name,
            "AWS::StackId": stack_id,
            "AWS::StackName": stack_name,
            "AWS::NoValue": None,
        }

    def __getitem__(self, key):
        resource_logical_id = key

        if resource_logical_id in self._parsed_resources:
            return self._parsed_resources[resource_logical_id]
        else:
            resource_json = self._resource_json_map.get(resource_logical_id)
            if not resource_json:
                raise KeyError(resource_logical_id)
            new_resource = parse_and_create_resource(
                resource_logical_id, resource_json, self, self._region_name)
            if new_resource is not None:
                self._parsed_resources[resource_logical_id] = new_resource
            return new_resource

    def __iter__(self):
        return iter(self.resources)

    def __len__(self):
        return len(self._resource_json_map)

    @property
    def resources(self):
        return self._resource_json_map.keys()

    def load_mapping(self):
        self._parsed_resources.update(self._template.get('Mappings', {}))

    def load_parameters(self):
        parameter_slots = self._template.get('Parameters', {})
        for parameter_name, parameter in parameter_slots.items():
            # Set the default values.
            self.resolved_parameters[parameter_name] = parameter.get('Default')

        # Set any input parameters that were passed
        for key, value in self.input_parameters.items():
            if key in self.resolved_parameters:
                value_type = parameter_slots[key].get('Type', 'String')
                if value_type == 'CommaDelimitedList' or value_type.startswith("List"):
                    value = value.split(',')
                self.resolved_parameters[key] = value

        # Check if there are any non-default params that were not passed input
        # params
        for key, value in self.resolved_parameters.items():
            if value is None:
                raise MissingParameterError(key)

        self._parsed_resources.update(self.resolved_parameters)

    def load_conditions(self):
        conditions = self._template.get('Conditions', {})
        self.lazy_condition_map = LazyDict()
        for condition_name, condition in conditions.items():
            self.lazy_condition_map[condition_name] = functools.partial(parse_condition,
                condition, self._parsed_resources, self.lazy_condition_map)

        for condition_name in self.lazy_condition_map:
            self.lazy_condition_map[condition_name]

    def create(self):
        self.load_mapping()
        self.load_parameters()
        self.load_conditions()

        # Since this is a lazy map, to create every object we just need to
        # iterate through self.
        self.tags.update({'aws:cloudformation:stack-name': self.get('AWS::StackName'),
                          'aws:cloudformation:stack-id': self.get('AWS::StackId')})
        for resource in self.resources:
            if isinstance(self[resource], ec2_models.TaggedEC2Resource):
                self.tags['aws:cloudformation:logical-id'] = resource
                ec2_models.ec2_backends[self._region_name].create_tags(
                    [self[resource].physical_resource_id], self.tags)

    def update(self, template, parameters=None):
        if parameters:
            self.input_parameters = parameters
        self.load_mapping()
        self.load_parameters()
        self.load_conditions()

        old_template = self._resource_json_map
        new_template = template['Resources']
        self._resource_json_map = new_template

        new_resource_names = set(new_template) - set(old_template)
        for resource_name in new_resource_names:
            resource_json = new_template[resource_name]
            new_resource = parse_and_create_resource(
                resource_name, resource_json, self, self._region_name)
            self._parsed_resources[resource_name] = new_resource

        removed_resource_names = set(old_template) - set(new_template)
        for resource_name in removed_resource_names:
            resource_json = old_template[resource_name]
            parse_and_delete_resource(
                resource_name, resource_json, self, self._region_name)
            self._parsed_resources.pop(resource_name)

        resources_to_update = set(name for name in new_template if name in old_template and new_template[
                                  name] != old_template[name])
        tries = 1
        while resources_to_update and tries < 5:
            for resource_name in resources_to_update.copy():
                resource_json = new_template[resource_name]
                try:
                    changed_resource = parse_and_update_resource(
                        resource_name, resource_json, self, self._region_name)
                except Exception as e:
                    # skip over dependency violations, and try again in a
                    # second pass
                    last_exception = e
                else:
                    self._parsed_resources[resource_name] = changed_resource
                    resources_to_update.remove(resource_name)
            tries += 1
        if tries == 5:
            raise last_exception

    def delete(self):
        remaining_resources = set(self.resources)
        tries = 1
        while remaining_resources and tries < 5:
            for resource in remaining_resources.copy():
                parsed_resource = self._parsed_resources.get(resource)
                try:
                    if parsed_resource and hasattr(parsed_resource, 'delete'):
                        parsed_resource.delete(self._region_name)
                except Exception as e:
                    # skip over dependency violations, and try again in a
                    # second pass
                    last_exception = e
                else:
                    remaining_resources.remove(resource)
            tries += 1
        if tries == 5:
            raise last_exception


class OutputMap(collections.Mapping):

    def __init__(self, resources, template, stack_id):
        self._template = template
        self._stack_id = stack_id
        self._output_json_map = template.get('Outputs')

        # Create the default resources
        self._resource_map = resources
        self._parsed_outputs = dict()

    def __getitem__(self, key):
        output_logical_id = key

        if output_logical_id in self._parsed_outputs:
            return self._parsed_outputs[output_logical_id]
        else:
            output_json = self._output_json_map.get(output_logical_id)
            new_output = parse_output(
                output_logical_id, output_json, self._resource_map)
            self._parsed_outputs[output_logical_id] = new_output
            return new_output

    def __iter__(self):
        return iter(self.outputs)

    def __len__(self):
        return len(self._output_json_map)

    @property
    def outputs(self):
        return self._output_json_map.keys() if self._output_json_map else []

    @property
    def exports(self):
        exports = []
        if self.outputs:
            for key, value in self._output_json_map.items():
                if value.get('Export'):
                    cleaned_name = clean_json(value['Export'].get('Name'), self._resource_map)
                    cleaned_value = clean_json(value.get('Value'), self._resource_map)
                    exports.append(Export(self._stack_id, cleaned_name, cleaned_value))
        return exports

    def create(self):
        for output in self.outputs:
            self[output]


class Export(object):

    def __init__(self, exporting_stack_id, name, value):
        self._exporting_stack_id = exporting_stack_id
        self._name = name
        self._value = value

    @property
    def exporting_stack_id(self):
        return self._exporting_stack_id

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value
