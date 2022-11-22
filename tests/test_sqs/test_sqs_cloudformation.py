import boto3

import json
import sure  # noqa # pylint: disable=unused-import
from moto import mock_sqs, mock_cloudformation
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from string import Template
from random import randint
from uuid import uuid4

simple_queue = Template(
    """{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "QueueGroup": {
            "Type": "AWS::SQS::Queue",
            "Properties": {"QueueName": $q_name, "VisibilityTimeout": 60},
        }
    },
}"""
)

sqs_template_with_tags = """
{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "SQSQueue": {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "Tags" : [
                    {
                        "Key" : "keyname1",
                        "Value" : "value1"
                    },
                    {
                        "Key" : "keyname2",
                        "Value" : "value2"
                    }
                ]
            }
        }
    }
}"""


@mock_sqs
@mock_cloudformation
def test_describe_stack_subresources():
    res = boto3.resource("cloudformation", region_name="us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")
    client = boto3.client("sqs", region_name="us-east-1")

    stack_name = str(uuid4())[0:6]
    q_name = str(uuid4())[0:6]
    template_body = simple_queue.substitute(q_name=q_name)
    cf.create_stack(StackName=stack_name, TemplateBody=template_body)

    queue_urls = client.list_queues(QueueNamePrefix=q_name)["QueueUrls"]
    assert any([f"{ACCOUNT_ID}/{q_name}" in url for url in queue_urls])

    stack = res.Stack(stack_name)
    for s in stack.resource_summaries.all():
        s.resource_type.should.equal("AWS::SQS::Queue")
        s.logical_id.should.equal("QueueGroup")
        s.physical_resource_id.should.contain(f"/{q_name}")


@mock_sqs
@mock_cloudformation
def test_list_stack_resources():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    client = boto3.client("sqs", region_name="us-east-1")

    stack_name = str(uuid4())[0:6]
    q_name = str(uuid4())[0:6]
    template_body = simple_queue.substitute(q_name=q_name)
    cf.create_stack(StackName=stack_name, TemplateBody=template_body)

    queue_urls = client.list_queues(QueueNamePrefix=q_name)["QueueUrls"]
    assert any([f"{ACCOUNT_ID}/{q_name}" in url for url in queue_urls])

    queue = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"][0]

    queue.should.have.key("ResourceType").equal("AWS::SQS::Queue")
    queue.should.have.key("LogicalResourceId").should.equal("QueueGroup")
    expected_url = f"https://sqs.us-east-1.amazonaws.com/{ACCOUNT_ID}/{q_name}"
    queue.should.have.key("PhysicalResourceId").should.equal(expected_url)


@mock_sqs
@mock_cloudformation
def test_create_from_cloudformation_json_with_tags():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    client = boto3.client("sqs", region_name="us-east-1")

    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=sqs_template_with_tags)

    response = cf.describe_stack_resources(StackName=stack_name)
    q_name = response["StackResources"][0]["PhysicalResourceId"].split("/")[-1]

    all_urls = client.list_queues(QueueNamePrefix=q_name)["QueueUrls"]
    queue_url = [url for url in all_urls if url.endswith(q_name)][0]

    queue_tags = client.list_queue_tags(QueueUrl=queue_url)["Tags"]
    queue_tags.should.equal({"keyname1": "value1", "keyname2": "value2"})


@mock_cloudformation
@mock_sqs
def test_update_stack():
    q_name = str(uuid4())[0:6]
    sqs_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "QueueGroup": {
                "Type": "AWS::SQS::Queue",
                "Properties": {"QueueName": q_name, "VisibilityTimeout": 60},
            }
        },
    }
    sqs_template_json = json.dumps(sqs_template)

    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=sqs_template_json)

    client = boto3.client("sqs", region_name="us-west-1")
    queues = client.list_queues(QueueNamePrefix=q_name)["QueueUrls"]
    queues.should.have.length_of(1)
    attrs = client.get_queue_attributes(QueueUrl=queues[0], AttributeNames=["All"])[
        "Attributes"
    ]
    attrs["VisibilityTimeout"].should.equal("60")

    # when updating
    sqs_template["Resources"]["QueueGroup"]["Properties"]["VisibilityTimeout"] = 100
    sqs_template_json = json.dumps(sqs_template)
    cf.update_stack(StackName=stack_name, TemplateBody=sqs_template_json)

    # then the attribute should be updated
    queues = client.list_queues(QueueNamePrefix=q_name)["QueueUrls"]
    queues.should.have.length_of(1)
    attrs = client.get_queue_attributes(QueueUrl=queues[0], AttributeNames=["All"])[
        "Attributes"
    ]
    attrs["VisibilityTimeout"].should.equal("100")


@mock_cloudformation
@mock_sqs
def test_update_stack_and_remove_resource():
    q_name = str(uuid4())[0:6]
    sqs_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "QueueGroup": {
                "Type": "AWS::SQS::Queue",
                "Properties": {"QueueName": q_name, "VisibilityTimeout": 60},
            }
        },
    }
    sqs_template_json = json.dumps(sqs_template)

    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=sqs_template_json)

    client = boto3.client("sqs", region_name="us-west-1")
    client.list_queues(QueueNamePrefix=q_name)["QueueUrls"].should.have.length_of(1)

    sqs_template["Resources"].pop("QueueGroup")
    sqs_template_json = json.dumps(sqs_template)
    cf.update_stack(StackName=stack_name, TemplateBody=sqs_template_json)

    # No queues exist, so the key is not passed through
    client.list_queues(QueueNamePrefix=q_name).shouldnt.have.key("QueueUrls")


@mock_cloudformation
@mock_sqs
def test_update_stack_and_add_resource():
    sqs_template = {"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}
    sqs_template_json = json.dumps(sqs_template)

    q_name = str(uuid4())[0:6]

    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=sqs_template_json)

    client = boto3.client("sqs", region_name="us-west-1")
    client.list_queues(QueueNamePrefix=q_name).shouldnt.have.key("QueueUrls")

    sqs_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "QueueGroup": {
                "Type": "AWS::SQS::Queue",
                "Properties": {"QueueName": q_name, "VisibilityTimeout": 60},
            }
        },
    }
    sqs_template_json = json.dumps(sqs_template)
    cf.update_stack(StackName=stack_name, TemplateBody=sqs_template_json)

    client.list_queues(QueueNamePrefix=q_name)["QueueUrls"].should.have.length_of(1)


@mock_sqs
@mock_cloudformation
def test_create_queue_passing_integer_as_name():
    """
    Passing the queue name as an Integer in the CloudFormation template
    This works in AWS - it simply converts the integer to a string, and treats it as any other name
    """
    cf = boto3.client("cloudformation", region_name="us-east-1")
    client = boto3.client("sqs", region_name="us-east-1")

    stack_name = str(uuid4())[0:6]
    q_name = f"{randint(10000000, 99999999)}"
    template_body = simple_queue.substitute(q_name=q_name)
    cf.create_stack(StackName=stack_name, TemplateBody=template_body)

    queue_urls = client.list_queues(QueueNamePrefix=q_name[0:6])["QueueUrls"]
    queue_urls.should.have.length_of(1)
