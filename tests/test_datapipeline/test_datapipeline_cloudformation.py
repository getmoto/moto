import boto3
import json
import sure  # noqa


from moto import mock_cloudformation, mock_datapipeline


@mock_cloudformation
@mock_datapipeline
def test_datapipeline():
    dp_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "dataPipeline": {
                "Properties": {
                    "Activate": "true",
                    "Name": "testDataPipeline",
                    "PipelineObjects": [
                        {
                            "Fields": [
                                {
                                    "Key": "failureAndRerunMode",
                                    "StringValue": "CASCADE",
                                },
                                {"Key": "scheduleType", "StringValue": "cron"},
                                {"Key": "schedule", "RefValue": "DefaultSchedule"},
                                {
                                    "Key": "pipelineLogUri",
                                    "StringValue": "s3://bucket/logs",
                                },
                                {"Key": "type", "StringValue": "Default"},
                            ],
                            "Id": "Default",
                            "Name": "Default",
                        },
                        {
                            "Fields": [
                                {
                                    "Key": "startDateTime",
                                    "StringValue": "1970-01-01T01:00:00",
                                },
                                {"Key": "period", "StringValue": "1 Day"},
                                {"Key": "type", "StringValue": "Schedule"},
                            ],
                            "Id": "DefaultSchedule",
                            "Name": "RunOnce",
                        },
                    ],
                    "PipelineTags": [],
                },
                "Type": "AWS::DataPipeline::Pipeline",
            }
        },
    }
    cf = boto3.client("cloudformation", region_name="us-east-1")
    template_json = json.dumps(dp_template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    dp = boto3.client("datapipeline", region_name="us-east-1")
    data_pipelines = dp.list_pipelines()["pipelineIdList"]

    data_pipelines.should.have.length_of(1)
    data_pipelines[0]["name"].should.equal("testDataPipeline")

    stack_resources = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]
    stack_resources.should.have.length_of(1)
    stack_resources[0]["PhysicalResourceId"].should.equal(data_pipelines[0]["id"])
