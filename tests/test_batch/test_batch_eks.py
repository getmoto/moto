"""Tests for EKS properties support in AWS Batch."""

from uuid import uuid4

import pytest

from moto import mock_aws

from . import _get_clients, _setup


@mock_aws
def test_register_job_definition_with_eks_properties():
    """Test registering a job definition with eksProperties."""
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    job_def_name = f"eks-job-{str(uuid4())[0:6]}"

    resp = batch_client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        eksProperties={
            "podProperties": {
                "containers": [
                    {
                        "image": "python:3.11",
                        "command": ["python", "-c", "print('hello')"],
                        "env": [{"name": "MY_VAR", "value": "my_value"}],
                        "resources": {
                            "requests": {"cpu": "1", "memory": "1024Mi"},
                            "limits": {"cpu": "2", "memory": "2048Mi"},
                        },
                    }
                ]
            }
        },
    )

    assert "jobDefinitionArn" in resp
    assert resp["revision"] == 1

    # Describe and verify
    job_defs = batch_client.describe_job_definitions(jobDefinitionName=job_def_name)[
        "jobDefinitions"
    ]

    assert len(job_defs) == 1
    job_def = job_defs[0]

    assert "eksProperties" in job_def
    assert "containerProperties" not in job_def

    pod_props = job_def["eksProperties"]["podProperties"]
    assert len(pod_props["containers"]) == 1
    assert pod_props["containers"][0]["image"] == "python:3.11"
    assert pod_props["containers"][0]["command"] == ["python", "-c", "print('hello')"]
    assert pod_props["containers"][0]["env"] == [{"name": "MY_VAR", "value": "my_value"}]


@mock_aws
def test_submit_job_with_eks_properties_override():
    """Test submitting an EKS job with overrides."""
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    # Create compute environment and queue
    compute_name = str(uuid4())
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    compute_arn = resp["computeEnvironmentArn"]

    resp = batch_client.create_job_queue(
        jobQueueName=str(uuid4()),
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": compute_arn}],
    )
    queue_arn = resp["jobQueueArn"]

    # Register EKS job definition
    job_def_name = f"eks-job-{str(uuid4())[0:6]}"
    batch_client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        eksProperties={
            "podProperties": {
                "containers": [
                    {
                        "image": "python:3.11",
                        "command": ["sleep", "10"],
                        "env": [
                            {"name": "VAR1", "value": "from_definition"},
                            {"name": "VAR2", "value": "from_definition"},
                        ],
                    }
                ]
            }
        },
    )

    # Submit job with overrides
    resp = batch_client.submit_job(
        jobName="test-eks-job",
        jobQueue=queue_arn,
        jobDefinition=job_def_name,
        eksPropertiesOverride={
            "podProperties": {
                "containers": [
                    {
                        "command": ["python", "my_script.py"],
                        "env": [
                            {"name": "VAR1", "value": "from_override"},
                            {"name": "VAR3", "value": "from_override"},
                        ],
                    }
                ]
            }
        },
    )

    job_id = resp["jobId"]

    # Describe and verify merged properties
    jobs = batch_client.describe_jobs(jobs=[job_id])["jobs"]
    assert len(jobs) == 1

    job = jobs[0]
    assert "eksProperties" in job

    containers = job["eksProperties"]["podProperties"]["containers"]
    assert len(containers) == 1

    container = containers[0]
    # Command should be overridden
    assert container["command"] == ["python", "my_script.py"]
    # Image should remain from definition
    assert container["image"] == "python:3.11"

    # Environment should be merged
    env_dict = {e["name"]: e["value"] for e in container["env"]}
    assert env_dict["VAR1"] == "from_override"  # Overridden
    assert env_dict["VAR2"] == "from_definition"  # Kept from definition
    assert env_dict["VAR3"] == "from_override"  # Added from override


@mock_aws
def test_submit_eks_job_without_override():
    """Test submitting an EKS job without overrides returns original properties."""
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    # Create compute environment and queue
    compute_name = str(uuid4())
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    compute_arn = resp["computeEnvironmentArn"]

    resp = batch_client.create_job_queue(
        jobQueueName=str(uuid4()),
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": compute_arn}],
    )
    queue_arn = resp["jobQueueArn"]

    # Register EKS job definition
    job_def_name = f"eks-job-{str(uuid4())[0:6]}"
    batch_client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        eksProperties={
            "podProperties": {
                "containers": [
                    {
                        "image": "python:3.11",
                        "command": ["sleep", "10"],
                        "env": [{"name": "MY_VAR", "value": "my_value"}],
                    }
                ]
            }
        },
    )

    # Submit job without overrides
    resp = batch_client.submit_job(
        jobName="test-eks-job",
        jobQueue=queue_arn,
        jobDefinition=job_def_name,
    )

    job_id = resp["jobId"]

    # Describe and verify original properties are returned
    jobs = batch_client.describe_jobs(jobs=[job_id])["jobs"]
    assert len(jobs) == 1

    job = jobs[0]
    assert "eksProperties" in job

    containers = job["eksProperties"]["podProperties"]["containers"]
    container = containers[0]

    assert container["command"] == ["sleep", "10"]
    assert container["image"] == "python:3.11"

    env_dict = {e["name"]: e["value"] for e in container["env"]}
    assert env_dict["MY_VAR"] == "my_value"


@mock_aws
def test_eks_job_definition_validation_missing_containers():
    """Test validation for EKS job definitions - missing containers."""
    _, _, _, _, batch_client = _get_clients()

    job_def_name = f"eks-job-{str(uuid4())[0:6]}"

    # Should fail without containers
    with pytest.raises(Exception) as exc:
        batch_client.register_job_definition(
            jobDefinitionName=job_def_name,
            type="container",
            eksProperties={"podProperties": {"containers": []}},
        )
    assert "must contain at least one container" in str(exc.value)


@mock_aws
def test_eks_job_definition_validation_missing_image():
    """Test validation for EKS job definitions - missing image.

    Note: boto3 client-side validation catches this before our mock,
    which is correct behavior. We just verify an exception is raised.
    """
    _, _, _, _, batch_client = _get_clients()

    job_def_name = f"eks-job-{str(uuid4())[0:6]}"

    # Should fail without image (caught by boto3 client-side validation)
    with pytest.raises(Exception) as exc:
        batch_client.register_job_definition(
            jobDefinitionName=job_def_name,
            type="container",
            eksProperties={
                "podProperties": {"containers": [{"command": ["sleep", "10"]}]}
            },
        )
    # Either our validation or boto3's validation catches the missing image
    assert "image" in str(exc.value).lower()


@mock_aws
def test_eks_job_definition_defaults():
    """Test that default values are set for EKS container properties."""
    _, _, _, _, batch_client = _get_clients()

    job_def_name = f"eks-job-{str(uuid4())[0:6]}"

    # Register with minimal properties
    batch_client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        eksProperties={
            "podProperties": {"containers": [{"image": "python:3.11"}]}
        },
    )

    # Describe and verify defaults are set
    job_defs = batch_client.describe_job_definitions(jobDefinitionName=job_def_name)[
        "jobDefinitions"
    ]

    container = job_defs[0]["eksProperties"]["podProperties"]["containers"][0]
    assert container["command"] == []  # Default empty command
    assert container["env"] == []  # Default empty env
