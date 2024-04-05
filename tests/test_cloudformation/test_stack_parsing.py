import json
from unittest.mock import patch

import boto3
import pytest
import yaml
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.cloudformation.exceptions import ValidationError
from moto.cloudformation.models import FakeStack
from moto.cloudformation.parsing import (
    Output,
    parse_condition,
    resource_class_from_type,
)
from moto.cloudformation.utils import yaml_tag_constructor
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.s3.models import FakeBucket
from moto.sqs.models import Queue

dummy_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "sample template",
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
    "Description": "sample template",
    "Resources": {
        "Queue": {"Type": "AWS::SQS::Queue", "Properties": {"VisibilityTimeout": 60}}
    },
}

name_type_template_with_tabs_json = """
\t{
\t\t"AWSTemplateFormatVersion": "2010-09-09",
\t\t"Description": "sample template",
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
                "QueueName": {"Fn::Sub": "${AWS::StackName}-queue"},
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

sub_num_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Parameters": {
        "Num": {"Type": "Number"},
    },
    "Resources": {
        "Queue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": {"Fn::Sub": "${AWS::StackName}-queue-${Num}"},
                "VisibilityTimeout": 60,
            },
        },
    },
}

sub_mapping_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Parameters": {
        "TestRef": {"Type": "String"},
    },
    "Conditions": {
        "IsApple": {"Fn::Equals": [{"Ref": "TestRef"}, "apple"]},
    },
    "Resources": {
        "Queue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": {
                    "Fn::Sub": [
                        "${AWS::StackName}-queue-${TestRef}-${TestFn}",
                        {
                            "TestRef": {"Ref": "TestRef"},
                            "TestFn": {"Fn::If": ["IsApple", "yes", "no"]},
                        },
                    ],
                },
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
to_json_string_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "DLQ": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": "deadletter",
                "VisibilityTimeout": 60,
            },
        },
        "Queue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": "test",
                "RedrivePolicy": {
                    "Fn::ToJsonString": {
                        "deadLetterTargetArn": {"Fn::Sub": "${DLQ.Arn}"},
                        "maxReceiveCount": 1,
                    }
                },
                "VisibilityTimeout": 60,
            },
        },
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
sub_num_template_json = json.dumps(sub_num_template)
sub_mapping_json = json.dumps(sub_mapping_template)
export_value_template_json = json.dumps(export_value_template)
import_value_template_json = json.dumps(import_value_template)
to_json_string_template_json = json.dumps(to_json_string_template)


def test_parse_stack_resources():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=dummy_template_json,
        parameters={},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )

    assert len(stack.resource_map) == 2

    queue = stack.resource_map["Queue"]
    assert isinstance(queue, Queue)
    assert queue.name == "my-queue"

    bucket = stack.resource_map["S3Bucket"]
    assert isinstance(bucket, FakeBucket)
    assert bucket.physical_resource_id == bucket.name


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
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )

    assert len(stack.resource_map) == 1
    assert list(stack.resource_map.keys())[0] == "Queue"
    queue = list(stack.resource_map.values())[0]
    assert isinstance(queue, Queue)


def test_parse_stack_with_tabbed_json_template():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=name_type_template_with_tabs_json,
        parameters={},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )

    assert len(stack.resource_map) == 1
    assert list(stack.resource_map.keys())[0] == "Queue"
    queue = list(stack.resource_map.values())[0]
    assert isinstance(queue, Queue)


def test_parse_stack_with_yaml_template():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=yaml.dump(name_type_template),
        parameters={},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )

    assert len(stack.resource_map) == 1
    assert list(stack.resource_map.keys())[0] == "Queue"
    queue = list(stack.resource_map.values())[0]
    assert isinstance(queue, Queue)


def test_parse_stack_with_outputs():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=output_type_template_json,
        parameters={},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )

    assert len(stack.output_map) == 1
    assert list(stack.output_map.keys())[0] == "Output1"
    output = list(stack.output_map.values())[0]
    assert isinstance(output, Output)
    assert output.description == "This is a description."


def test_parse_stack_with_get_attribute_outputs():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=get_attribute_outputs_template_json,
        parameters={},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )

    assert len(stack.output_map) == 1
    assert list(stack.output_map.keys())[0] == "Output1"
    output = list(stack.output_map.values())[0]
    assert isinstance(output, Output)
    assert output.value == "my-queue"


def test_parse_stack_with_get_attribute_kms():
    from .fixtures.kms_key import template

    template_json = json.dumps(template)
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=template_json,
        parameters={},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )

    assert len(stack.output_map) == 1
    assert list(stack.output_map.keys())[0] == "KeyArn"
    output = list(stack.output_map.values())[0]
    assert isinstance(output, Output)


def test_parse_stack_with_get_availability_zones():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=get_availability_zones_template_json,
        parameters={},
        account_id=ACCOUNT_ID,
        region_name="us-east-1",
    )

    assert len(stack.output_map) == 1
    assert list(stack.output_map.keys())[0] == "Output1"
    output = list(stack.output_map.values())[0]
    assert isinstance(output, Output)
    assert output.value == ["us-east-1a", "us-east-1b", "us-east-1c", "us-east-1d"]


@mock_aws
def test_parse_stack_with_bad_get_attribute_outputs_using_boto3():
    conn = boto3.client("cloudformation", region_name="us-west-1")
    with pytest.raises(ClientError) as exc:
        conn.create_stack(StackName="teststack", TemplateBody=bad_output_template_json)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "Template error: resource Queue does not support attribute type InvalidAttribute in Fn::GetAtt"
    )


def test_parse_stack_with_null_outputs_section():
    with pytest.raises(ValidationError) as exc:
        FakeStack(
            "test_id",
            "test_stack",
            null_output_template_json,
            {},
            account_id=ACCOUNT_ID,
            region_name="us-west-1",
        )
    assert "[/Outputs] 'null' values are not allowed in templates" in str(exc.value)


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
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )

    assert "NoEchoParam" in stack.resource_map.no_echo_parameter_keys
    assert "Param" not in stack.resource_map.no_echo_parameter_keys
    assert "NumberParam" not in stack.resource_map.no_echo_parameter_keys
    assert "NumberListParam" not in stack.resource_map.no_echo_parameter_keys
    assert stack.resource_map.resolved_parameters["NumberParam"] == 42
    assert stack.resource_map.resolved_parameters["NumberListParam"] == [42, 3.14159]


def test_parse_equals_condition():
    assert (
        parse_condition(
            condition={"Fn::Equals": [{"Ref": "EnvType"}, "prod"]},
            resources_map={"EnvType": "prod"},
            condition_map={},
        )
        is True
    )

    assert (
        parse_condition(
            condition={"Fn::Equals": [{"Ref": "EnvType"}, "prod"]},
            resources_map={"EnvType": "staging"},
            condition_map={},
        )
        is False
    )


def test_parse_not_condition():
    assert (
        parse_condition(
            condition={"Fn::Not": [{"Fn::Equals": [{"Ref": "EnvType"}, "prod"]}]},
            resources_map={"EnvType": "prod"},
            condition_map={},
        )
        is False
    )

    assert (
        parse_condition(
            condition={"Fn::Not": [{"Fn::Equals": [{"Ref": "EnvType"}, "prod"]}]},
            resources_map={"EnvType": "staging"},
            condition_map={},
        )
        is True
    )


def test_parse_and_condition():
    assert (
        parse_condition(
            condition={
                "Fn::And": [
                    {"Fn::Equals": [{"Ref": "EnvType"}, "prod"]},
                    {"Fn::Equals": [{"Ref": "EnvType"}, "staging"]},
                ]
            },
            resources_map={"EnvType": "prod"},
            condition_map={},
        )
        is False
    )

    assert (
        parse_condition(
            condition={
                "Fn::And": [
                    {"Fn::Equals": [{"Ref": "EnvType"}, "prod"]},
                    {"Fn::Equals": [{"Ref": "EnvType"}, "prod"]},
                ]
            },
            resources_map={"EnvType": "prod"},
            condition_map={},
        )
        is True
    )


def test_parse_or_condition():
    assert (
        parse_condition(
            condition={
                "Fn::Or": [
                    {"Fn::Equals": [{"Ref": "EnvType"}, "prod"]},
                    {"Fn::Equals": [{"Ref": "EnvType"}, "staging"]},
                ]
            },
            resources_map={"EnvType": "prod"},
            condition_map={},
        )
        is True
    )

    assert (
        parse_condition(
            condition={
                "Fn::Or": [
                    {"Fn::Equals": [{"Ref": "EnvType"}, "staging"]},
                    {"Fn::Equals": [{"Ref": "EnvType"}, "staging"]},
                ]
            },
            resources_map={"EnvType": "prod"},
            condition_map={},
        )
        is False
    )


def test_reference_other_conditions():
    assert (
        parse_condition(
            condition={"Fn::Not": [{"Condition": "OtherCondition"}]},
            resources_map={},
            condition_map={"OtherCondition": True},
        )
        is False
    )


def test_parse_split_and_select():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=split_select_template_json,
        parameters={},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )

    assert len(stack.resource_map) == 1
    queue = stack.resource_map["Queue"]
    assert queue.name == "myqueue"


def test_sub():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=sub_template_json,
        parameters={},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )

    queue1 = stack.resource_map["Queue1"]
    queue2 = stack.resource_map["Queue2"]
    assert queue2.name == queue1.name


def test_sub_num():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=sub_num_template_json,
        parameters={"Num": "42"},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )

    # Errors on moto<=4.0.10 because int(42) is used with str.replace
    queue = stack.resource_map["Queue"]
    assert queue.name == "test_stack-queue-42"


def test_sub_mapping():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=sub_mapping_json,
        parameters={"TestRef": "apple"},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )
    queue = stack.resource_map["Queue"]
    assert queue.name == "test_stack-queue-apple-yes"

    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=sub_mapping_json,
        parameters={"TestRef": "banana"},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )
    queue = stack.resource_map["Queue"]
    assert queue.name == "test_stack-queue-banana-no"


def test_import():
    export_stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=export_value_template_json,
        parameters={},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )
    import_stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=import_value_template_json,
        parameters={},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
        cross_stack_resources={export_stack.exports[0].value: export_stack.exports[0]},
    )

    queue = import_stack.resource_map["Queue"]
    assert queue.name == "value"


def test_to_json_string():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=to_json_string_template_json,
        parameters={},
        account_id=ACCOUNT_ID,
        region_name="us-west-1",
    )
    queue = stack.resource_map["Queue"]
    assert queue.name == "test"
    assert queue.dead_letter_queue.name == "deadletter"


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
        assert template_dict[k] == v


@mock_aws
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
            account_id=ACCOUNT_ID,
            region_name="us-west-1",
        )

        params = stack.resource_map.resolved_parameters
        assert params["SingleParamCfn"] == "string"
        assert params["ListParamCfn"] == ["comma", "separated", "string"]

    # Not passing in a value for ListParamCfn to test Default value
    if not settings.TEST_SERVER_MODE:
        stack = FakeStack(
            stack_id="test_id",
            name="test_stack",
            template=ssm_parameter_template_json,
            parameters={"SingleParamCfn": "/path/to/single/param"},
            account_id=ACCOUNT_ID,
            region_name="us-west-1",
        )

        params = stack.resource_map.resolved_parameters
        assert params["SingleParamCfn"] == "string"
        assert params["ListParamCfn"] == ["comma", "separated", "string"]
