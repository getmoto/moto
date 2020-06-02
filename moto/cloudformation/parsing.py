from __future__ import unicode_literals
import functools
import json
import logging
import copy
import warnings
import re

from moto.autoscaling import models as autoscaling_models
from moto.awslambda import models as lambda_models
from moto.batch import models as batch_models
from moto.cloudwatch import models as cloudwatch_models
from moto.cognitoidentity import models as cognitoidentity_models
from moto.compat import collections_abc
from moto.datapipeline import models as datapipeline_models
from moto.dynamodb2 import models as dynamodb2_models
from moto.ec2 import models as ec2_models
from moto.ecs import models as ecs_models
from moto.elb import models as elb_models
from moto.elbv2 import models as elbv2_models
from moto.events import models as events_models
from moto.iam import models as iam_models
from moto.kinesis import models as kinesis_models
from moto.kms import models as kms_models
from moto.rds import models as rds_models
from moto.rds2 import models as rds2_models
from moto.redshift import models as redshift_models
from moto.route53 import models as route53_models
from moto.s3 import models as s3_models, s3_backend
from moto.s3.utils import bucket_and_name_from_url
from moto.sns import models as sns_models
from moto.sqs import models as sqs_models
from moto.core import ACCOUNT_ID
from .utils import random_suffix
from .exceptions import (
    ExportNotFound,
    MissingParameterError,
    UnformattedGetAttTemplateException,
    ValidationError,
)
from boto.cloudformation.stack import Output

MODEL_MAP = {
    "AWS::AutoScaling::AutoScalingGroup": autoscaling_models.FakeAutoScalingGroup,
    "AWS::AutoScaling::LaunchConfiguration": autoscaling_models.FakeLaunchConfiguration,
    "AWS::Batch::JobDefinition": batch_models.JobDefinition,
    "AWS::Batch::JobQueue": batch_models.JobQueue,
    "AWS::Batch::ComputeEnvironment": batch_models.ComputeEnvironment,
    "AWS::DynamoDB::Table": dynamodb2_models.Table,
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
    "AWS::Cognito::IdentityPool": cognitoidentity_models.CognitoIdentity,
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
    "AWS::Events::Rule": events_models.Rule,
}

UNDOCUMENTED_NAME_TYPE_MAP = {
    "AWS::AutoScaling::AutoScalingGroup": "AutoScalingGroupName",
    "AWS::AutoScaling::LaunchConfiguration": "LaunchConfigurationName",
    "AWS::IAM::InstanceProfile": "InstanceProfileName",
}

# http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-name.html
NAME_TYPE_MAP = {
    "AWS::ApiGateway::ApiKey": "Name",
    "AWS::ApiGateway::Model": "Name",
    "AWS::CloudWatch::Alarm": "AlarmName",
    "AWS::DynamoDB::Table": "TableName",
    "AWS::ElasticBeanstalk::Application": "ApplicationName",
    "AWS::ElasticBeanstalk::Environment": "EnvironmentName",
    "AWS::CodeDeploy::Application": "ApplicationName",
    "AWS::CodeDeploy::DeploymentConfig": "DeploymentConfigName",
    "AWS::CodeDeploy::DeploymentGroup": "DeploymentGroupName",
    "AWS::Config::ConfigRule": "ConfigRuleName",
    "AWS::Config::DeliveryChannel": "Name",
    "AWS::Config::ConfigurationRecorder": "Name",
    "AWS::ElasticLoadBalancing::LoadBalancer": "LoadBalancerName",
    "AWS::ElasticLoadBalancingV2::LoadBalancer": "Name",
    "AWS::ElasticLoadBalancingV2::TargetGroup": "Name",
    "AWS::EC2::SecurityGroup": "GroupName",
    "AWS::ElastiCache::CacheCluster": "ClusterName",
    "AWS::ECR::Repository": "RepositoryName",
    "AWS::ECS::Cluster": "ClusterName",
    "AWS::Elasticsearch::Domain": "DomainName",
    "AWS::Events::Rule": "Name",
    "AWS::IAM::Group": "GroupName",
    "AWS::IAM::ManagedPolicy": "ManagedPolicyName",
    "AWS::IAM::Role": "RoleName",
    "AWS::IAM::User": "UserName",
    "AWS::Lambda::Function": "FunctionName",
    "AWS::RDS::DBInstance": "DBInstanceIdentifier",
    "AWS::S3::Bucket": "BucketName",
    "AWS::SNS::Topic": "TopicName",
    "AWS::SQS::Queue": "QueueName",
}
NAME_TYPE_MAP.update(UNDOCUMENTED_NAME_TYPE_MAP)

# Just ignore these models types for now
NULL_MODELS = [
    "AWS::CloudFormation::WaitCondition",
    "AWS::CloudFormation::WaitConditionHandle",
]

DEFAULT_REGION = "us-east-1"

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
        if "Ref" in resource_json:
            # Parse resource reference
            resource = resources_map[resource_json["Ref"]]
            if hasattr(resource, "physical_resource_id"):
                return resource.physical_resource_id
            else:
                return resource

        if "Fn::FindInMap" in resource_json:
            map_name = resource_json["Fn::FindInMap"][0]
            map_path = resource_json["Fn::FindInMap"][1:]
            result = resources_map[map_name]
            for path in map_path:
                if "Fn::Transform" in result:
                    result = resources_map[clean_json(path, resources_map)]
                else:
                    result = result[clean_json(path, resources_map)]
            return result

        if "Fn::GetAtt" in resource_json:
            resource = resources_map.get(resource_json["Fn::GetAtt"][0])
            if resource is None:
                return resource_json
            try:
                return resource.get_cfn_attribute(resource_json["Fn::GetAtt"][1])
            except NotImplementedError as n:
                logger.warning(str(n).format(resource_json["Fn::GetAtt"][0]))
            except UnformattedGetAttTemplateException:
                raise ValidationError(
                    "Bad Request",
                    UnformattedGetAttTemplateException.description.format(
                        resource_json["Fn::GetAtt"][0], resource_json["Fn::GetAtt"][1]
                    ),
                )

        if "Fn::If" in resource_json:
            condition_name, true_value, false_value = resource_json["Fn::If"]
            if resources_map.lazy_condition_map[condition_name]:
                return clean_json(true_value, resources_map)
            else:
                return clean_json(false_value, resources_map)

        if "Fn::Join" in resource_json:
            join_list = clean_json(resource_json["Fn::Join"][1], resources_map)
            return resource_json["Fn::Join"][0].join([str(x) for x in join_list])

        if "Fn::Split" in resource_json:
            to_split = clean_json(resource_json["Fn::Split"][1], resources_map)
            return to_split.split(resource_json["Fn::Split"][0])

        if "Fn::Select" in resource_json:
            select_index = int(resource_json["Fn::Select"][0])
            select_list = clean_json(resource_json["Fn::Select"][1], resources_map)
            return select_list[select_index]

        if "Fn::Sub" in resource_json:
            if isinstance(resource_json["Fn::Sub"], list):
                warnings.warn(
                    "Tried to parse Fn::Sub with variable mapping but it's not supported by moto's CloudFormation implementation"
                )
            else:
                fn_sub_value = clean_json(resource_json["Fn::Sub"], resources_map)
                to_sub = re.findall(r'(?=\${)[^!^"]*?}', fn_sub_value)
                literals = re.findall(r'(?=\${!)[^"]*?}', fn_sub_value)
                for sub in to_sub:
                    if "." in sub:
                        cleaned_ref = clean_json(
                            {
                                "Fn::GetAtt": re.findall(r'(?<=\${)[^"]*?(?=})', sub)[
                                    0
                                ].split(".")
                            },
                            resources_map,
                        )
                    else:
                        cleaned_ref = clean_json(
                            {"Ref": re.findall(r'(?<=\${)[^"]*?(?=})', sub)[0]},
                            resources_map,
                        )
                    fn_sub_value = fn_sub_value.replace(sub, cleaned_ref)
                for literal in literals:
                    fn_sub_value = fn_sub_value.replace(
                        literal, literal.replace("!", "")
                    )
                return fn_sub_value
            pass

        if "Fn::ImportValue" in resource_json:
            cleaned_val = clean_json(resource_json["Fn::ImportValue"], resources_map)
            values = [
                x.value
                for x in resources_map.cross_stack_resources.values()
                if x.name == cleaned_val
            ]
            if any(values):
                return values[0]
            else:
                raise ExportNotFound(cleaned_val)

        if "Fn::GetAZs" in resource_json:
            region = resource_json.get("Fn::GetAZs") or DEFAULT_REGION
            result = []
            # TODO: make this configurable, to reflect the real AWS AZs
            for az in ("a", "b", "c", "d"):
                result.append("%s%s" % (region, az))
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


def generate_resource_name(resource_type, stack_name, logical_id):
    if resource_type in [
        "AWS::ElasticLoadBalancingV2::TargetGroup",
        "AWS::ElasticLoadBalancingV2::LoadBalancer",
    ]:
        # Target group names need to be less than 32 characters, so when cloudformation creates a name for you
        # it makes sure to stay under that limit
        name_prefix = "{0}-{1}".format(stack_name, logical_id)
        my_random_suffix = random_suffix()
        truncated_name_prefix = name_prefix[0 : 32 - (len(my_random_suffix) + 1)]
        # if the truncated name ends in a dash, we'll end up with a double dash in the final name, which is
        # not allowed
        if truncated_name_prefix.endswith("-"):
            truncated_name_prefix = truncated_name_prefix[:-1]
        return "{0}-{1}".format(truncated_name_prefix, my_random_suffix)
    else:
        return "{0}-{1}-{2}".format(stack_name, logical_id, random_suffix())


def parse_resource(logical_id, resource_json, resources_map):
    resource_type = resource_json["Type"]
    resource_class = resource_class_from_type(resource_type)
    if not resource_class:
        warnings.warn(
            "Tried to parse {0} but it's not supported by moto's CloudFormation implementation".format(
                resource_type
            )
        )
        return None

    resource_json = clean_json(resource_json, resources_map)
    resource_name_property = resource_name_property_from_type(resource_type)
    if resource_name_property:
        if "Properties" not in resource_json:
            resource_json["Properties"] = dict()
        if resource_name_property not in resource_json["Properties"]:
            resource_json["Properties"][
                resource_name_property
            ] = generate_resource_name(
                resource_type, resources_map.get("AWS::StackName"), logical_id
            )
        resource_name = resource_json["Properties"][resource_name_property]
    else:
        resource_name = generate_resource_name(
            resource_type, resources_map.get("AWS::StackName"), logical_id
        )

    return resource_class, resource_json, resource_name


def parse_and_create_resource(logical_id, resource_json, resources_map, region_name):
    condition = resource_json.get("Condition")
    if condition and not resources_map.lazy_condition_map[condition]:
        # If this has a False condition, don't create the resource
        return None

    resource_type = resource_json["Type"]
    resource_tuple = parse_resource(logical_id, resource_json, resources_map)
    if not resource_tuple:
        return None
    resource_class, resource_json, resource_name = resource_tuple
    resource = resource_class.create_from_cloudformation_json(
        resource_name, resource_json, region_name
    )
    resource.type = resource_type
    resource.logical_resource_id = logical_id
    return resource


def parse_and_update_resource(logical_id, resource_json, resources_map, region_name):
    resource_class, new_resource_json, new_resource_name = parse_resource(
        logical_id, resource_json, resources_map
    )
    original_resource = resources_map[logical_id]
    new_resource = resource_class.update_from_cloudformation_json(
        original_resource=original_resource,
        new_resource_name=new_resource_name,
        cloudformation_json=new_resource_json,
        region_name=region_name,
    )
    new_resource.type = resource_json["Type"]
    new_resource.logical_resource_id = logical_id
    return new_resource


def parse_and_delete_resource(logical_id, resource_json, resources_map, region_name):
    resource_class, resource_json, resource_name = parse_resource(
        logical_id, resource_json, resources_map
    )
    resource_class.delete_from_cloudformation_json(
        resource_name, resource_json, region_name
    )


def parse_condition(condition, resources_map, condition_map):
    if isinstance(condition, bool):
        return condition

    condition_operator = list(condition.keys())[0]

    condition_values = []
    for value in list(condition.values())[0]:
        # Check if we are referencing another Condition
        if "Condition" in value:
            condition_values.append(condition_map[value["Condition"]])
        else:
            condition_values.append(clean_json(value, resources_map))

    if condition_operator == "Fn::Equals":
        return condition_values[0] == condition_values[1]
    elif condition_operator == "Fn::Not":
        return not parse_condition(condition_values[0], resources_map, condition_map)
    elif condition_operator == "Fn::And":
        return all(
            [
                parse_condition(condition_value, resources_map, condition_map)
                for condition_value in condition_values
            ]
        )
    elif condition_operator == "Fn::Or":
        return any(
            [
                parse_condition(condition_value, resources_map, condition_map)
                for condition_value in condition_values
            ]
        )


def parse_output(output_logical_id, output_json, resources_map):
    output_json = clean_json(output_json, resources_map)
    output = Output()
    output.key = output_logical_id
    output.value = clean_json(output_json["Value"], resources_map)
    output.description = output_json.get("Description")
    return output


class ResourceMap(collections_abc.Mapping):
    """
    This is a lazy loading map for resources. This allows us to create resources
    without needing to create a full dependency tree. Upon creation, each
    each resources is passed this lazy map that it can grab dependencies from.
    """

    def __init__(
        self,
        stack_id,
        stack_name,
        parameters,
        tags,
        region_name,
        template,
        cross_stack_resources,
    ):
        self._template = template
        self._resource_json_map = template["Resources"] if template != {} else {}
        self._region_name = region_name
        self.input_parameters = parameters
        self.tags = copy.deepcopy(tags)
        self.resolved_parameters = {}
        self.cross_stack_resources = cross_stack_resources

        # Create the default resources
        self._parsed_resources = {
            "AWS::AccountId": ACCOUNT_ID,
            "AWS::Region": self._region_name,
            "AWS::StackId": stack_id,
            "AWS::StackName": stack_name,
            "AWS::URLSuffix": "amazonaws.com",
            "AWS::NoValue": None,
            "AWS::Partition": "aws",
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
                resource_logical_id, resource_json, self, self._region_name
            )
            if new_resource is not None:
                self._parsed_resources[resource_logical_id] = new_resource
            return new_resource

    def __iter__(self):
        return iter(self.resources)

    def __len__(self):
        return len(self._resource_json_map)

    def __get_resources_in_dependency_order(self):
        resource_map = copy.deepcopy(self._resource_json_map)
        resources_in_dependency_order = []

        def recursively_get_dependencies(resource):
            resource_info = resource_map[resource]

            if "DependsOn" not in resource_info:
                resources_in_dependency_order.append(resource)
                del resource_map[resource]
                return

            dependencies = resource_info["DependsOn"]
            if isinstance(dependencies, str):  # Dependencies may be a string or list
                dependencies = [dependencies]

            for dependency in dependencies:
                if dependency in resource_map:
                    recursively_get_dependencies(dependency)

            resources_in_dependency_order.append(resource)
            del resource_map[resource]

        while resource_map:
            recursively_get_dependencies(list(resource_map.keys())[0])

        return resources_in_dependency_order

    @property
    def resources(self):
        return self._resource_json_map.keys()

    def load_mapping(self):
        self._parsed_resources.update(self._template.get("Mappings", {}))

    def transform_mapping(self):
        for k, v in self._template.get("Mappings", {}).items():
            if "Fn::Transform" in v:
                name = v["Fn::Transform"]["Name"]
                params = v["Fn::Transform"]["Parameters"]
                if name == "AWS::Include":
                    location = params["Location"]
                    bucket_name, name = bucket_and_name_from_url(location)
                    key = s3_backend.get_key(bucket_name, name)
                    self._parsed_resources.update(json.loads(key.value))

    def load_parameters(self):
        parameter_slots = self._template.get("Parameters", {})
        for parameter_name, parameter in parameter_slots.items():
            # Set the default values.
            self.resolved_parameters[parameter_name] = parameter.get("Default")

        # Set any input parameters that were passed
        self.no_echo_parameter_keys = []
        for key, value in self.input_parameters.items():
            if key in self.resolved_parameters:
                parameter_slot = parameter_slots[key]

                value_type = parameter_slot.get("Type", "String")
                if value_type == "CommaDelimitedList" or value_type.startswith("List"):
                    value = value.split(",")

                if parameter_slot.get("NoEcho"):
                    self.no_echo_parameter_keys.append(key)

                self.resolved_parameters[key] = value

        # Check if there are any non-default params that were not passed input
        # params
        for key, value in self.resolved_parameters.items():
            if value is None:
                raise MissingParameterError(key)

        self._parsed_resources.update(self.resolved_parameters)

    def load_conditions(self):
        conditions = self._template.get("Conditions", {})
        self.lazy_condition_map = LazyDict()
        for condition_name, condition in conditions.items():
            self.lazy_condition_map[condition_name] = functools.partial(
                parse_condition,
                condition,
                self._parsed_resources,
                self.lazy_condition_map,
            )

        for condition_name in self.lazy_condition_map:
            self.lazy_condition_map[condition_name]

    def load(self):
        self.load_mapping()
        self.transform_mapping()
        self.load_parameters()
        self.load_conditions()

    def create(self, template):
        # Since this is a lazy map, to create every object we just need to
        # iterate through self.
        # Assumes that self.load() has been called before
        self._template = template
        self._resource_json_map = template["Resources"]
        self.tags.update(
            {
                "aws:cloudformation:stack-name": self.get("AWS::StackName"),
                "aws:cloudformation:stack-id": self.get("AWS::StackId"),
            }
        )
        for resource in self.__get_resources_in_dependency_order():
            if isinstance(self[resource], ec2_models.TaggedEC2Resource):
                self.tags["aws:cloudformation:logical-id"] = resource
                ec2_models.ec2_backends[self._region_name].create_tags(
                    [self[resource].physical_resource_id], self.tags
                )

    def diff(self, template, parameters=None):
        if parameters:
            self.input_parameters = parameters
        self.load_mapping()
        self.load_parameters()
        self.load_conditions()

        old_template = self._resource_json_map
        new_template = template["Resources"]

        resource_names_by_action = {
            "Add": set(new_template) - set(old_template),
            "Modify": set(
                name
                for name in new_template
                if name in old_template and new_template[name] != old_template[name]
            ),
            "Remove": set(old_template) - set(new_template),
        }
        resources_by_action = {"Add": {}, "Modify": {}, "Remove": {}}

        for resource_name in resource_names_by_action["Add"]:
            resources_by_action["Add"][resource_name] = {
                "LogicalResourceId": resource_name,
                "ResourceType": new_template[resource_name]["Type"],
            }

        for resource_name in resource_names_by_action["Modify"]:
            resources_by_action["Modify"][resource_name] = {
                "LogicalResourceId": resource_name,
                "ResourceType": new_template[resource_name]["Type"],
            }

        for resource_name in resource_names_by_action["Remove"]:
            resources_by_action["Remove"][resource_name] = {
                "LogicalResourceId": resource_name,
                "ResourceType": old_template[resource_name]["Type"],
            }

        return resources_by_action

    def update(self, template, parameters=None):
        resources_by_action = self.diff(template, parameters)

        old_template = self._resource_json_map
        new_template = template["Resources"]
        self._resource_json_map = new_template

        for resource_name, resource in resources_by_action["Add"].items():
            resource_json = new_template[resource_name]
            new_resource = parse_and_create_resource(
                resource_name, resource_json, self, self._region_name
            )
            self._parsed_resources[resource_name] = new_resource

        for resource_name, resource in resources_by_action["Remove"].items():
            resource_json = old_template[resource_name]
            parse_and_delete_resource(
                resource_name, resource_json, self, self._region_name
            )
            self._parsed_resources.pop(resource_name)

        tries = 1
        while resources_by_action["Modify"] and tries < 5:
            for resource_name, resource in resources_by_action["Modify"].copy().items():
                resource_json = new_template[resource_name]
                try:
                    changed_resource = parse_and_update_resource(
                        resource_name, resource_json, self, self._region_name
                    )
                except Exception as e:
                    # skip over dependency violations, and try again in a
                    # second pass
                    last_exception = e
                else:
                    self._parsed_resources[resource_name] = changed_resource
                    del resources_by_action["Modify"][resource_name]
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
                    if parsed_resource and hasattr(parsed_resource, "delete"):
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


class OutputMap(collections_abc.Mapping):
    def __init__(self, resources, template, stack_id):
        self._template = template
        self._stack_id = stack_id
        self._output_json_map = template.get("Outputs")

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
                output_logical_id, output_json, self._resource_map
            )
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
                if value.get("Export"):
                    cleaned_name = clean_json(
                        value["Export"].get("Name"), self._resource_map
                    )
                    cleaned_value = clean_json(value.get("Value"), self._resource_map)
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
