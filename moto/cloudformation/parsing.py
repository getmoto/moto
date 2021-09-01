from __future__ import unicode_literals
import functools
import json
import logging
import copy
import warnings
import re

import collections.abc as collections_abc

# This ugly section of imports is necessary because we
# build the list of CloudFormationModel subclasses using
# CloudFormationModel.__subclasses__(). However, if the class
# definition of a subclass hasn't been executed yet - for example, if
# the subclass's module hasn't been imported yet - then that subclass
# doesn't exist yet, and __subclasses__ won't find it.
# So we import here to populate the list of subclasses.
from moto.apigateway import models as apigateway_models  # noqa
from moto.autoscaling import models as autoscaling_models  # noqa
from moto.awslambda import models as awslambda_models  # noqa
from moto.batch import models as batch_models  # noqa
from moto.cloudwatch import models as cloudwatch_models  # noqa
from moto.datapipeline import models as datapipeline_models  # noqa
from moto.dynamodb2 import models as dynamodb2_models  # noqa
from moto.ec2 import models as ec2_models
from moto.ecr import models as ecr_models  # noqa
from moto.ecs import models as ecs_models  # noqa
from moto.efs import models as efs_models  # noqa
from moto.elb import models as elb_models  # noqa
from moto.elbv2 import models as elbv2_models  # noqa
from moto.events import models as events_models  # noqa
from moto.iam import models as iam_models  # noqa
from moto.kinesis import models as kinesis_models  # noqa
from moto.kms import models as kms_models  # noqa
from moto.rds import models as rds_models  # noqa
from moto.rds2 import models as rds2_models  # noqa
from moto.redshift import models as redshift_models  # noqa
from moto.route53 import models as route53_models  # noqa
from moto.s3 import models as s3_models, s3_backend  # noqa
from moto.s3.utils import bucket_and_name_from_url
from moto.sagemaker import models as sagemaker_models  # noqa
from moto.sns import models as sns_models  # noqa
from moto.sqs import models as sqs_models  # noqa
from moto.stepfunctions import models as stepfunctions_models  # noqa
from moto.ssm import models as ssm_models, ssm_backends  # noqa

# End ugly list of imports

from moto.core import ACCOUNT_ID, CloudFormationModel
from .utils import random_suffix
from .exceptions import (
    ExportNotFound,
    MissingParameterError,
    UnformattedGetAttTemplateException,
    ValidationError,
)
from moto.packages.boto.cloudformation.stack import Output

# List of supported CloudFormation models
MODEL_LIST = CloudFormationModel.__subclasses__()
MODEL_MAP = {model.cloudformation_type(): model for model in MODEL_LIST}
NAME_TYPE_MAP = {
    model.cloudformation_type(): model.cloudformation_name_type()
    for model in MODEL_LIST
}

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
    for model in MODEL_LIST:
        if model.cloudformation_type() == resource_type:
            return model.cloudformation_name_type()
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
    elif resource_type == "AWS::S3::Bucket":
        right_hand_part_of_name = "-{0}-{1}".format(logical_id, random_suffix())
        max_stack_name_portion_len = 63 - len(right_hand_part_of_name)
        return "{0}{1}".format(
            stack_name[:max_stack_name_portion_len], right_hand_part_of_name
        ).lower()
    elif resource_type == "AWS::IAM::Policy":
        return "{0}-{1}-{2}".format(stack_name[:5], logical_id[:4], random_suffix())
    else:
        return "{0}-{1}-{2}".format(stack_name, logical_id, random_suffix())


def parse_resource(
    resource_json, resources_map,
):
    resource_type = resource_json["Type"]
    resource_class = resource_class_from_type(resource_type)
    if not resource_class:
        warnings.warn(
            "Tried to parse {0} but it's not supported by moto's CloudFormation implementation".format(
                resource_type
            )
        )
        return None

    if "Properties" not in resource_json:
        resource_json["Properties"] = {}

    resource_json = clean_json(resource_json, resources_map)

    return resource_class, resource_json, resource_type


def parse_resource_and_generate_name(
    logical_id, resource_json, resources_map,
):
    resource_tuple = parse_resource(resource_json, resources_map)
    if not resource_tuple:
        return None
    resource_class, resource_json, resource_type = resource_tuple

    generated_resource_name = generate_resource_name(
        resource_type, resources_map.get("AWS::StackName"), logical_id
    )

    resource_name_property = resource_name_property_from_type(resource_type)
    if resource_name_property:
        if (
            "Properties" in resource_json
            and resource_name_property in resource_json["Properties"]
        ):
            resource_name = resource_json["Properties"][resource_name_property]
        else:
            resource_name = generated_resource_name
    else:
        resource_name = generated_resource_name

    return resource_class, resource_json, resource_name


def parse_and_create_resource(logical_id, resource_json, resources_map, region_name):
    condition = resource_json.get("Condition")
    if condition and not resources_map.lazy_condition_map[condition]:
        # If this has a False condition, don't create the resource
        return None

    resource_type = resource_json["Type"]
    resource_tuple = parse_resource_and_generate_name(
        logical_id, resource_json, resources_map
    )
    if not resource_tuple:
        return None
    resource_class, resource_json, resource_physical_name = resource_tuple
    resource = resource_class.create_from_cloudformation_json(
        resource_physical_name, resource_json, region_name
    )
    resource.type = resource_type
    resource.logical_resource_id = logical_id
    return resource


def parse_and_update_resource(logical_id, resource_json, resources_map, region_name):
    resource_class, resource_json, new_resource_name = parse_resource_and_generate_name(
        logical_id, resource_json, resources_map
    )
    original_resource = resources_map[logical_id]
    if not hasattr(
        resource_class.update_from_cloudformation_json, "__isabstractmethod__"
    ):
        new_resource = resource_class.update_from_cloudformation_json(
            original_resource=original_resource,
            new_resource_name=new_resource_name,
            cloudformation_json=resource_json,
            region_name=region_name,
        )
        new_resource.type = resource_json["Type"]
        new_resource.logical_resource_id = logical_id
        return new_resource
    else:
        return None


def parse_and_delete_resource(resource_name, resource_json, region_name):
    resource_type = resource_json["Type"]
    resource_class = resource_class_from_type(resource_type)
    if not hasattr(
        resource_class.delete_from_cloudformation_json, "__isabstractmethod__"
    ):
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
                    key = s3_backend.get_object(bucket_name, name)
                    self._parsed_resources.update(json.loads(key.value))

    def parse_ssm_parameter(self, value, value_type):
        # The Value in SSM parameters is the SSM parameter path
        # we need to use ssm_backend to retrieve the
        # actual value from parameter store
        parameter = ssm_backends[self._region_name].get_parameter(value, False)
        actual_value = parameter.value
        if value_type.find("List") > 0:
            return actual_value.split(",")
        return actual_value

    def load_parameters(self):
        parameter_slots = self._template.get("Parameters", {})
        for parameter_name, parameter in parameter_slots.items():
            # Set the default values.
            value = parameter.get("Default")
            value_type = parameter.get("Type")
            if value_type.startswith("AWS::SSM::Parameter::") and value:
                value = self.parse_ssm_parameter(value, value_type)
            self.resolved_parameters[parameter_name] = value

        # Set any input parameters that were passed
        self.no_echo_parameter_keys = []
        for key, value in self.input_parameters.items():
            if key in self.resolved_parameters:
                parameter_slot = parameter_slots[key]

                value_type = parameter_slot.get("Type", "String")
                if value_type.startswith("AWS::SSM::Parameter::"):
                    value = self.parse_ssm_parameter(value, value_type)
                if value_type == "CommaDelimitedList" or value_type.startswith("List"):
                    value = value.split(",")

                def _parse_number_parameter(num_string):
                    """CloudFormation NUMBER types can be an int or float.
                    Try int first and then fall back to float if that fails
                    """
                    try:
                        return int(num_string)
                    except ValueError:
                        return float(num_string)

                if value_type == "List<Number>":
                    # The if statement directly above already converted
                    # to a list. Now we convert each element to a number
                    value = [_parse_number_parameter(v) for v in value]

                if value_type == "Number":
                    value = _parse_number_parameter(value)

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

    def build_resource_diff(self, other_template):

        old = self._resource_json_map
        new = other_template["Resources"]

        resource_names_by_action = {"Add": {}, "Modify": {}, "Remove": {}}

        resource_names_by_action = {
            "Add": set(new) - set(old),
            "Modify": set(
                name for name in new if name in old and new[name] != old[name]
            ),
            "Remove": set(old) - set(new),
        }

        return resource_names_by_action

    def build_change_set_actions(self, template, parameters):

        resource_names_by_action = self.build_resource_diff(template)

        resources_by_action = {"Add": {}, "Modify": {}, "Remove": {}}

        for resource_name in resource_names_by_action["Add"]:
            resources_by_action["Add"][resource_name] = {
                "LogicalResourceId": resource_name,
                "ResourceType": template["Resources"][resource_name]["Type"],
            }

        for resource_name in resource_names_by_action["Modify"]:
            resources_by_action["Modify"][resource_name] = {
                "LogicalResourceId": resource_name,
                "ResourceType": template["Resources"][resource_name]["Type"],
            }

        for resource_name in resource_names_by_action["Remove"]:
            resources_by_action["Remove"][resource_name] = {
                "LogicalResourceId": resource_name,
                "ResourceType": self._resource_json_map[resource_name]["Type"],
            }

        return resources_by_action

    def update(self, template, parameters=None):

        resource_names_by_action = self.build_resource_diff(template)

        for logical_name in resource_names_by_action["Remove"]:
            resource_json = self._resource_json_map[logical_name]
            resource = self._parsed_resources[logical_name]
            # ToDo: Standardize this.
            if hasattr(resource, "physical_resource_id"):
                resource_name = self._parsed_resources[
                    logical_name
                ].physical_resource_id
            else:
                resource_name = None
            parse_and_delete_resource(resource_name, resource_json, self._region_name)
            self._parsed_resources.pop(logical_name)

        self._template = template
        if parameters:
            self.input_parameters = parameters
        self.load_mapping()
        self.load_parameters()
        self.load_conditions()

        self._resource_json_map = template["Resources"]

        for logical_name in resource_names_by_action["Add"]:

            # call __getitem__ to initialize the resource
            # TODO: usage of indexer to initalize the resource is questionable
            _ = self[logical_name]

        tries = 1
        while resource_names_by_action["Modify"] and tries < 5:
            for logical_name in resource_names_by_action["Modify"].copy():
                resource_json = self._resource_json_map[logical_name]
                try:
                    changed_resource = parse_and_update_resource(
                        logical_name, resource_json, self, self._region_name
                    )
                except Exception as e:
                    # skip over dependency violations, and try again in a
                    # second pass
                    last_exception = e
                else:
                    self._parsed_resources[logical_name] = changed_resource
                    resource_names_by_action["Modify"].remove(logical_name)
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
                    if (
                        not isinstance(parsed_resource, str)
                        and parsed_resource is not None
                    ):
                        if parsed_resource and hasattr(parsed_resource, "delete"):
                            parsed_resource.delete(self._region_name)
                        else:
                            if hasattr(parsed_resource, "physical_resource_id"):
                                resource_name = parsed_resource.physical_resource_id
                            else:
                                resource_name = None

                            resource_json = self._resource_json_map[
                                parsed_resource.logical_resource_id
                            ]

                            parse_and_delete_resource(
                                resource_name, resource_json, self._region_name,
                            )

                        self._parsed_resources.pop(parsed_resource.logical_resource_id)
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

        if "Outputs" in template and template["Outputs"] is None:
            raise ValidationError(
                stack_id,  # not sure why we need to supply this when also supplying message
                message="[/Outputs] 'null' values are not allowed in templates",
            )

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
