import boto3
import json
import sure  # noqa

from moto import mock_sqs, mock_cloudformation
from moto.core import ACCOUNT_ID


simple_queue = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "QueueGroup": {
            "Type": "AWS::SQS::Queue",
            "Properties": {"QueueName": "my-queue", "VisibilityTimeout": 60},
        }
    },
}
simple_queue_json = json.dumps(simple_queue)
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

    cf.create_stack(StackName="test_sqs", TemplateBody=simple_queue_json)

    queue_url = client.list_queues()["QueueUrls"][0]
    queue_url.should.contain("{}/{}".format(ACCOUNT_ID, "my-queue"))

    stack = res.Stack("test_sqs")
    for s in stack.resource_summaries.all():
        s.resource_type.should.equal("AWS::SQS::Queue")
        s.logical_id.should.equal("QueueGroup")
        s.physical_resource_id.should.equal("my-queue")


@mock_sqs
@mock_cloudformation
def test_list_stack_resources():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    client = boto3.client("sqs", region_name="us-east-1")

    cf.create_stack(StackName="test_sqs", TemplateBody=simple_queue_json)

    queue_url = client.list_queues()["QueueUrls"][0]
    queue_url.should.contain("{}/{}".format(ACCOUNT_ID, "my-queue"))

    queue = cf.list_stack_resources(StackName="test_sqs")["StackResourceSummaries"][0]

    queue.should.have.key("ResourceType").equal("AWS::SQS::Queue")
    queue.should.have.key("LogicalResourceId").should.equal("QueueGroup")
    queue.should.have.key("PhysicalResourceId").should.equal("my-queue")


@mock_sqs
@mock_cloudformation
def test_create_from_cloudformation_json_with_tags():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    client = boto3.client("sqs", region_name="us-east-1")

    cf.create_stack(StackName="test-sqs", TemplateBody=sqs_template_with_tags)

    queue_url = client.list_queues()["QueueUrls"][0]

    queue_tags = client.list_queue_tags(QueueUrl=queue_url)["Tags"]
    queue_tags.should.equal({"keyname1": "value1", "keyname2": "value2"})


@mock_cloudformation
@mock_sqs
def test_update_stack():
    sqs_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "QueueGroup": {
                "Type": "AWS::SQS::Queue",
                "Properties": {"QueueName": "my-queue", "VisibilityTimeout": 60},
            }
        },
    }
    sqs_template_json = json.dumps(sqs_template)

    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=sqs_template_json)

    client = boto3.client("sqs", region_name="us-west-1")
    queues = client.list_queues()["QueueUrls"]
    queues.should.have.length_of(1)
    attrs = client.get_queue_attributes(QueueUrl=queues[0], AttributeNames=["All"])[
        "Attributes"
    ]
    attrs["VisibilityTimeout"].should.equal("60")

    # when updating
    sqs_template["Resources"]["QueueGroup"]["Properties"]["VisibilityTimeout"] = 100
    sqs_template_json = json.dumps(sqs_template)
    cf.update_stack(StackName="test_stack", TemplateBody=sqs_template_json)

    # then the attribute should be updated
    queues = client.list_queues()["QueueUrls"]
    queues.should.have.length_of(1)
    attrs = client.get_queue_attributes(QueueUrl=queues[0], AttributeNames=["All"])[
        "Attributes"
    ]
    attrs["VisibilityTimeout"].should.equal("100")


@mock_cloudformation
@mock_sqs
def test_update_stack_and_remove_resource():
    sqs_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "QueueGroup": {
                "Type": "AWS::SQS::Queue",
                "Properties": {"QueueName": "my-queue", "VisibilityTimeout": 60},
            }
        },
    }
    sqs_template_json = json.dumps(sqs_template)

    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=sqs_template_json)

    client = boto3.client("sqs", region_name="us-west-1")
    client.list_queues()["QueueUrls"].should.have.length_of(1)

    sqs_template["Resources"].pop("QueueGroup")
    sqs_template_json = json.dumps(sqs_template)
    cf.update_stack(StackName="test_stack", TemplateBody=sqs_template_json)

    client.list_queues().shouldnt.have.key(
        "QueueUrls"
    )  # No queues exist, so the key is not passed through


@mock_cloudformation
@mock_sqs
def test_update_stack_and_add_resource():
    sqs_template = {"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}
    sqs_template_json = json.dumps(sqs_template)

    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=sqs_template_json)

    client = boto3.client("sqs", region_name="us-west-1")
    client.list_queues().shouldnt.have.key("QueueUrls")

    sqs_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "QueueGroup": {
                "Type": "AWS::SQS::Queue",
                "Properties": {"QueueName": "my-queue", "VisibilityTimeout": 60},
            }
        },
    }
    sqs_template_json = json.dumps(sqs_template)
    cf.update_stack(StackName="test_stack", TemplateBody=sqs_template_json)

    client.list_queues()["QueueUrls"].should.have.length_of(1)
