import json

import boto3

from moto import mock_aws


@mock_aws
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

    assert len(data_pipelines) == 1
    assert data_pipelines[0]["name"] == "testDataPipeline"

    stack_resources = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]
    assert len(stack_resources) == 1
    assert stack_resources[0]["PhysicalResourceId"] == data_pipelines[0]["id"]
