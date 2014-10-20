from __future__ import unicode_literals
import json

from mock import patch
import sure  # noqa

from moto.cloudformation.models import FakeStack
from moto.cloudformation.parsing import resource_class_from_type
from moto.sqs.models import Queue

dummy_template = {
    "AWSTemplateFormatVersion": "2010-09-09",

    "Description": "Create a multi-az, load balanced, Auto Scaled sample web site. The Auto Scaling trigger is based on the CPU utilization of the web servers. The AMI is chosen based on the region in which the stack is run. This example creates a web service running across all availability zones in a region. The instances are load balanced with a simple health check. The web site is available on port 80, however, the instances can be configured to listen on any port (8888 by default). **WARNING** This template creates one or more Amazon EC2 instances. You will be billed for the AWS resources used if you create a stack from this template.",

    "Resources": {
        "WebServerGroup": {

            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": "my-queue",
                "VisibilityTimeout": 60,
            }
        },
    },
}

name_type_template = {
    "AWSTemplateFormatVersion": "2010-09-09",

    "Description": "Create a multi-az, load balanced, Auto Scaled sample web site. The Auto Scaling trigger is based on the CPU utilization of the web servers. The AMI is chosen based on the region in which the stack is run. This example creates a web service running across all availability zones in a region. The instances are load balanced with a simple health check. The web site is available on port 80, however, the instances can be configured to listen on any port (8888 by default). **WARNING** This template creates one or more Amazon EC2 instances. You will be billed for the AWS resources used if you create a stack from this template.",

    "Resources": {
        "WebServerGroup": {

            "Type": "AWS::SQS::Queue",
            "Properties": {
                "VisibilityTimeout": 60,
            }
        },
    },
}

dummy_template_json = json.dumps(dummy_template)
name_type_template_json = json.dumps(name_type_template)


def test_parse_stack_resources():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=dummy_template_json,
    )

    stack.resource_map.should.have.length_of(1)
    list(stack.resource_map.keys())[0].should.equal('WebServerGroup')
    queue = list(stack.resource_map.values())[0]
    queue.should.be.a(Queue)
    queue.name.should.equal("my-queue")


@patch("moto.cloudformation.parsing.logger")
def test_missing_resource_logs(logger):
    resource_class_from_type("foobar")
    logger.warning.assert_called_with('No Moto CloudFormation support for %s', 'foobar')


def test_parse_stack_with_name_type_resource():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=name_type_template_json)

    stack.resource_map.should.have.length_of(1)
    list(stack.resource_map.keys())[0].should.equal('WebServerGroup')
    queue = list(stack.resource_map.values())[0]
    queue.should.be.a(Queue)
