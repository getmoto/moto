"""Unit tests for glue-supported APIs."""

import json
from random import randint
from uuid import uuid4

import boto3
import pytest
from botocore.client import ClientError

from moto import mock_aws


@mock_aws
def test_create_job():
    client = create_glue_client()
    job_name = str(uuid4())
    response = client.create_job(
        Name=job_name, Role="test_role", Command=dict(Name="test_command")
    )
    assert response["Name"] == job_name


@mock_aws
def test_delete_job():
    client = create_glue_client()
    job_name = create_test_job(client)

    client.get_job(JobName=job_name)

    client.delete_job(JobName=job_name)

    with pytest.raises(ClientError) as exc:
        client.get_job(JobName=job_name)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"


@mock_aws
def test_list_jobs():
    client = create_glue_client()
    expected_jobs = randint(1, 15)
    create_test_jobs(client, expected_jobs)
    response = client.list_jobs()
    assert len(response["JobNames"]) == expected_jobs
    assert "NextToken" not in response


@mock_aws
def test_get_job_not_exists():
    client = create_glue_client()
    name = "my_job_name"

    with pytest.raises(ClientError) as exc:
        client.get_job(JobName=name)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Job my_job_name not found."


@mock_aws
def test_get_job_exists():
    client = create_glue_client()
    job_attributes = {
        "Description": "test_description",
        "LogUri": "test_log/",
        "Role": "test_role",
        "ExecutionProperty": {"MaxConcurrentRuns": 123},
        "Command": {
            "Name": "test_command",
            "ScriptLocation": "test_s3_path",
            "PythonVersion": "3.6",
        },
        "DefaultArguments": {"string": "string"},
        "NonOverridableArguments": {"string": "string"},
        "Connections": {
            "Connections": [
                "string",
            ]
        },
        "MaxRetries": 123,
        "AllocatedCapacity": 123,
        "Timeout": 123,
        "MaxCapacity": 123.0,
        "WorkerType": "G.2X",
        "NumberOfWorkers": 123,
        "SecurityConfiguration": "test_config",
        "NotificationProperty": {"NotifyDelayAfter": 123},
        "GlueVersion": "string",
        "CodeGenConfigurationNodes": {},
        "ExecutionClass": "string",
        "SourceControlDetails": {},
    }
    job_name = create_test_job_w_all_attributes(client, **job_attributes)
    job = client.get_job(JobName=job_name)["Job"]
    assert job["Name"] == job_name
    assert "Description" in job
    assert "LogUri" in job
    assert "Role" in job
    assert job["ExecutionProperty"] == {"MaxConcurrentRuns": 123}
    assert "CreatedOn" in job
    assert "LastModifiedOn" in job
    assert "ExecutionProperty" in job
    assert "Command" in job
    assert "DefaultArguments" in job
    assert "NonOverridableArguments" in job
    assert "Connections" in job
    assert "MaxRetries" in job
    assert "AllocatedCapacity" in job
    assert "Timeout" in job
    assert "MaxCapacity" in job
    assert "WorkerType" in job
    assert "NumberOfWorkers" in job
    assert "SecurityConfiguration" in job
    assert "NotificationProperty" in job
    assert "GlueVersion" in job
    assert "CodeGenConfigurationNodes" in job
    assert "ExecutionClass" in job
    assert "SourceControlDetails" in job


@mock_aws
def test_get_jobs_job_name_exists():
    client = create_glue_client()
    test_job_name = create_test_job(client)
    response = client.get_jobs()
    assert len(response["Jobs"]) == 1
    assert response["Jobs"][0]["Name"] == test_job_name


@mock_aws
def test_get_jobs_with_max_results():
    client = create_glue_client()
    create_test_jobs(client, 4)
    response = client.get_jobs(MaxResults=2)
    assert len(response["Jobs"]) == 2
    assert "NextToken" in response


@mock_aws
def test_get_jobs_from_next_token():
    client = create_glue_client()
    create_test_jobs(client, 10)
    first_response = client.get_jobs(MaxResults=3)
    response = client.get_jobs(NextToken=first_response["NextToken"])
    assert len(response["Jobs"]) == 7


@mock_aws
def test_get_jobs_with_max_results_greater_than_actual_results():
    client = create_glue_client()
    create_test_jobs(client, 4)
    response = client.get_jobs(MaxResults=10)
    assert len(response["Jobs"]) == 4


@mock_aws
def test_get_jobs_next_token_logic_does_not_create_infinite_loop():
    client = create_glue_client()
    create_test_jobs(client, 4)
    first_response = client.get_jobs(MaxResults=1)
    next_token = first_response["NextToken"]
    while next_token:
        response = client.get_jobs(NextToken=next_token)
        next_token = response.get("NextToken")
    assert not next_token


@mock_aws
def test_list_jobs_with_max_results():
    client = create_glue_client()
    create_test_jobs(client, 4)
    response = client.list_jobs(MaxResults=2)
    assert len(response["JobNames"]) == 2
    assert "NextToken" in response


@mock_aws
def test_list_jobs_from_next_token():
    client = create_glue_client()
    create_test_jobs(client, 10)
    first_response = client.list_jobs(MaxResults=3)
    response = client.list_jobs(NextToken=first_response["NextToken"])
    assert len(response["JobNames"]) == 7


@mock_aws
def test_list_jobs_with_max_results_greater_than_actual_results():
    client = create_glue_client()
    create_test_jobs(client, 4)
    response = client.list_jobs(MaxResults=10)
    assert len(response["JobNames"]) == 4


@mock_aws
def test_list_jobs_with_tags():
    client = create_glue_client()
    create_test_job(client)
    create_test_job(client, {"string": "string"})
    response = client.list_jobs(Tags={"string": "string"})
    assert len(response["JobNames"]) == 1


@mock_aws
def test_list_jobs_after_tagging():
    client = create_glue_client()
    job_name = create_test_job(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:job/{job_name}"

    client.tag_resource(ResourceArn=resource_arn, TagsToAdd={"key1": "value1"})

    response = client.list_jobs(Tags={"key1": "value1"})
    assert len(response["JobNames"]) == 1


@mock_aws
def test_list_jobs_after_removing_tag():
    client = create_glue_client()
    job_name = create_test_job(client, {"key1": "value1"})
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:job/{job_name}"

    client.untag_resource(ResourceArn=resource_arn, TagsToRemove=["key1"])

    response = client.list_jobs(Tags={"key1": "value1"})
    assert len(response["JobNames"]) == 0


@mock_aws
def test_list_jobs_next_token_logic_does_not_create_infinite_loop():
    client = create_glue_client()
    create_test_jobs(client, 4)
    first_response = client.list_jobs(MaxResults=1)
    next_token = first_response["NextToken"]
    while next_token:
        response = client.list_jobs(NextToken=next_token)
        next_token = response.get("NextToken")
    assert not next_token


@mock_aws
def test_batch_get_jobs():
    client = create_glue_client()
    job_name = create_test_job(client)

    response = client.batch_get_jobs(JobNames=[job_name, "job-not-found"])

    assert len(response["Jobs"]) == 1
    assert len(response["JobsNotFound"]) == 1


def create_glue_client():
    return boto3.client("glue", region_name="us-east-1")


def create_test_job(client, tags=None):
    job_name = str(uuid4())
    client.create_job(
        Name=job_name,
        Role="test_role",
        Command=dict(Name="test_command"),
        Tags=tags or {},
    )
    return job_name


def create_test_job_w_all_attributes(client, **job_attributes):
    job_name = str(uuid4())
    client.create_job(Name=job_name, **job_attributes)
    return job_name


def create_test_jobs(client, number_of_jobs):
    for _ in range(number_of_jobs):
        create_test_job(client)


def create_test_crawler(client, tags=None):
    crawler_name = str(uuid4())
    client.create_crawler(
        Name=crawler_name,
        Role="test_role",
        Targets={"S3Targets": [{"Path": "s3://tests3target"}]},
        Tags=tags or {},
    )
    return crawler_name


def create_test_crawlers(client, number_of_crawlers):
    for _ in range(number_of_crawlers):
        create_test_crawler(client)


@mock_aws
def test_list_crawlers_with_max_results():
    client = create_glue_client()
    create_test_crawlers(client, 4)
    response = client.list_crawlers(MaxResults=2)
    assert len(response["CrawlerNames"]) == 2
    assert "NextToken" in response


@mock_aws
def test_list_crawlers_from_next_token():
    client = create_glue_client()
    create_test_crawlers(client, 10)
    first_response = client.list_crawlers(MaxResults=3)
    response = client.list_crawlers(NextToken=first_response["NextToken"])
    assert len(response["CrawlerNames"]) == 7


@mock_aws
def test_list_crawlers_with_max_results_greater_than_actual_results():
    client = create_glue_client()
    create_test_crawlers(client, 4)
    response = client.list_crawlers(MaxResults=10)
    assert len(response["CrawlerNames"]) == 4


@mock_aws
def test_list_crawlers_with_tags():
    client = create_glue_client()
    create_test_crawler(client)
    create_test_crawler(client, {"string": "string"})
    response = client.list_crawlers(Tags={"string": "string"})
    assert len(response["CrawlerNames"]) == 1


@mock_aws
def test_list_crawlers_after_tagging():
    client = create_glue_client()
    crawler_name = create_test_crawler(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:crawler/{crawler_name}"

    client.tag_resource(ResourceArn=resource_arn, TagsToAdd={"key1": "value1"})

    response = client.list_crawlers(Tags={"key1": "value1"})
    assert len(response["CrawlerNames"]) == 1


@mock_aws
def test_list_crawlers_after_removing_tag():
    client = create_glue_client()
    crawler_name = create_test_crawler(client, {"key1": "value1"})
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:crawler/{crawler_name}"

    client.untag_resource(ResourceArn=resource_arn, TagsToRemove=["key1"])

    response = client.list_crawlers(Tags={"key1": "value1"})
    assert len(response["CrawlerNames"]) == 0


@mock_aws
def test_list_crawlers_next_token_logic_does_not_create_infinite_loop():
    client = create_glue_client()
    create_test_crawlers(client, 4)
    first_response = client.list_crawlers(MaxResults=1)
    next_token = first_response["NextToken"]
    while next_token:
        response = client.list_crawlers(NextToken=next_token)
        next_token = response.get("NextToken")
    assert not next_token


@mock_aws
def test_get_tags_job():
    client = create_glue_client()
    job_name = create_test_job(client, {"key1": "value1", "key2": "value2"})
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:job/{job_name}"

    resp = client.get_tags(ResourceArn=resource_arn)

    assert resp["Tags"] == {"key1": "value1", "key2": "value2"}


@mock_aws
def test_get_tags_jobs_no_tags():
    client = create_glue_client()
    job_name = create_test_job(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:job/{job_name}"

    resp = client.get_tags(ResourceArn=resource_arn)

    assert resp["Tags"] == {}


@mock_aws
def test_tag_glue_job():
    client = create_glue_client()
    job_name = create_test_job(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:job/{job_name}"

    client.tag_resource(
        ResourceArn=resource_arn, TagsToAdd={"key1": "value1", "key2": "value2"}
    )

    resp = client.get_tags(ResourceArn=resource_arn)

    assert resp["Tags"] == {"key1": "value1", "key2": "value2"}


@mock_aws
def test_untag_glue_job():
    client = create_glue_client()
    job_name = create_test_job(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:job/{job_name}"

    client.tag_resource(
        ResourceArn=resource_arn,
        TagsToAdd={"key1": "value1", "key2": "value2", "key3": "value3"},
    )

    client.untag_resource(ResourceArn=resource_arn, TagsToRemove=["key2"])

    resp = client.get_tags(ResourceArn=resource_arn)

    assert resp["Tags"] == {"key1": "value1", "key3": "value3"}


@mock_aws
def test_get_tags_crawler():
    client = create_glue_client()
    crawler_name = create_test_crawler(client, {"key1": "value1", "key2": "value2"})
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:crawler/{crawler_name}"

    resp = client.get_tags(ResourceArn=resource_arn)

    assert resp["Tags"] == {"key1": "value1", "key2": "value2"}


@mock_aws
def test_get_tags_crawler_no_tags():
    client = create_glue_client()
    crawler_name = create_test_crawler(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:crawler/{crawler_name}"

    resp = client.get_tags(ResourceArn=resource_arn)

    assert resp["Tags"] == {}


@mock_aws
def test_tag_glue_crawler():
    client = create_glue_client()
    crawler_name = create_test_crawler(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:crawler/{crawler_name}"

    client.tag_resource(
        ResourceArn=resource_arn, TagsToAdd={"key1": "value1", "key2": "value2"}
    )

    resp = client.get_tags(ResourceArn=resource_arn)

    assert resp["Tags"] == {"key1": "value1", "key2": "value2"}


@mock_aws
def test_untag_glue_crawler():
    client = create_glue_client()
    crawler_name = create_test_crawler(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:crawler/{crawler_name}"

    client.tag_resource(
        ResourceArn=resource_arn,
        TagsToAdd={"key1": "value1", "key2": "value2", "key3": "value3"},
    )

    client.untag_resource(ResourceArn=resource_arn, TagsToRemove=["key2"])

    resp = client.get_tags(ResourceArn=resource_arn)

    assert resp["Tags"] == {"key1": "value1", "key3": "value3"}


@mock_aws
def test_batch_get_crawlers():
    client = create_glue_client()
    crawler_name = create_test_crawler(client)

    response = client.batch_get_crawlers(
        CrawlerNames=[crawler_name, "crawler-not-found"]
    )

    assert len(response["Crawlers"]) == 1
    assert len(response["CrawlersNotFound"]) == 1


@mock_aws
def test_create_trigger():
    client = create_glue_client()
    job_name = create_test_job(client)
    trigger_name = str(uuid4())

    response = client.create_trigger(
        Name=trigger_name,
        Type="ON_DEMAND",
        Actions=[
            {
                "JobName": job_name,
            }
        ],
    )
    assert response["Name"] == trigger_name


@mock_aws
def test_get_trigger_on_demand():
    client = create_glue_client()
    job_name = create_test_job(client)
    trigger_name = str(uuid4())
    trigger_attributes = {
        "Type": "ON_DEMAND",
        "Actions": [
            {
                "JobName": job_name,
            }
        ],
    }
    client.create_trigger(Name=trigger_name, **trigger_attributes)

    trigger = client.get_trigger(Name=trigger_name)["Trigger"]

    assert trigger["Name"] == trigger_name
    assert trigger["Type"] == "ON_DEMAND"
    assert trigger["State"] == "CREATED"
    assert trigger["Actions"] == [{"JobName": job_name}]


@mock_aws
def test_get_trigger_scheduled():
    client = create_glue_client()
    job_name = create_test_job(client)
    trigger_name = str(uuid4())
    trigger_attributes = {
        "Type": "SCHEDULED",
        "Schedule": "cron(5 3 * * ? *)",
        "Actions": [
            {
                "JobName": job_name,
            }
        ],
        "StartOnCreation": True,
    }
    client.create_trigger(Name=trigger_name, **trigger_attributes)

    trigger = client.get_trigger(Name=trigger_name)["Trigger"]

    assert trigger["Name"] == trigger_name
    assert trigger["Type"] == "SCHEDULED"
    assert trigger["State"] == "ACTIVATED"
    assert trigger["Actions"] == [{"JobName": job_name}]


@mock_aws
def test_get_trigger_conditional():
    client = create_glue_client()
    crawler_name = create_test_crawler(client)
    job_name = create_test_job(client)
    trigger_name = str(uuid4())
    trigger_attributes = {
        "Type": "CONDITIONAL",
        "Actions": [
            {
                "JobName": job_name,
            }
        ],
        "StartOnCreation": True,
        "Predicate": {
            "Logical": "ANY",
            "Conditions": [
                {
                    "LogicalOperator": "EQUALS",
                    "CrawlerName": crawler_name,
                    "CrawlState": "SUCCEEDED",
                }
            ],
        },
    }
    client.create_trigger(Name=trigger_name, **trigger_attributes)

    trigger = client.get_trigger(Name=trigger_name)["Trigger"]

    assert trigger["Name"] == trigger_name
    assert trigger["Type"] == "CONDITIONAL"
    assert trigger["State"] == "ACTIVATED"
    assert trigger["Actions"] == [{"JobName": job_name}]
    assert "Predicate" in trigger


def create_test_trigger(client, tags=None):
    job_name = create_test_job(client)
    trigger_name = str(uuid4())
    client.create_trigger(
        Name=trigger_name,
        Type="ON_DEMAND",
        Actions=[
            {
                "JobName": job_name,
            }
        ],
        Tags=tags or {},
    )
    return trigger_name


@mock_aws
def test_get_triggers_trigger_name_exists():
    client = create_glue_client()
    trigger_name = create_test_trigger(client)
    response = client.get_triggers()
    assert len(response["Triggers"]) == 1
    assert response["Triggers"][0]["Name"] == trigger_name


@mock_aws
def test_get_triggers_dependent_job_name():
    client = create_glue_client()

    create_test_trigger(client)
    job_name = create_test_job(client)
    trigger_name = str(uuid4())
    response = client.create_trigger(
        Name=trigger_name,
        Type="ON_DEMAND",
        Actions=[
            {
                "JobName": job_name,
            }
        ],
    )

    response = client.get_triggers(DependentJobName=job_name)
    assert len(response["Triggers"]) == 1
    assert response["Triggers"][0]["Name"] == trigger_name


@mock_aws
def test_start_trigger():
    client = create_glue_client()
    job_name = create_test_job(client)
    trigger_name = str(uuid4())
    trigger_attributes = {
        "Type": "SCHEDULED",
        "Schedule": "cron(5 3 * * ? *)",
        "Actions": [
            {
                "JobName": job_name,
            }
        ],
    }
    client.create_trigger(Name=trigger_name, **trigger_attributes)

    trigger = client.get_trigger(Name=trigger_name)["Trigger"]

    assert trigger["State"] == "CREATED"

    client.start_trigger(Name=trigger_name)

    trigger = client.get_trigger(Name=trigger_name)["Trigger"]

    assert trigger["State"] == "ACTIVATED"


@mock_aws
def test_stop_trigger():
    client = create_glue_client()
    job_name = create_test_job(client)
    trigger_name = str(uuid4())
    trigger_attributes = {
        "Type": "SCHEDULED",
        "Schedule": "cron(5 3 * * ? *)",
        "Actions": [
            {
                "JobName": job_name,
            }
        ],
        "StartOnCreation": True,
    }
    client.create_trigger(Name=trigger_name, **trigger_attributes)

    trigger = client.get_trigger(Name=trigger_name)["Trigger"]

    assert trigger["State"] == "ACTIVATED"

    client.stop_trigger(Name=trigger_name)

    trigger = client.get_trigger(Name=trigger_name)["Trigger"]

    assert trigger["State"] == "DEACTIVATED"


@mock_aws
def test_list_triggers():
    client = create_glue_client()
    trigger_name = create_test_trigger(client)
    response = client.list_triggers()
    assert response["TriggerNames"] == [trigger_name]
    assert "NextToken" not in response


@mock_aws
def test_list_triggers_dependent_job_name():
    client = create_glue_client()

    job_name = create_test_job(client)
    trigger_name = str(uuid4())
    trigger_attributes = {
        "Type": "ON_DEMAND",
        "Actions": [
            {
                "JobName": job_name,
            }
        ],
    }

    client.create_trigger(Name=trigger_name, **trigger_attributes)
    create_test_trigger(client)

    response = client.list_triggers()
    assert len(response["TriggerNames"]) == 2

    response = client.list_triggers(DependentJobName=job_name)
    assert len(response["TriggerNames"]) == 1
    assert response["TriggerNames"] == [trigger_name]


@mock_aws
def test_list_triggers_tags():
    client = create_glue_client()

    job_name = create_test_job(client)
    trigger_name = str(uuid4())
    trigger_attributes = {
        "Type": "ON_DEMAND",
        "Actions": [
            {
                "JobName": job_name,
            }
        ],
        "Tags": {
            "CreatedBy": "moto",
        },
    }

    client.create_trigger(Name=trigger_name, **trigger_attributes)
    create_test_trigger(client)

    response = client.list_triggers()
    assert len(response["TriggerNames"]) == 2

    response = client.list_triggers(Tags={"CreatedBy": "moto"})
    assert len(response["TriggerNames"]) == 1
    assert response["TriggerNames"] == [trigger_name]


@mock_aws
def test_batch_get_triggers():
    client = create_glue_client()
    trigger_name = create_test_trigger(client)

    response = client.batch_get_triggers(
        TriggerNames=[trigger_name, "trigger-not-found"]
    )

    assert len(response["Triggers"]) == 1
    assert len(response["TriggersNotFound"]) == 1


@mock_aws
def test_delete_trigger():
    client = create_glue_client()
    trigger_name = create_test_trigger(client)

    client.get_trigger(Name=trigger_name)

    client.delete_trigger(Name=trigger_name)

    with pytest.raises(ClientError) as exc:
        client.get_trigger(Name=trigger_name)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"


def create_test_session(client):
    session_id = str(uuid4())
    client.create_session(
        Id=session_id,
        Description="string",
        Role="arn_of_a_testing_role",
        Command={"Name": "string", "PythonVersion": "string"},
        Timeout=123,
        IdleTimeout=123,
        DefaultArguments={"string": "string"},
        Connections={
            "Connections": [
                "string",
            ]
        },
        MaxCapacity=123.0,
        NumberOfWorkers=123,
        WorkerType="Standard",
        SecurityConfiguration="string",
        GlueVersion="string",
        Tags={"string": "string"},
        RequestOrigin="string",
    )
    return session_id


@mock_aws
def test_create_session():
    client = create_glue_client()
    session_id = create_test_session(client)

    resp = client.get_session(Id=session_id)
    assert resp["Session"]["Id"] == session_id


@mock_aws
def test_get_session():
    client = create_glue_client()
    session_id = create_test_session(client)

    resp = client.get_session(Id=session_id)
    assert resp["Session"]["Id"] == session_id


@mock_aws
def test_list_sessions():
    client = create_glue_client()
    session_id = create_test_session(client)

    resp = client.list_sessions()
    assert session_id in resp["Ids"]


@mock_aws
def test_delete_session():
    client = create_glue_client()
    session_id = create_test_session(client)

    resp = client.delete_session(Id=session_id)
    assert resp["Id"] == session_id

    resp = client.list_sessions()
    assert session_id not in resp["Ids"]


@mock_aws
def test_stop_session():
    client = create_glue_client()
    session_id = create_test_session(client)

    resp = client.get_session(Id=session_id)
    assert resp["Session"]["Status"] == "READY"

    resp = client.stop_session(Id=session_id)
    assert resp["Id"] == session_id

    resp = client.get_session(Id=session_id)
    assert resp["Session"]["Status"] == "STOPPING"


@mock_aws
def test_get_dev_endpoints():
    client = create_glue_client()

    response = client.get_dev_endpoints()
    assert response["DevEndpoints"] == []
    assert "NextToken" not in response

    client.create_dev_endpoint(
        EndpointName="dev-endpoint-1",
        RoleArn="arn:aws:iam::123456789012:role/GlueDevEndpoint",
    )
    client.create_dev_endpoint(
        EndpointName="dev-endpoint-2",
        RoleArn="arn:aws:iam::123456789012:role/GlueDevEndpoint",
    )

    response = client.get_dev_endpoints()
    assert len(response["DevEndpoints"]) == 2
    assert {ep["EndpointName"] for ep in response["DevEndpoints"]} == {
        "dev-endpoint-1",
        "dev-endpoint-2",
    }
    assert "NextToken" not in response

    response = client.get_dev_endpoints(MaxResults=1)
    assert len(response["DevEndpoints"]) == 1
    assert "NextToken" in response

    next_token = response["NextToken"]
    response = client.get_dev_endpoints(NextToken=next_token)
    assert len(response["DevEndpoints"]) == 1
    assert "NextToken" not in response


@mock_aws
def test_create_dev_endpoint():
    client = create_glue_client()

    response = client.create_dev_endpoint(
        EndpointName="test-endpoint",
        RoleArn="arn:aws:iam::123456789012:role/GlueDevEndpoint",
    )

    assert response["EndpointName"] == "test-endpoint"
    assert response["Status"] == "READY"
    assert response["RoleArn"] == "arn:aws:iam::123456789012:role/GlueDevEndpoint"


@mock_aws
def test_get_dev_endpoint():
    client = create_glue_client()

    client.create_dev_endpoint(
        EndpointName="test-endpoint",
        RoleArn="arn:aws:iam::123456789012:role/GlueDevEndpoint",
    )

    response = client.get_dev_endpoint(EndpointName="test-endpoint")
    assert response["DevEndpoint"]["EndpointName"] == "test-endpoint"
    assert response["DevEndpoint"]["Status"] == "READY"
    assert "PublicAddress" in response["DevEndpoint"]

    with pytest.raises(client.exceptions.EntityNotFoundException):
        client.get_dev_endpoint(EndpointName="nonexistent")

    client.create_dev_endpoint(
        EndpointName="test-endpoint-private",
        RoleArn="arn:aws:iam::123456789012:role/GlueDevEndpoint",
        SubnetId="subnet-1234567890abcdef0",
    )

    response = client.get_dev_endpoint(EndpointName="test-endpoint-private")
    assert response["DevEndpoint"]["EndpointName"] == "test-endpoint-private"
    assert "PublicAddress" not in response["DevEndpoint"]


@mock_aws
def test_create_connection():
    client = boto3.client("glue", region_name="us-east-2")
    subnet_id = "subnet-1234567890abcdef0"
    connection_input = {
        "Name": "test-connection",
        "Description": "Test Connection",
        "ConnectionType": "JDBC",
        "ConnectionProperties": {"key": "value"},
        "PhysicalConnectionRequirements": {
            "SubnetId": subnet_id,
            "SecurityGroupIdList": [],
            "AvailabilityZone": "us-east-1a",
        },
    }
    resp = client.create_connection(ConnectionInput=connection_input)
    assert resp["CreateConnectionStatus"] == "READY"

    # Test duplicate name
    with pytest.raises(client.exceptions.AlreadyExistsException):
        client.create_connection(ConnectionInput=connection_input)


@mock_aws
def test_get_connection():
    client = boto3.client("glue", region_name="us-east-2")
    subnet_id = "subnet-1234567890abcdef0"
    connection_input = {
        "Name": "test-connection",
        "Description": "Test Connection",
        "ConnectionType": "JDBC",
        "ConnectionProperties": {"key": "value"},
        "PhysicalConnectionRequirements": {
            "SubnetId": subnet_id,
            "SecurityGroupIdList": [],
            "AvailabilityZone": "us-east-1a",
        },
    }
    client.create_connection(ConnectionInput=connection_input)
    connection = client.get_connection(Name="test-connection")["Connection"]
    assert connection["Name"] == "test-connection"
    assert connection["Status"] == "READY"
    assert "PhysicalConnectionRequirements" in connection_input
    assert connection["PhysicalConnectionRequirements"]["SubnetId"] == subnet_id

    # Test not found
    with pytest.raises(client.exceptions.EntityNotFoundException):
        client.get_connection(Name="nonexistent")


@mock_aws
def test_get_connections():
    client = boto3.client("glue", region_name="ap-southeast-1")
    for i in range(3):
        subnet_id = f"subnet-1234567890abcdef{i}"
        connection_input = {
            "Name": f"test-connection-{i}",
            "Description": "Test Connection",
            "ConnectionType": "JDBC",
            "ConnectionProperties": {"key": "value"},
            "PhysicalConnectionRequirements": {
                "SubnetId": subnet_id,
                "SecurityGroupIdList": [],
                "AvailabilityZone": "us-east-1a",
            },
        }
        client.create_connection(ConnectionInput=connection_input)

    connections = client.get_connections()["ConnectionList"]
    assert len(connections) == 3
    assert connections[0]["Name"] == "test-connection-0"
    assert connections[1]["Name"] == "test-connection-1"
    assert connections[2]["Name"] == "test-connection-2"


@mock_aws
def test_put_data_catalog_encryption_settings():
    client = boto3.client("glue", region_name="us-east-1")

    encryption_settings = {
        "EncryptionAtRest": {
            "CatalogEncryptionMode": "SSE-KMS",
            "SseAwsKmsKeyId": "test-key-id",
            "CatalogEncryptionServiceRole": "arn:aws:iam::123456789012:role/GlueServiceRole",
        },
        "ConnectionPasswordEncryption": {
            "ReturnConnectionPasswordEncrypted": True,
            "AwsKmsKeyId": "test-password-key-id",
        },
    }

    response = client.put_data_catalog_encryption_settings(
        DataCatalogEncryptionSettings=encryption_settings
    )

    assert "ResponseMetadata" in response
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    get_response = client.get_data_catalog_encryption_settings()
    assert get_response["DataCatalogEncryptionSettings"] == encryption_settings

    # Testing a Specific Catalog ID
    catalog_id = "123456789012"
    catalog_settings = {
        "EncryptionAtRest": {
            "CatalogEncryptionMode": "SSE-KMS-WITH-SERVICE-ROLE",
            "SseAwsKmsKeyId": "catalog-specific-key-id",
            "CatalogEncryptionServiceRole": "arn:aws:iam::123456789012:role/GlueServiceRole",
        },
        "ConnectionPasswordEncryption": {
            "ReturnConnectionPasswordEncrypted": True,
            "AwsKmsKeyId": "catalog-specific-password-key-id",
        },
    }

    catalog_response = client.put_data_catalog_encryption_settings(
        CatalogId=catalog_id, DataCatalogEncryptionSettings=catalog_settings
    )

    assert "ResponseMetadata" in catalog_response
    assert catalog_response["ResponseMetadata"]["HTTPStatusCode"] == 200

    catalog_get_response = client.get_data_catalog_encryption_settings(
        CatalogId=catalog_id
    )

    assert catalog_get_response["DataCatalogEncryptionSettings"] == catalog_settings


@mock_aws
def test_put_resource_policy():
    client = boto3.client("glue", region_name="us-east-1")

    policy_json = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "glue.amazonaws.com"},
                    "Action": ["glue:*"],
                    "Resource": ["*"],
                }
            ],
        }
    )

    response = client.put_resource_policy(PolicyInJson=policy_json)

    assert "PolicyHash" in response
    policy_hash = response["PolicyHash"]

    get_response = client.get_resource_policy()
    assert "PolicyInJson" in get_response
    assert get_response["PolicyInJson"] == policy_json
    assert "PolicyHash" in get_response
    assert get_response["PolicyHash"] == policy_hash
    assert "CreateTime" in get_response
    assert "UpdateTime" in get_response

    response = client.put_resource_policy(
        PolicyInJson=policy_json,
        PolicyHashCondition=policy_hash,
    )

    assert "PolicyHash" in response

    resource_arn = "arn:aws:glue:us-east-2:123456789012:catalog"
    response = client.put_resource_policy(
        PolicyInJson=policy_json, ResourceArn=resource_arn
    )

    assert "PolicyHash" in response

    get_resource_response = client.get_resource_policy(ResourceArn=resource_arn)
    assert "PolicyInJson" in get_resource_response
    assert get_resource_response["PolicyInJson"] == policy_json

    response = client.put_resource_policy(
        PolicyInJson=policy_json,
        ResourceArn=resource_arn,
        PolicyExistsCondition="MUST_EXIST",
    )
    assert "PolicyHash" in response

    unique_arn = "arn:aws:glue:us-east-2:123456789012:unique-resource"
    response = client.put_resource_policy(
        PolicyInJson=policy_json, ResourceArn=unique_arn, PolicyExistsCondition="NONE"
    )
    assert "PolicyHash" in response

    response = client.put_resource_policy(PolicyInJson=policy_json, EnableHybrid="TRUE")
    assert "PolicyHash" in response


@mock_aws
def test_get_resource_policy():
    client = boto3.client("glue", region_name="us-east-1")

    response = client.get_resource_policy()
    assert "PolicyInJson" not in response

    policy_json = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "glue.amazonaws.com"},
                    "Action": ["glue:*"],
                    "Resource": ["*"],
                }
            ],
        }
    )

    put_response = client.put_resource_policy(PolicyInJson=policy_json)

    response = client.get_resource_policy()

    assert "PolicyInJson" in response
    assert response["PolicyInJson"] == policy_json
    assert "PolicyHash" in response

    if (
        isinstance(put_response["PolicyHash"], dict)
        and "PolicyHash" in put_response["PolicyHash"]
    ):
        assert response["PolicyHash"] == put_response["PolicyHash"]["PolicyHash"]
    else:
        assert response["PolicyHash"] == put_response["PolicyHash"]

    assert "CreateTime" in response
    assert "UpdateTime" in response

    catalog_arn = "arn:aws:glue:us-east-1:123456789012:catalog"
    database_arn = "arn:aws:glue:us-east-1:123456789012:database/mydb"
    table_arn = "arn:aws:glue:us-east-1:123456789012:table/mydb/mytable"

    catalog_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                    "Action": ["glue:*"],
                    "Resource": [catalog_arn],
                }
            ],
        }
    )
    client.put_resource_policy(PolicyInJson=catalog_policy, ResourceArn=catalog_arn)

    database_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::123456789012:role/GlueRole"},
                    "Action": ["glue:GetDatabase", "glue:UpdateDatabase"],
                    "Resource": [database_arn],
                }
            ],
        }
    )
    client.put_resource_policy(PolicyInJson=database_policy, ResourceArn=database_arn)

    table_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::987654321098:root"},
                    "Action": ["glue:GetTable"],
                    "Resource": [table_arn],
                }
            ],
        }
    )
    client.put_resource_policy(PolicyInJson=table_policy, ResourceArn=table_arn)

    catalog_response = client.get_resource_policy(ResourceArn=catalog_arn)
    assert catalog_response["PolicyInJson"] == catalog_policy

    database_response = client.get_resource_policy(ResourceArn=database_arn)
    assert database_response["PolicyInJson"] == database_policy

    table_response = client.get_resource_policy(ResourceArn=table_arn)
    assert table_response["PolicyInJson"] == table_policy

    nonexistent_response = client.get_resource_policy(
        ResourceArn="arn:aws:glue:us-east-1:123456789012:nonexistent"
    )
    assert "PolicyInJson" not in nonexistent_response


@mock_aws
def test_put_resource_policy_error_conditions():
    client = boto3.client("glue", region_name="us-east-1")

    policy_json = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "glue.amazonaws.com"},
                    "Action": ["glue:*"],
                    "Resource": ["*"],
                }
            ],
        }
    )

    resource_arn = "arn:aws:glue:us-west-2:123456789012:catalog"

    response = client.put_resource_policy(
        PolicyInJson=policy_json,
        ResourceArn=resource_arn,
        PolicyExistsCondition="NOT_EXIST",
    )
    assert "PolicyHash" in response

    with pytest.raises(ClientError) as excinfo:
        client.put_resource_policy(
            PolicyInJson=policy_json,
            ResourceArn=resource_arn,
            PolicyExistsCondition="NOT_EXIST",
        )
    assert "ResourceNumberLimitExceededException" in str(excinfo.value)

    with pytest.raises(ClientError) as excinfo:
        client.put_resource_policy(
            PolicyInJson=policy_json,
            ResourceArn=resource_arn,
            PolicyHashCondition="incorrect-hash",
        )
    assert "ConcurrentModificationException" in str(excinfo.value)

    nonexistent_arn = "arn:aws:glue:us-west-2:123456789012:nonexistent-resource"
    with pytest.raises(ClientError) as excinfo:
        client.put_resource_policy(
            PolicyInJson=policy_json,
            ResourceArn=nonexistent_arn,
            PolicyExistsCondition="MUST_EXIST",
        )
    assert "ResourceNumberLimitExceededException" in str(excinfo.value)
