import json

import boto3
import pytest

from moto import mock_aws


@mock_aws
def test_create_job_template():
    client = boto3.client("iot", region_name="eu-west-1")
    job_template_id = "TestJobTemplate"

    job_document = {"field": "value"}

    job_template = client.create_job_template(
        jobTemplateId=job_template_id,
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
        jobExecutionsRetryConfig={
            "criteriaList": [{"failureType": "ALL", "numberOfRetries": 10}]
        },
        abortConfig={
            "criteriaList": [
                {
                    "action": "CANCEL",
                    "failureType": "ALL",
                    "minNumberOfExecutedThings": 1,
                    "thresholdPercentage": 90,
                }
            ]
        },
    )

    assert job_template["jobTemplateId"] == job_template_id
    assert (
        job_template["jobTemplateArn"]
        == "arn:aws:iot:eu-west-1:123456789012:jobtemplate/TestJobTemplate"
    )


@mock_aws
def test_create_job_template_with_invalid_id():
    client = boto3.client("iot", region_name="eu-west-1")
    job_template_id = "TestJobTemplate!@#4"

    with pytest.raises(client.exceptions.InvalidRequestException):
        client.create_job_template(
            jobTemplateId=job_template_id,
            document=json.dumps({"field": "value"}),
            description="Description",
        )


@mock_aws
def test_create_job_template_with_the_same_id_twice():
    client = boto3.client("iot", region_name="eu-west-1")
    job_template_id = "TestJobTemplate"

    client.create_job_template(
        jobTemplateId=job_template_id,
        document=json.dumps({"field": "value"}),
        description="Description",
    )

    with pytest.raises(client.exceptions.ConflictException):
        client.create_job_template(
            jobTemplateId=job_template_id,
            document=json.dumps({"field": "value"}),
            description="Description",
        )


@mock_aws
def test_describe_job_template():
    client = boto3.client("iot", region_name="eu-west-1")
    job_template_id = "TestJobTemplate"

    job_document = {"field": "value"}

    client.create_job_template(
        jobTemplateId=job_template_id,
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
        jobExecutionsRetryConfig={
            "criteriaList": [{"failureType": "ALL", "numberOfRetries": 10}]
        },
        abortConfig={
            "criteriaList": [
                {
                    "action": "CANCEL",
                    "failureType": "ALL",
                    "minNumberOfExecutedThings": 1,
                    "thresholdPercentage": 90,
                }
            ]
        },
    )

    job_template = client.describe_job_template(jobTemplateId=job_template_id)

    assert job_template["jobTemplateId"] == job_template_id
    assert (
        job_template["jobTemplateArn"]
        == "arn:aws:iot:eu-west-1:123456789012:jobtemplate/TestJobTemplate"
    )
    assert job_template["description"] == "Description"
    assert job_template["presignedUrlConfig"] == {
        "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
        "expiresInSec": 123,
    }
    assert job_template["jobExecutionsRolloutConfig"] == {"maximumPerMinute": 10}
    assert job_template["jobExecutionsRetryConfig"]["criteriaList"] == [
        {"failureType": "ALL", "numberOfRetries": 10}
    ]


@mock_aws
def test_describe_nonexistent_job_template():
    client = boto3.client("iot", region_name="eu-west-1")
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.describe_job_template(jobTemplateId="nonexistent")


@mock_aws
def test_delete_nonexistent_job_template():
    client = boto3.client("iot", region_name="eu-west-1")
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.delete_job_template(jobTemplateId="nonexistent")


@mock_aws
def test_list_job_templates():
    client = boto3.client("iot", region_name="eu-west-1")
    job_document = {"field": "value"}
    job_template_ids = ["TestJobTemplate1", "AnotherJobTemplate"]

    for template_id in job_template_ids:
        job_template = client.create_job_template(
            jobTemplateId=template_id,
            document=json.dumps(job_document),
            description="Description",
        )

        assert job_template["jobTemplateId"] == template_id

    list_result = client.list_job_templates(maxResults=100)
    assert "nextToken" not in list_result
    assert len(list_result["jobTemplates"]) == 2


@mock_aws
def test_list_job_templates_wht_pagination():
    client = boto3.client("iot", region_name="eu-west-1")
    job_document = {"field": "value"}
    job_template_ids = [
        "TestJobTemplate1",
        "AnotherJobTemplate",
        "YetAnotherJob",
        "LasttestJob",
    ]

    for template_id in job_template_ids:
        job_template = client.create_job_template(
            jobTemplateId=template_id,
            document=json.dumps(job_document),
            description="Description",
        )

        assert job_template["jobTemplateId"] == template_id

    first_list_result = client.list_job_templates(maxResults=2)
    assert "nextToken" in first_list_result
    assert len(first_list_result["jobTemplates"]) == 2

    second_list_result = client.list_job_templates(
        maxResults=2, nextToken=first_list_result["nextToken"]
    )
    assert "nextToken" not in second_list_result
    assert len(second_list_result["jobTemplates"]) == 2


@mock_aws
def test_delete_job_template():
    # given
    client = boto3.client("iot", region_name="eu-west-1")
    job_template_id = "TestJobTemplate"
    client.create_job_template(
        jobTemplateId=job_template_id,
        document=json.dumps({"field": "value"}),
        description="Description",
    )
    list_result = client.list_job_templates(maxResults=100)
    assert len(list_result["jobTemplates"]) == 1

    # when
    client.delete_job_template(
        jobTemplateId=job_template_id,
    )

    # then
    list_result = client.list_job_templates(maxResults=100)
    assert len(list_result["jobTemplates"]) == 0
