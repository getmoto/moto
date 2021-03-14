from . import _get_clients, _setup
import random
import sure  # noqa
from moto import mock_batch, mock_iam, mock_ec2, mock_ecs


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_register_task_definition():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    _setup(ec2_client, iam_client)

    resp = register_job_def(batch_client)

    resp.should.contain("jobDefinitionArn")
    resp.should.contain("jobDefinitionName")
    resp.should.contain("revision")

    assert resp["jobDefinitionArn"].endswith(
        "{0}:{1}".format(resp["jobDefinitionName"], resp["revision"])
    )


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_reregister_task_definition():
    # Reregistering task with the same name bumps the revision number
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    _setup(ec2_client, iam_client)

    resp1 = register_job_def(batch_client)

    resp1.should.contain("jobDefinitionArn")
    resp1.should.contain("jobDefinitionName")
    resp1.should.contain("revision")

    assert resp1["jobDefinitionArn"].endswith(
        "{0}:{1}".format(resp1["jobDefinitionName"], resp1["revision"])
    )
    resp1["revision"].should.equal(1)

    resp2 = register_job_def(batch_client)
    resp2["revision"].should.equal(2)

    resp2["jobDefinitionArn"].should_not.equal(resp1["jobDefinitionArn"])

    resp3 = register_job_def(batch_client)
    resp3["revision"].should.equal(3)

    resp3["jobDefinitionArn"].should_not.equal(resp1["jobDefinitionArn"])
    resp3["jobDefinitionArn"].should_not.equal(resp2["jobDefinitionArn"])

    resp4 = register_job_def(batch_client)
    resp4["revision"].should.equal(4)

    resp4["jobDefinitionArn"].should_not.equal(resp1["jobDefinitionArn"])
    resp4["jobDefinitionArn"].should_not.equal(resp2["jobDefinitionArn"])
    resp4["jobDefinitionArn"].should_not.equal(resp3["jobDefinitionArn"])


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_delete_task_definition():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    _setup(ec2_client, iam_client)

    resp = register_job_def(batch_client)

    batch_client.deregister_job_definition(jobDefinition=resp["jobDefinitionArn"])

    resp = batch_client.describe_job_definitions()
    len(resp["jobDefinitions"]).should.equal(0)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_describe_task_definition():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    _setup(ec2_client, iam_client)

    register_job_def(batch_client, definition_name="sleep10")
    register_job_def(batch_client, definition_name="sleep10")
    register_job_def(batch_client, definition_name="test1")

    resp = batch_client.describe_job_definitions(jobDefinitionName="sleep10")
    len(resp["jobDefinitions"]).should.equal(2)

    resp = batch_client.describe_job_definitions()
    len(resp["jobDefinitions"]).should.equal(3)

    resp = batch_client.describe_job_definitions(jobDefinitions=["sleep10", "test1"])
    len(resp["jobDefinitions"]).should.equal(3)

    for job_definition in resp["jobDefinitions"]:
        job_definition["status"].should.equal("ACTIVE")


def register_job_def(batch_client, definition_name="sleep10"):
    return batch_client.register_job_definition(
        jobDefinitionName=definition_name,
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": random.randint(4, 128),
            "command": ["sleep", "10"],
        },
    )
