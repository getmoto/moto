from __future__ import unicode_literals
import boto3
import json
import yaml

import sure  # noqa
from unittest.mock import patch

from moto.cloudformation.exceptions import ValidationError
from moto.cloudformation.models import FakeStack
from moto.cloudformation.parsing import (
    resource_class_from_type,
    parse_condition,
    Export,
)
from moto import mock_ssm, settings
from moto.sqs.models import Queue
from moto.s3.models import FakeBucket
from moto.cloudformation.utils import yaml_tag_constructor
from moto.packages.boto.cloudformation.stack import Output


dummy_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Create a multi-az, load balanced, Auto Scaled sample web site. The Auto Scaling trigger is based on the CPU utilization of the web servers. The AMI is chosen based on the region in which the stack is run. This example creates a web service running across all availability zones in a region. The instances are load balanced with a simple health check. The web site is available on port 80, however, the instances can be configured to listen on any port (8888 by default). **WARNING** This template creates one or more Amazon EC2 instances. You will be billed for the AWS resources used if you create a stack from this template.",
    "Resources": {
        "Queue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {"QueueName": "my-queue", "VisibilityTimeout": 60},
        },
        "S3Bucket": {"Type": "AWS::S3::Bucket", "DeletionPolicy": "Retain"},
    },
}

name_type_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Create a multi-az, load balanced, Auto Scaled sample web site. The Auto Scaling trigger is based on the CPU utilization of the web servers. The AMI is chosen based on the region in which the stack is run. This example creates a web service running across all availability zones in a region. The instances are load balanced with a simple health check. The web site is available on port 80, however, the instances can be configured to listen on any port (8888 by default). **WARNING** This template creates one or more Amazon EC2 instances. You will be billed for the AWS resources used if you create a stack from this template.",
    "Resources": {
        "Queue": {"Type": "AWS::SQS::Queue", "Properties": {"VisibilityTimeout": 60}}
    },
}

name_type_template_with_tabs_json = """
\t{
\t\t"AWSTemplateFormatVersion": "2010-09-09",
\t\t"Description": "Create a multi-az, load balanced, Auto Scaled sample web site. The Auto Scaling trigger is based on the CPU utilization of the web servers. The AMI is chosen based on the region in which the stack is run. This example creates a web service running across all availability zones in a region. The instances are load balanced with a simple health check. The web site is available on port 80, however, the instances can be configured to listen on any port (8888 by default). **WARNING** This template creates one or more Amazon EC2 instances. You will be billed for the AWS resources used if you create a stack from this template.",
\t\t"Resources": {
\t\t\t"Queue": {"Type": "AWS::SQS::Queue", "Properties": {"VisibilityTimeout": 60}}
\t\t}
\t}
"""

output_dict = {
    "Outputs": {
        "Output1": {"Value": {"Ref": "Queue"}, "Description": "This is a description."}
    }
}

null_output = {"Outputs": None}

bad_output = {
    "Outputs": {"Output1": {"Value": {"Fn::GetAtt": ["Queue", "InvalidAttribute"]}}}
}

get_attribute_output = {
    "Outputs": {"Output1": {"Value": {"Fn::GetAtt": ["Queue", "QueueName"]}}}
}

get_availability_zones_output = {"Outputs": {"Output1": {"Value": {"Fn::GetAZs": ""}}}}

parameters = {
    "Parameters": {
        "Param": {"Type": "String"},
        "NumberParam": {"Type": "Number"},
        "NumberListParam": {"Type": "List<Number>"},
        "NoEchoParam": {"Type": "String", "NoEcho": True},
    }
}

ssm_parameter = {
    "Parameters": {
        "SingleParamCfn": {"Type": "AWS::SSM::Parameter::Value<String>"},
        "ListParamCfn": {
            "Type": "AWS::SSM::Parameter::Value<List<String>>",
            "Default": "/path/to/list/param",
        },
    }
}

split_select_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "Queue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": {"Fn::Select": ["1", {"Fn::Split": ["-", "123-myqueue"]}]},
                "VisibilityTimeout": 60,
            },
        }
    },
}

sub_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "Queue1": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": {"Fn::Sub": "${AWS::StackName}-queue-${!Literal}"},
                "VisibilityTimeout": 60,
            },
        },
        "Queue2": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": {"Fn::Sub": "${Queue1.QueueName}"},
                "VisibilityTimeout": 60,
            },
        },
    },
}

export_value_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "Queue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": {"Fn::Sub": "${AWS::StackName}-queue"},
                "VisibilityTimeout": 60,
            },
        }
    },
    "Outputs": {"Output1": {"Value": "value", "Export": {"Name": "queue-us-west-1"}}},
}

import_value_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "Queue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": {"Fn::ImportValue": "queue-us-west-1"},
                "VisibilityTimeout": 60,
            },
        }
    },
}

outputs_template = dict(list(dummy_template.items()) + list(output_dict.items()))
null_outputs_template = dict(list(dummy_template.items()) + list(null_output.items()))
bad_outputs_template = dict(list(dummy_template.items()) + list(bad_output.items()))
get_attribute_outputs_template = dict(
    list(dummy_template.items()) + list(get_attribute_output.items())
)
get_availability_zones_template = dict(
    list(dummy_template.items()) + list(get_availability_zones_output.items())
)

parameters_template = dict(list(dummy_template.items()) + list(parameters.items()))
ssm_parameter_template = dict(
    list(dummy_template.items()) + list(ssm_parameter.items())
)

dummy_template_json = json.dumps(dummy_template)
name_type_template_json = json.dumps(name_type_template)
output_type_template_json = json.dumps(outputs_template)
null_output_template_json = json.dumps(null_outputs_template)
bad_output_template_json = json.dumps(bad_outputs_template)
get_attribute_outputs_template_json = json.dumps(get_attribute_outputs_template)
get_availability_zones_template_json = json.dumps(get_availability_zones_template)
parameters_template_json = json.dumps(parameters_template)
ssm_parameter_template_json = json.dumps(ssm_parameter_template)
split_select_template_json = json.dumps(split_select_template)
sub_template_json = json.dumps(sub_template)
export_value_template_json = json.dumps(export_value_template)
import_value_template_json = json.dumps(import_value_template)


def test_parse_stack_resources():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=dummy_template_json,
        parameters={},
        region_name="us-west-1",
    )

    stack.resource_map.should.have.length_of(2)

    queue = stack.resource_map["Queue"]
    queue.should.be.a(Queue)
    queue.name.should.equal("my-queue")

    bucket = stack.resource_map["S3Bucket"]
    bucket.should.be.a(FakeBucket)
    bucket.physical_resource_id.should.equal(bucket.name)


@patch("moto.cloudformation.parsing.logger")
def test_missing_resource_logs(logger):
    resource_class_from_type("foobar")
    logger.warning.assert_called_with("No Moto CloudFormation support for %s", "foobar")


def test_parse_stack_with_name_type_resource():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=name_type_template_json,
        parameters={},
        region_name="us-west-1",
    )

    stack.resource_map.should.have.length_of(1)
    list(stack.resource_map.keys())[0].should.equal("Queue")
    queue = list(stack.resource_map.values())[0]
    queue.should.be.a(Queue)


def test_parse_stack_with_tabbed_json_template():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=name_type_template_with_tabs_json,
        parameters={},
        region_name="us-west-1",
    )

    stack.resource_map.should.have.length_of(1)
    list(stack.resource_map.keys())[0].should.equal("Queue")
    queue = list(stack.resource_map.values())[0]
    queue.should.be.a(Queue)


def test_parse_stack_with_yaml_template():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=yaml.dump(name_type_template),
        parameters={},
        region_name="us-west-1",
    )

    stack.resource_map.should.have.length_of(1)
    list(stack.resource_map.keys())[0].should.equal("Queue")
    queue = list(stack.resource_map.values())[0]
    queue.should.be.a(Queue)


def test_parse_stack_with_outputs():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=output_type_template_json,
        parameters={},
        region_name="us-west-1",
    )

    stack.output_map.should.have.length_of(1)
    list(stack.output_map.keys())[0].should.equal("Output1")
    output = list(stack.output_map.values())[0]
    output.should.be.a(Output)
    output.description.should.equal("This is a description.")


def test_parse_stack_with_get_attribute_outputs():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=get_attribute_outputs_template_json,
        parameters={},
        region_name="us-west-1",
    )

    stack.output_map.should.have.length_of(1)
    list(stack.output_map.keys())[0].should.equal("Output1")
    output = list(stack.output_map.values())[0]
    output.should.be.a(Output)
    output.value.should.equal("my-queue")


def test_parse_stack_with_get_attribute_kms():
    from .fixtures.kms_key import template

    template_json = json.dumps(template)
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=template_json,
        parameters={},
        region_name="us-west-1",
    )

    stack.output_map.should.have.length_of(1)
    list(stack.output_map.keys())[0].should.equal("KeyArn")
    output = list(stack.output_map.values())[0]
    output.should.be.a(Output)


def test_parse_stack_with_get_availability_zones():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=get_availability_zones_template_json,
        parameters={},
        region_name="us-east-1",
    )

    stack.output_map.should.have.length_of(1)
    list(stack.output_map.keys())[0].should.equal("Output1")
    output = list(stack.output_map.values())[0]
    output.should.be.a(Output)
    output.value.should.equal(["us-east-1a", "us-east-1b", "us-east-1c", "us-east-1d"])


def test_parse_stack_with_bad_get_attribute_outputs():
    FakeStack.when.called_with(
        "test_id", "test_stack", bad_output_template_json, {}, "us-west-1"
    ).should.throw(ValidationError)


def test_parse_stack_with_null_outputs_section():
    FakeStack.when.called_with(
        "test_id", "test_stack", null_output_template_json, {}, "us-west-1"
    ).should.throw(
        ValidationError, "[/Outputs] 'null' values are not allowed in templates"
    )


def test_parse_stack_with_parameters():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=parameters_template_json,
        parameters={
            "Param": "visible value",
            "NumberParam": "42",
            "NumberListParam": "42,3.14159",
            "NoEchoParam": "hidden value",
        },
        region_name="us-west-1",
    )

    stack.resource_map.no_echo_parameter_keys.should.have("NoEchoParam")
    stack.resource_map.no_echo_parameter_keys.should_not.have("Param")
    stack.resource_map.no_echo_parameter_keys.should_not.have("NumberParam")
    stack.resource_map.no_echo_parameter_keys.should_not.have("NumberListParam")
    stack.resource_map.resolved_parameters["NumberParam"].should.equal(42)
    stack.resource_map.resolved_parameters["NumberListParam"].should.equal(
        [42, 3.14159]
    )


def test_parse_equals_condition():
    parse_condition(
        condition={"Fn::Equals": [{"Ref": "EnvType"}, "prod"]},
        resources_map={"EnvType": "prod"},
        condition_map={},
    ).should.equal(True)

    parse_condition(
        condition={"Fn::Equals": [{"Ref": "EnvType"}, "prod"]},
        resources_map={"EnvType": "staging"},
        condition_map={},
    ).should.equal(False)


def test_parse_not_condition():
    parse_condition(
        condition={"Fn::Not": [{"Fn::Equals": [{"Ref": "EnvType"}, "prod"]}]},
        resources_map={"EnvType": "prod"},
        condition_map={},
    ).should.equal(False)

    parse_condition(
        condition={"Fn::Not": [{"Fn::Equals": [{"Ref": "EnvType"}, "prod"]}]},
        resources_map={"EnvType": "staging"},
        condition_map={},
    ).should.equal(True)


def test_parse_and_condition():
    parse_condition(
        condition={
            "Fn::And": [
                {"Fn::Equals": [{"Ref": "EnvType"}, "prod"]},
                {"Fn::Equals": [{"Ref": "EnvType"}, "staging"]},
            ]
        },
        resources_map={"EnvType": "prod"},
        condition_map={},
    ).should.equal(False)

    parse_condition(
        condition={
            "Fn::And": [
                {"Fn::Equals": [{"Ref": "EnvType"}, "prod"]},
                {"Fn::Equals": [{"Ref": "EnvType"}, "prod"]},
            ]
        },
        resources_map={"EnvType": "prod"},
        condition_map={},
    ).should.equal(True)


def test_parse_or_condition():
    parse_condition(
        condition={
            "Fn::Or": [
                {"Fn::Equals": [{"Ref": "EnvType"}, "prod"]},
                {"Fn::Equals": [{"Ref": "EnvType"}, "staging"]},
            ]
        },
        resources_map={"EnvType": "prod"},
        condition_map={},
    ).should.equal(True)

    parse_condition(
        condition={
            "Fn::Or": [
                {"Fn::Equals": [{"Ref": "EnvType"}, "staging"]},
                {"Fn::Equals": [{"Ref": "EnvType"}, "staging"]},
            ]
        },
        resources_map={"EnvType": "prod"},
        condition_map={},
    ).should.equal(False)


def test_reference_other_conditions():
    parse_condition(
        condition={"Fn::Not": [{"Condition": "OtherCondition"}]},
        resources_map={},
        condition_map={"OtherCondition": True},
    ).should.equal(False)


def test_parse_split_and_select():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=split_select_template_json,
        parameters={},
        region_name="us-west-1",
    )

    stack.resource_map.should.have.length_of(1)
    queue = stack.resource_map["Queue"]
    queue.name.should.equal("myqueue")


def test_sub():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=sub_template_json,
        parameters={},
        region_name="us-west-1",
    )

    queue1 = stack.resource_map["Queue1"]
    queue2 = stack.resource_map["Queue2"]
    queue2.name.should.equal(queue1.name)


def test_import():
    export_stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=export_value_template_json,
        parameters={},
        region_name="us-west-1",
    )
    import_stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=import_value_template_json,
        parameters={},
        region_name="us-west-1",
        cross_stack_resources={export_stack.exports[0].value: export_stack.exports[0]},
    )

    queue = import_stack.resource_map["Queue"]
    queue.name.should.equal("value")


def test_short_form_func_in_yaml_teamplate():
    template = """---
    KeyB64: !Base64 valueToEncode
    KeyRef: !Ref foo
    KeyAnd: !And
      - A
      - B
    KeyEquals: !Equals [A, B]
    KeyIf: !If [A, B, C]
    KeyNot: !Not [A]
    KeyOr: !Or [A, B]
    KeyFindInMap: !FindInMap [A, B, C]
    KeyGetAtt: !GetAtt A.B
    KeyGetAZs: !GetAZs A
    KeyImportValue: !ImportValue A
    KeyJoin: !Join [ ":", [A, B, C] ]
    KeySelect: !Select [A, B]
    KeySplit: !Split [A, B]
    KeySub: !Sub A
    """
    yaml.add_multi_constructor("", yaml_tag_constructor, Loader=yaml.Loader)
    template_dict = yaml.load(template, Loader=yaml.Loader)
    key_and_expects = [
        ["KeyRef", {"Ref": "foo"}],
        ["KeyB64", {"Fn::Base64": "valueToEncode"}],
        ["KeyAnd", {"Fn::And": ["A", "B"]}],
        ["KeyEquals", {"Fn::Equals": ["A", "B"]}],
        ["KeyIf", {"Fn::If": ["A", "B", "C"]}],
        ["KeyNot", {"Fn::Not": ["A"]}],
        ["KeyOr", {"Fn::Or": ["A", "B"]}],
        ["KeyFindInMap", {"Fn::FindInMap": ["A", "B", "C"]}],
        ["KeyGetAtt", {"Fn::GetAtt": ["A", "B"]}],
        ["KeyGetAZs", {"Fn::GetAZs": "A"}],
        ["KeyImportValue", {"Fn::ImportValue": "A"}],
        ["KeyJoin", {"Fn::Join": [":", ["A", "B", "C"]]}],
        ["KeySelect", {"Fn::Select": ["A", "B"]}],
        ["KeySplit", {"Fn::Split": ["A", "B"]}],
        ["KeySub", {"Fn::Sub": "A"}],
    ]
    for k, v in key_and_expects:
        template_dict.should.have.key(k).which.should.be.equal(v)


@mock_ssm
def test_ssm_parameter_parsing():
    client = boto3.client("ssm", region_name="us-west-1")
    client.put_parameter(Name="/path/to/single/param", Value="string", Type="String")
    client.put_parameter(
        Name="/path/to/list/param", Value="comma,separated,string", Type="StringList"
    )

    if not settings.TEST_SERVER_MODE:
        stack = FakeStack(
            stack_id="test_id",
            name="test_stack",
            template=ssm_parameter_template_json,
            parameters={
                "SingleParamCfn": "/path/to/single/param",
                "ListParamCfn": "/path/to/list/param",
            },
            region_name="us-west-1",
        )

        stack.resource_map.resolved_parameters["SingleParamCfn"].should.equal("string")
        stack.resource_map.resolved_parameters["ListParamCfn"].should.equal(
            ["comma", "separated", "string"]
        )

    # Not passing in a value for ListParamCfn to test Default value
    if not settings.TEST_SERVER_MODE:
        stack = FakeStack(
            stack_id="test_id",
            name="test_stack",
            template=ssm_parameter_template_json,
            parameters={"SingleParamCfn": "/path/to/single/param",},
            region_name="us-west-1",
        )

        stack.resource_map.resolved_parameters["SingleParamCfn"].should.equal("string")
        stack.resource_map.resolved_parameters["ListParamCfn"].should.equal(
            ["comma", "separated", "string"]
        )
