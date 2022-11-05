import uuid

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_databrew
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


def _create_databrew_client():
    client = boto3.client("databrew", region_name="us-west-1")
    return client


def _create_test_profile_job(
    client,
    dataset_name=None,
    job_name=None,
    output_location=None,
    role_arn=None,
    tags=None,
):
    kwargs = {}
    kwargs["Name"] = job_name or str(uuid.uuid4())
    kwargs["RoleArn"] = role_arn or str(uuid.uuid4())
    kwargs["DatasetName"] = dataset_name or str(uuid.uuid4())
    kwargs["OutputLocation"] = output_location or {"Bucket": str(uuid.uuid4())}
    if tags is not None:
        kwargs["Tags"] = tags

    return client.create_profile_job(**kwargs)


def _create_test_recipe_job(
    client,
    job_name=None,
    role_arn=None,
    tags=None,
    encryption_mode=None,
    log_subscription=None,
    dataset_name=None,
    project_name=None,
):
    kwargs = {}
    kwargs["Name"] = job_name or str(uuid.uuid4())
    kwargs["RoleArn"] = role_arn or str(uuid.uuid4())
    if tags is not None:
        kwargs["Tags"] = tags
    if encryption_mode is not None:
        kwargs["EncryptionMode"] = encryption_mode
    if log_subscription is not None:
        kwargs["LogSubscription"] = log_subscription
    if dataset_name is not None:
        kwargs["DatasetName"] = dataset_name
    if project_name is not None:
        kwargs["ProjectName"] = project_name

    return client.create_recipe_job(**kwargs)


def _create_test_recipe_jobs(client, count, **kwargs):
    for _ in range(count):
        _create_test_recipe_job(client, **kwargs)


def _create_test_profile_jobs(client, count, **kwargs):
    for _ in range(count):
        _create_test_profile_job(client, **kwargs)


@mock_databrew
def test_create_profile_job_that_already_exists():
    client = _create_databrew_client()

    response = _create_test_profile_job(client)
    job_name = response["Name"]
    with pytest.raises(ClientError) as exc:
        _create_test_profile_job(client, job_name=response["Name"])
    err = exc.value.response["Error"]
    err["Code"].should.equal("ConflictException")
    err["Message"].should.equal(f"The job {job_name} profile job already exists.")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(409)


@mock_databrew
def test_create_recipe_job_that_already_exists():
    client = _create_databrew_client()

    response = _create_test_recipe_job(client)
    job_name = response["Name"]
    with pytest.raises(ClientError) as exc:
        _create_test_recipe_job(client, job_name=response["Name"])
    err = exc.value.response["Error"]
    err["Code"].should.equal("ConflictException")
    err["Message"].should.equal(f"The job {job_name} recipe job already exists.")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(409)


@mock_databrew
def test_create_recipe_job_with_invalid_encryption_mode():
    client = _create_databrew_client()

    with pytest.raises(ClientError) as exc:
        _create_test_recipe_job(client, encryption_mode="INVALID")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "1 validation error detected: Value 'INVALID' at 'encryptionMode' failed to satisfy constraint: "
        "Member must satisfy enum value set: [SSE-S3, SSE-KMS]"
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_databrew
def test_create_recipe_job_with_invalid_log_subscription_value():
    client = _create_databrew_client()

    with pytest.raises(ClientError) as exc:
        _create_test_recipe_job(client, log_subscription="INVALID")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "1 validation error detected: Value 'INVALID' at 'logSubscription' failed to satisfy constraint: "
        "Member must satisfy enum value set: [ENABLE, DISABLE]"
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_databrew
def test_create_recipe_job_with_same_name_as_profile_job():
    client = _create_databrew_client()

    response = _create_test_profile_job(client)
    job_name = response["Name"]
    with pytest.raises(ClientError) as exc:
        _create_test_recipe_job(client, job_name=response["Name"])
    err = exc.value.response["Error"]
    err["Code"].should.equal("ConflictException")
    err["Message"].should.equal(f"The job {job_name} profile job already exists.")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(409)


@mock_databrew
def test_describe_recipe_job():
    client = _create_databrew_client()

    response = _create_test_recipe_job(client)
    job_name = response["Name"]
    job = client.describe_job(Name=job_name)
    job.should.have.key("Name").equal(response["Name"])
    job.should.have.key("Type").equal("RECIPE")
    job.should.have.key("ResourceArn").equal(
        f"arn:aws:databrew:us-west-1:{ACCOUNT_ID}:job/{job_name}"
    )
    job["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_databrew
def test_describe_job_that_does_not_exist():
    client = _create_databrew_client()

    with pytest.raises(ClientError) as exc:
        client.describe_job(Name="DoesNotExist")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("Job DoesNotExist wasn't found.")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)


@mock_databrew
def test_describe_job_with_long_name():
    client = _create_databrew_client()
    name = "a" * 241
    with pytest.raises(ClientError) as exc:
        client.describe_job(Name=name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        f"1 validation error detected: Value '{name}' at 'name' failed to satisfy constraint: "
        f"Member must have length less than or equal to 240"
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_databrew
def test_update_profile_job():
    client = _create_databrew_client()

    # Create the job
    response = _create_test_profile_job(client)
    job_name = response["Name"]

    # Update the job by changing RoleArn
    update_response = client.update_profile_job(
        Name=job_name, RoleArn="a" * 20, OutputLocation={"Bucket": "b" * 20}
    )
    update_response.should.have.key("Name").equals(job_name)
    update_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # Describe the job to check that RoleArn was updated
    job = client.describe_job(Name=job_name)
    job.should.have.key("Name").equal(response["Name"])
    job.should.have.key("RoleArn").equal("a" * 20)


@mock_databrew
def test_update_recipe_job():
    client = _create_databrew_client()

    # Create the job
    response = _create_test_recipe_job(client)
    job_name = response["Name"]

    # Update the job by changing RoleArn
    update_response = client.update_recipe_job(Name=job_name, RoleArn="a" * 20)
    update_response.should.have.key("Name").equals(job_name)
    update_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # Describe the job to check that RoleArn was updated
    job = client.describe_job(Name=job_name)
    job.should.have.key("Name").equal(response["Name"])
    job.should.have.key("RoleArn").equal("a" * 20)


@mock_databrew
def test_update_profile_job_does_not_exist():
    client = _create_databrew_client()

    with pytest.raises(ClientError) as exc:
        client.update_profile_job(
            Name="DoesNotExist", RoleArn="a" * 20, OutputLocation={"Bucket": "b" * 20}
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("The job DoesNotExist wasn't found")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)


@mock_databrew
def test_update_recipe_job_does_not_exist():
    client = _create_databrew_client()

    with pytest.raises(ClientError) as exc:
        client.update_recipe_job(Name="DoesNotExist", RoleArn="a" * 20)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("The job DoesNotExist wasn't found")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)


@mock_databrew
def test_delete_job():
    client = _create_databrew_client()

    # Create the job
    response = _create_test_recipe_job(client)
    job_name = response["Name"]

    # Delete the job
    response = client.delete_job(Name=job_name)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["Name"].should.equal(job_name)

    # Check the job does not exist anymore
    with pytest.raises(ClientError) as exc:
        client.describe_job(Name=job_name)

    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(f"Job {job_name} wasn't found.")


@mock_databrew
def test_delete_job_does_not_exist():
    client = _create_databrew_client()

    # Delete the job
    with pytest.raises(ClientError) as exc:
        client.delete_job(Name="DoesNotExist")
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)

    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("The job DoesNotExist wasn't found.")


@mock_databrew
def test_delete_job_with_long_name():
    client = _create_databrew_client()
    name = "a" * 241
    with pytest.raises(ClientError) as exc:
        client.delete_job(Name=name)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        f"1 validation error detected: Value '{name}' at 'name' failed to satisfy constraint: "
        f"Member must have length less than or equal to 240"
    )
    exc.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_databrew
def test_job_list_when_empty():
    client = _create_databrew_client()

    response = client.list_jobs()
    response.should.have.key("Jobs")
    response["Jobs"].should.have.length_of(0)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_databrew
def test_list_jobs_with_max_results():
    client = _create_databrew_client()

    _create_test_recipe_jobs(client, 4)
    response = client.list_jobs(MaxResults=2)
    response["Jobs"].should.have.length_of(2)
    response.should.have.key("NextToken")
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_databrew
def test_list_jobs_from_next_token():
    client = _create_databrew_client()
    _create_test_recipe_jobs(client, 10)
    first_response = client.list_jobs(MaxResults=3)
    response = client.list_jobs(NextToken=first_response["NextToken"])
    response["Jobs"].should.have.length_of(7)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_databrew
def test_list_jobs_with_max_results_greater_than_actual_results():
    client = _create_databrew_client()
    _create_test_recipe_jobs(client, 4)
    response = client.list_jobs(MaxResults=10)
    response["Jobs"].should.have.length_of(4)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_databrew
def test_list_jobs_recipe_and_profile():
    client = _create_databrew_client()

    _create_test_recipe_jobs(client, 4)
    _create_test_profile_jobs(client, 2)
    response = client.list_jobs()
    response["Jobs"].should.have.length_of(6)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_databrew
def test_list_jobs_dataset_name_filter():
    client = _create_databrew_client()

    _create_test_recipe_jobs(client, 3, dataset_name="TEST")
    _create_test_recipe_jobs(client, 1)
    _create_test_profile_jobs(client, 4, dataset_name="TEST")
    _create_test_profile_jobs(client, 1)

    response = client.list_jobs(DatasetName="TEST")
    response["Jobs"].should.have.length_of(7)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_databrew
def test_list_jobs_project_name_filter():
    client = _create_databrew_client()

    _create_test_recipe_jobs(client, 3, project_name="TEST_PROJECT")
    _create_test_recipe_jobs(client, 1)
    _create_test_profile_jobs(client, 1)

    response = client.list_jobs(ProjectName="TEST_PROJECT")
    response["Jobs"].should.have.length_of(3)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_databrew
def test_list_jobs_dataset_name_and_project_name_filter():
    client = _create_databrew_client()

    _create_test_recipe_jobs(client, 1, dataset_name="TEST")
    _create_test_recipe_jobs(client, 1, project_name="TEST_PROJECT")
    _create_test_recipe_jobs(
        client, 10, dataset_name="TEST", project_name="TEST_PROJECT"
    )
    _create_test_recipe_jobs(client, 1)
    _create_test_profile_jobs(client, 1)

    response = client.list_jobs(DatasetName="TEST", ProjectName="TEST_PROJECT")
    response["Jobs"].should.have.length_of(10)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
