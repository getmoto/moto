import json

import boto
import sure  # noqa

from moto import mock_cloudformation

dummy_template = {
    "AWSTemplateFormatVersion": "2010-09-09",

    "Description": "Create a multi-az, load balanced, Auto Scaled sample web site. The Auto Scaling trigger is based on the CPU utilization of the web servers. The AMI is chosen based on the region in which the stack is run. This example creates a web service running across all availability zones in a region. The instances are load balanced with a simple health check. The web site is available on port 80, however, the instances can be configured to listen on any port (8888 by default). **WARNING** This template creates one or more Amazon EC2 instances. You will be billed for the AWS resources used if you create a stack from this template.",

    "Resources": {
        "WebServerGroup": {
            "Type": "AWS::AutoScaling::AutoScalingGroup",
            "Properties": {
                "AvailabilityZones": {"Fn::GetAZs": ""},
                "LaunchConfigurationName": {"Ref": "LaunchConfig"},
                "MinSize": "1",
                "MaxSize": "3",
                "LoadBalancerNames": [{"Ref": "ElasticLoadBalancer"}]
            }
        },
    },
}

dummy_template2 = {
    "AWSTemplateFormatVersion": "2010-09-09",

    "Description": "Create a multi-az, load balanced, Auto Scaled sample web site. The Auto Scaling trigger is based on the CPU utilization of the web servers. The AMI is chosen based on the region in which the stack is run. This example creates a web service running across all availability zones in a region. The instances are load balanced with a simple health check. The web site is available on port 80, however, the instances can be configured to listen on any port (8888 by default). **WARNING** This template creates one or more Amazon EC2 instances. You will be billed for the AWS resources used if you create a stack from this template.",

    "Resources": {
        "WebServerGroup": {
            "Type": "AWS::AutoScaling::AutoScalingGroup",
            "Properties": {
                "AvailabilityZones": {"Fn::GetAZs": ""},
                "LaunchConfigurationName": {"Ref": "LaunchConfig"},
                "MinSize": "2",
                "MaxSize": "2",
                "LoadBalancerNames": [{"Ref": "ElasticLoadBalancer"}]
            }
        },
    },
}

dummy_template_json = json.dumps(dummy_template)
dummy_template_json2 = json.dumps(dummy_template2)


@mock_cloudformation
def test_create_stack():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    stack = conn.describe_stacks()[0]
    stack.stack_name.should.equal('test_stack')
    stack.get_template().should.equal(dummy_template)


@mock_cloudformation
def test_describe_stack_by_name():
    conn = boto.connect_cloudformation()
    conn.create_stack("test_stack")

    stack = conn.describe_stacks("test_stack")[0]
    stack.stack_name.should.equal('test_stack')


@mock_cloudformation
def test_get_template_by_name():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    template = conn.get_template("test_stack")
    template.should.equal(dummy_template)


@mock_cloudformation
def test_list_stacks():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )
    conn.create_stack(
        "test_stack2",
        template_body=dummy_template_json,
    )

    stacks = conn.list_stacks()
    stacks.should.have.length_of(2)


@mock_cloudformation
def test_delete_stack_by_name():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    conn.list_stacks().should.have.length_of(1)
    conn.delete_stack("test_stack")
    conn.list_stacks().should.have.length_of(0)


@mock_cloudformation
def test_delete_stack_by_id():
    conn = boto.connect_cloudformation()
    stack_id = conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    conn.list_stacks().should.have.length_of(1)
    conn.delete_stack(stack_id)
    conn.list_stacks().should.have.length_of(0)


@mock_cloudformation
def test_update_stack():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    conn.update_stack("test_stack", dummy_template_json2)

    stack = conn.describe_stacks()[0]
    stack.get_template().should.equal(dummy_template2)
