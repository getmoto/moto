from uuid import uuid4

import botocore.exceptions
import pytest

from moto import mock_aws

from . import _get_clients, _setup


@mock_aws
def test_submit_job_with_tags():
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    resp = batch_client.create_compute_environment(
        computeEnvironmentName=str(uuid4()),
        type="UNMANAGED",
        state="ENABLED",
        serviceRole=iam_arn,
    )
    arn = resp["computeEnvironmentArn"]

    resp = batch_client.create_job_queue(
        jobQueueName=str(uuid4()),
        state="ENABLED",
        priority=123,
        computeEnvironmentOrder=[{"order": 123, "computeEnvironment": arn}],
    )
    queue_arn = resp["jobQueueArn"]

    job_definition_name = f"sleep_{str(uuid4())[0:6]}"

    resp = batch_client.register_job_definition(
        jobDefinitionName=job_definition_name,
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 512,
            "command": ["sleep", "10"],
        },
    )
    job_definition_arn = resp["jobDefinitionArn"]

    # Submit a job with more than 50 tags - we expect a failure
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        batch_client.submit_job(
            jobName="test1",
            jobQueue=queue_arn,
            jobDefinition=job_definition_name,
            tags={f"tag{i}": f"value{i}" for i in range(51)},
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert "Member must have length less than or equal to 50" in err["Message"]

    # Submit a job with 2 tags. It is a valid scenario and should be returned as part
    # of DescribeJobs response
    resp = batch_client.submit_job(
        jobName="test2",
        jobQueue=queue_arn,
        jobDefinition=job_definition_name,
        tags={"tag1": "value1", "tag2": "value2"},
    )

    job_id = resp["jobId"]
    job_arn = resp["jobArn"]
    resp_jobs = batch_client.describe_jobs(jobs=[job_id])
    assert len(resp_jobs["jobs"]) == 1
    assert resp_jobs["jobs"][0]["jobId"] == job_id
    assert resp_jobs["jobs"][0]["jobQueue"] == queue_arn
    assert resp_jobs["jobs"][0]["jobDefinition"] == job_definition_arn
    assert resp_jobs["jobs"][0]["tags"] == {
        "tag1": "value1",
        "tag2": "value2",
    }

    # Also available via ListTagsForResource
    resp_tags = batch_client.list_tags_for_resource(resourceArn=job_arn)
    assert resp_tags["tags"] == {
        "tag1": "value1",
        "tag2": "value2",
    }

    # Tag and untag the job directly
    batch_client.tag_resource(resourceArn=job_arn, tags={"tag3": "value3"})
    batch_client.untag_resource(resourceArn=job_arn, tagKeys=["tag2"])
    resp_tags = batch_client.list_tags_for_resource(resourceArn=job_arn)
    assert resp_tags["tags"] == {
        "tag1": "value1",
        "tag3": "value3",
    }
