"""Unit tests for glue-supported APIs."""
from random import randint
from uuid import uuid4

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ParamValidationError
from botocore.client import ClientError
from moto.core import ACCOUNT_ID

from moto import mock_glue


@mock_glue
def test_create_job():
    client = create_glue_client()
    job_name = str(uuid4())
    response = client.create_job(
        Name=job_name, Role="test_role", Command=dict(Name="test_command")
    )
    assert response["Name"] == job_name


@mock_glue
def test_create_job_default_argument_not_provided():
    client = create_glue_client()
    with pytest.raises(ParamValidationError) as exc:
        client.create_job(Role="test_role", Command=dict(Name="test_command"))

    exc.value.kwargs["report"].should.equal(
        'Missing required parameter in input: "Name"'
    )


@mock_glue
def test_list_jobs():
    client = create_glue_client()
    expected_jobs = randint(1, 15)
    create_test_jobs(client, expected_jobs)
    response = client.list_jobs()
    response["JobNames"].should.have.length_of(expected_jobs)
    response.shouldnt.have.key("NextToken")


@mock_glue
def test_get_job_not_exists():
    client = create_glue_client()
    name = "my_job_name"

    with pytest.raises(ClientError) as exc:
        client.get_job(JobName=name)

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match("Job my_job_name not found")


@mock_glue
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
    }
    job_name = create_test_job_w_all_attributes(client, **job_attributes)
    response = client.get_job(JobName=job_name)
    assert response["Job"]["Name"] == job_name
    assert response["Job"]["Description"]
    assert response["Job"]["LogUri"]
    assert response["Job"]["Role"]
    assert response["Job"]["CreatedOn"]
    assert response["Job"]["LastModifiedOn"]
    assert response["Job"]["ExecutionProperty"]
    assert response["Job"]["Command"]
    assert response["Job"]["DefaultArguments"]
    assert response["Job"]["NonOverridableArguments"]
    assert response["Job"]["Connections"]
    assert response["Job"]["MaxRetries"]
    assert response["Job"]["AllocatedCapacity"]
    assert response["Job"]["Timeout"]
    assert response["Job"]["MaxCapacity"]
    assert response["Job"]["WorkerType"]
    assert response["Job"]["NumberOfWorkers"]
    assert response["Job"]["SecurityConfiguration"]
    assert response["Job"]["NotificationProperty"]
    assert response["Job"]["GlueVersion"]


@mock_glue
def test_start_job_run():
    client = create_glue_client()
    job_name = create_test_job(client)
    response = client.start_job_run(JobName=job_name)
    assert response["JobRunId"]


@mock_glue
def test_start_job_run_already_running():
    client = create_glue_client()
    job_name = create_test_job(client)
    client.start_job_run(JobName=job_name)
    with pytest.raises(ClientError) as exc:
        client.start_job_run(JobName=job_name)
    exc.value.response["Error"]["Code"].should.equal("ConcurrentRunsExceededException")
    exc.value.response["Error"]["Message"].should.match(
        f"Job with name {job_name} already running"
    )


@mock_glue
def test_get_job_run():
    client = create_glue_client()
    job_name = create_test_job(client)
    response = client.get_job_run(JobName=job_name, RunId="01")
    assert response["JobRun"]["Id"]
    assert response["JobRun"]["Attempt"]
    assert response["JobRun"]["PreviousRunId"]
    assert response["JobRun"]["TriggerName"]
    assert response["JobRun"]["StartedOn"]
    assert response["JobRun"]["LastModifiedOn"]
    assert response["JobRun"]["CompletedOn"]
    assert response["JobRun"]["JobRunState"]
    assert response["JobRun"]["Arguments"]
    assert response["JobRun"]["ErrorMessage"] == ""
    assert response["JobRun"]["PredecessorRuns"]
    assert response["JobRun"]["AllocatedCapacity"]
    assert response["JobRun"]["ExecutionTime"]
    assert response["JobRun"]["Timeout"]
    assert response["JobRun"]["MaxCapacity"]
    assert response["JobRun"]["WorkerType"]
    assert response["JobRun"]["NumberOfWorkers"]
    assert response["JobRun"]["SecurityConfiguration"]
    assert response["JobRun"]["LogGroupName"]
    assert response["JobRun"]["NotificationProperty"]
    assert response["JobRun"]["GlueVersion"]


@mock_glue
def test_list_jobs_with_max_results():
    client = create_glue_client()
    create_test_jobs(client, 4)
    response = client.list_jobs(MaxResults=2)
    response["JobNames"].should.have.length_of(2)
    response.should.have.key("NextToken")


@mock_glue
def test_list_jobs_from_next_token():
    client = create_glue_client()
    create_test_jobs(client, 10)
    first_response = client.list_jobs(MaxResults=3)
    response = client.list_jobs(NextToken=first_response["NextToken"])
    response["JobNames"].should.have.length_of(7)


@mock_glue
def test_list_jobs_with_max_results_greater_than_actual_results():
    client = create_glue_client()
    create_test_jobs(client, 4)
    response = client.list_jobs(MaxResults=10)
    response["JobNames"].should.have.length_of(4)


@mock_glue
def test_list_jobs_with_tags():
    client = create_glue_client()
    create_test_job(client)
    create_test_job(client, {"string": "string"})
    response = client.list_jobs(Tags={"string": "string"})
    response["JobNames"].should.have.length_of(1)


@mock_glue
def test_list_jobs_after_tagging():
    client = create_glue_client()
    job_name = create_test_job(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:job/{job_name}"

    client.tag_resource(ResourceArn=resource_arn, TagsToAdd={"key1": "value1"})

    response = client.list_jobs(Tags={"key1": "value1"})
    response["JobNames"].should.have.length_of(1)


@mock_glue
def test_list_jobs_after_removing_tag():
    client = create_glue_client()
    job_name = create_test_job(client, {"key1": "value1"})
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:job/{job_name}"

    client.untag_resource(ResourceArn=resource_arn, TagsToRemove=["key1"])

    response = client.list_jobs(Tags={"key1": "value1"})
    response["JobNames"].should.have.length_of(0)


@mock_glue
def test_list_jobs_next_token_logic_does_not_create_infinite_loop():
    client = create_glue_client()
    create_test_jobs(client, 4)
    first_response = client.list_jobs(MaxResults=1)
    next_token = first_response["NextToken"]
    while next_token:
        response = client.list_jobs(NextToken=next_token)
        next_token = response.get("NextToken")
    assert not next_token


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


@mock_glue
def test_list_crawlers_with_max_results():
    client = create_glue_client()
    create_test_crawlers(client, 4)
    response = client.list_crawlers(MaxResults=2)
    response["CrawlerNames"].should.have.length_of(2)
    response.should.have.key("NextToken")


@mock_glue
def test_list_crawlers_from_next_token():
    client = create_glue_client()
    create_test_crawlers(client, 10)
    first_response = client.list_crawlers(MaxResults=3)
    response = client.list_crawlers(NextToken=first_response["NextToken"])
    response["CrawlerNames"].should.have.length_of(7)


@mock_glue
def test_list_crawlers_with_max_results_greater_than_actual_results():
    client = create_glue_client()
    create_test_crawlers(client, 4)
    response = client.list_crawlers(MaxResults=10)
    response["CrawlerNames"].should.have.length_of(4)


@mock_glue
def test_list_crawlers_with_tags():
    client = create_glue_client()
    create_test_crawler(client)
    create_test_crawler(client, {"string": "string"})
    response = client.list_crawlers(Tags={"string": "string"})
    response["CrawlerNames"].should.have.length_of(1)


@mock_glue
def test_list_crawlers_after_tagging():
    client = create_glue_client()
    crawler_name = create_test_crawler(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:crawler/{crawler_name}"

    client.tag_resource(ResourceArn=resource_arn, TagsToAdd={"key1": "value1"})

    response = client.list_crawlers(Tags={"key1": "value1"})
    response["CrawlerNames"].should.have.length_of(1)


@mock_glue
def test_list_crawlers_after_removing_tag():
    client = create_glue_client()
    crawler_name = create_test_crawler(client, {"key1": "value1"})
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:crawler/{crawler_name}"

    client.untag_resource(ResourceArn=resource_arn, TagsToRemove=["key1"])

    response = client.list_crawlers(Tags={"key1": "value1"})
    response["CrawlerNames"].should.have.length_of(0)


@mock_glue
def test_list_crawlers_next_token_logic_does_not_create_infinite_loop():
    client = create_glue_client()
    create_test_crawlers(client, 4)
    first_response = client.list_crawlers(MaxResults=1)
    next_token = first_response["NextToken"]
    while next_token:
        response = client.list_crawlers(NextToken=next_token)
        next_token = response.get("NextToken")
    assert not next_token


@mock_glue
def test_get_tags_job():
    client = create_glue_client()
    job_name = create_test_job(client, {"key1": "value1", "key2": "value2"})
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:job/{job_name}"

    resp = client.get_tags(ResourceArn=resource_arn)

    resp.should.have.key("Tags").equals({"key1": "value1", "key2": "value2"})


@mock_glue
def test_get_tags_jobs_no_tags():
    client = create_glue_client()
    job_name = create_test_job(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:job/{job_name}"

    resp = client.get_tags(ResourceArn=resource_arn)

    resp.should.have.key("Tags").equals({})


@mock_glue
def test_tag_glue_job():
    client = create_glue_client()
    job_name = create_test_job(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:job/{job_name}"

    client.tag_resource(
        ResourceArn=resource_arn, TagsToAdd={"key1": "value1", "key2": "value2"}
    )

    resp = client.get_tags(ResourceArn=resource_arn)

    resp.should.have.key("Tags").equals({"key1": "value1", "key2": "value2"})


@mock_glue
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

    resp.should.have.key("Tags").equals({"key1": "value1", "key3": "value3"})


@mock_glue
def test_get_tags_crawler():
    client = create_glue_client()
    crawler_name = create_test_crawler(client, {"key1": "value1", "key2": "value2"})
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:crawler/{crawler_name}"

    resp = client.get_tags(ResourceArn=resource_arn)

    resp.should.have.key("Tags").equals({"key1": "value1", "key2": "value2"})


@mock_glue
def test_get_tags_crawler_no_tags():
    client = create_glue_client()
    crawler_name = create_test_crawler(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:crawler/{crawler_name}"

    resp = client.get_tags(ResourceArn=resource_arn)

    resp.should.have.key("Tags").equals({})


@mock_glue
def test_tag_glue_crawler():
    client = create_glue_client()
    crawler_name = create_test_crawler(client)
    resource_arn = f"arn:aws:glue:us-east-1:123456789012:crawler/{crawler_name}"

    client.tag_resource(
        ResourceArn=resource_arn, TagsToAdd={"key1": "value1", "key2": "value2"}
    )

    resp = client.get_tags(ResourceArn=resource_arn)

    resp.should.have.key("Tags").equals({"key1": "value1", "key2": "value2"})


@mock_glue
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

    resp.should.have.key("Tags").equals({"key1": "value1", "key3": "value3"})


@mock_glue
def test_create_registry_valid_input():
    client = create_glue_client()
    registry_name = "TestRegistry"
    response = client.create_registry(
        RegistryName=registry_name,
        Description="test_create_registry_description",
        Tags={"key1": "value1", "key2": "value2"},
    )
    response.should.have.key("RegistryName").equals("TestRegistry")
    response.should.have.key("Description").equals("test_create_registry_description")
    response.should.have.key("Tags").equals({"key1": "value1", "key2": "value2"})
    response.should.have.key("RegistryArn").equals(
        f"arn:aws:glue:us-east-1:{ACCOUNT_ID}:registry/" + registry_name
    )


@mock_glue
def test_create_registry_valid_partial_input():
    client = create_glue_client()
    registry_name = "TestRegistry"
    response = client.create_registry(RegistryName=registry_name)
    response.should.have.key("RegistryName").equals("TestRegistry")
    response.should.have.key("RegistryArn").equals(
        f"arn:aws:glue:us-east-1:{ACCOUNT_ID}:registry/" + registry_name
    )


@mock_glue
def test_create_registry_invalid_input_registry_name_too_long():
    client = create_glue_client()
    registry_name = ""
    for _ in range(90):
        registry_name = registry_name + "foobar"

    with pytest.raises(ClientError) as exc:
        client.create_registry(
            RegistryName=registry_name,
            Description="test_create_registry_description",
            Tags={"key1": "value1", "key2": "value2"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal(
        "An error occurred (InvalidInputException) when calling the CreateRegistry operation: The resource name contains too many or too few characters. Parameter Name: registryName"
    )


@mock_glue
def test_create_registry_more_than_allowed():
    client = create_glue_client()

    for i in range(10):
        registry_name = "TestRegistry" + str(i)
        client.create_registry(
            RegistryName=registry_name,
            Description="test_create_registry_description",
            Tags={"key1": "value1", "key2": "value2"},
        )

    with pytest.raises(ClientError) as exc:
        client.create_registry(
            RegistryName="TestRegistry10",
            Description="test_create_registry_description10",
            Tags={"key1": "value1", "key2": "value2"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNumberLimitExceededException")
    err["Message"].should.equal(
        "An error occurred (ResourceNumberLimitExceededException) when calling the CreateRegistry operation: More registries cannot be created. The maximum limit has been reached."
    )


@mock_glue
def test_create_registry_invalid_registry_name():
    client = create_glue_client()

    with pytest.raises(ClientError) as exc:
        client.create_registry(
            RegistryName="A,B,C",
            Description="test_create_registry_description",
            Tags={"key1": "value1", "key2": "value2"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal(
        "An error occurred (InvalidInputException) when calling the CreateRegistry operation: The parameter value contains one or more characters that are not valid. Parameter Name: registryName"
    )


@mock_glue
def test_create_registry_already_exists():
    client = create_glue_client()

    client.create_registry(
        RegistryName="TestRegistry1",
        Description="test_create_registry_description1",
        Tags={"key1": "value1", "key2": "value2"},
    )

    with pytest.raises(ClientError) as exc:
        client.create_registry(
            RegistryName="TestRegistry1",
            Description="test_create_registry_description1",
            Tags={"key1": "value1", "key2": "value2"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("AlreadyExistsException")
    err["Message"].should.equal(
        "An error occurred (AlreadyExistsException) when calling the CreateRegistry operation: Registry already exists. RegistryName: TestRegistry1"
    )


@mock_glue
def test_create_registry_invalid_description_too_long():
    client = create_glue_client()
    description = ""
    for _ in range(300):
        description = description + "foobar, "

    with pytest.raises(ClientError) as exc:
        client.create_registry(
            RegistryName="TestRegistry1",
            Description=description,
            Tags={"key1": "value1", "key2": "value2"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal(
        "An error occurred (InvalidInputException) when calling the CreateRegistry operation: The resource name contains too many or too few characters. Parameter Name: description"
    )


@mock_glue
def test_create_registry_invalid_number_of_tags():
    tags = {}
    for i in range(51):
        key = "k" + str(i)
        val = "v" + str(i)
        tags[key] = val

    client = create_glue_client()
    with pytest.raises(ClientError) as exc:
        client.create_registry(
            RegistryName="TestRegistry1",
            Description="test_create_registry_description",
            Tags=tags,
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidInputException")
    err["Message"].should.equal(
        "An error occurred (InvalidInputException) when calling the CreateRegistry operation: New Tags cannot be empty or more than 50"
    )
