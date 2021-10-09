from . import _get_clients, _setup
import random
import sure  # noqa
from moto import mock_batch, mock_iam, mock_ec2, mock_ecs
from uuid import uuid4


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
def test_register_task_definition_with_tags():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    _setup(ec2_client, iam_client)

    resp = register_job_def_with_tags(batch_client)

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

    job_def_name = str(uuid4())[0:6]
    resp1 = register_job_def(batch_client, definition_name=job_def_name)

    resp1.should.contain("jobDefinitionArn")
    resp1.should.have.key("jobDefinitionName").equals(job_def_name)
    resp1.should.contain("revision")

    assert resp1["jobDefinitionArn"].endswith(
        "{0}:{1}".format(resp1["jobDefinitionName"], resp1["revision"])
    )
    resp1["revision"].should.equal(1)

    resp2 = register_job_def(batch_client, definition_name=job_def_name)
    resp2["revision"].should.equal(2)

    resp2["jobDefinitionArn"].should_not.equal(resp1["jobDefinitionArn"])

    resp3 = register_job_def(batch_client, definition_name=job_def_name)
    resp3["revision"].should.equal(3)

    resp3["jobDefinitionArn"].should_not.equal(resp1["jobDefinitionArn"])
    resp3["jobDefinitionArn"].should_not.equal(resp2["jobDefinitionArn"])

    resp4 = register_job_def(batch_client, definition_name=job_def_name)
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

    resp = register_job_def(batch_client, definition_name=str(uuid4()))
    name = resp["jobDefinitionName"]

    batch_client.deregister_job_definition(jobDefinition=resp["jobDefinitionArn"])

    all_defs = batch_client.describe_job_definitions()["jobDefinitions"]
    [jobdef["jobDefinitionName"] for jobdef in all_defs].shouldnt.contain(name)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_delete_task_definition_by_name():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    _setup(ec2_client, iam_client)

    resp = register_job_def(batch_client, definition_name=str(uuid4()))
    name = resp["jobDefinitionName"]

    batch_client.deregister_job_definition(jobDefinition=f"{name}:{resp['revision']}")

    all_defs = batch_client.describe_job_definitions()["jobDefinitions"]
    [jobdef["jobDefinitionName"] for jobdef in all_defs].shouldnt.contain(name)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_describe_task_definition():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    _setup(ec2_client, iam_client)

    sleep_def_name = f"sleep10_{str(uuid4())[0:6]}"
    other_name = str(uuid4())[0:6]
    tagged_name = str(uuid4())[0:6]
    register_job_def(batch_client, definition_name=sleep_def_name)
    register_job_def(batch_client, definition_name=sleep_def_name)
    register_job_def(batch_client, definition_name=other_name)
    register_job_def_with_tags(batch_client, definition_name=tagged_name)

    resp = batch_client.describe_job_definitions(jobDefinitionName=sleep_def_name)
    len(resp["jobDefinitions"]).should.equal(2)

    job_defs = batch_client.describe_job_definitions()["jobDefinitions"]
    all_names = [jd["jobDefinitionName"] for jd in job_defs]
    all_names.should.contain(sleep_def_name)
    all_names.should.contain(other_name)
    all_names.should.contain(tagged_name)

    resp = batch_client.describe_job_definitions(
        jobDefinitions=[sleep_def_name, other_name]
    )
    len(resp["jobDefinitions"]).should.equal(3)
    resp["jobDefinitions"][0]["tags"].should.equal({})

    resp = batch_client.describe_job_definitions(jobDefinitionName=tagged_name)
    resp["jobDefinitions"][0]["tags"].should.equal(
        {"foo": "123", "bar": "456",}
    )

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


def register_job_def_with_tags(batch_client, definition_name="sleep10"):
    return batch_client.register_job_definition(
        jobDefinitionName=definition_name,
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": random.randint(4, 128),
            "command": ["sleep", "10"],
        },
        tags={"foo": "123", "bar": "456",},
    )
