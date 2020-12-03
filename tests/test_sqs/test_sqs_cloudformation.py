import boto3
from moto import mock_sqs, mock_cloudformation

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
def test_create_from_cloudformation_json_with_tags():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    client = boto3.client("sqs", region_name="us-east-1")

    cf.create_stack(StackName="test-sqs", TemplateBody=sqs_template_with_tags)

    queue_url = client.list_queues()["QueueUrls"][0]

    queue_tags = client.list_queue_tags(QueueUrl=queue_url)["Tags"]
    queue_tags.should.equal({"keyname1": "value1", "keyname2": "value2"})
