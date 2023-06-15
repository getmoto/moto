from . import _get_clients
import random
import pytest
from moto import mock_batch
from uuid import uuid4


@mock_batch
@pytest.mark.parametrize("use_resource_reqs", [True, False])
def test_register_task_definition(use_resource_reqs):
    _, _, _, _, batch_client = _get_clients()

    resp = register_job_def(batch_client, use_resource_reqs=use_resource_reqs)

    assert "jobDefinitionArn" in resp
    assert "jobDefinitionName" in resp
    assert "revision" in resp

    assert f"{resp['jobDefinitionName']}:{resp['revision']}" in resp["jobDefinitionArn"]


@mock_batch
@pytest.mark.parametrize("propagate_tags", [None, True, False])
def test_register_task_definition_with_tags(propagate_tags):
    _, _, _, _, batch_client = _get_clients()

    job_def_name = str(uuid4())[0:8]
    register_job_def_with_tags(batch_client, job_def_name, propagate_tags)

    resp = batch_client.describe_job_definitions(jobDefinitionName=job_def_name)
    job_def = resp["jobDefinitions"][0]
    if propagate_tags is None:
        assert "propagateTags" not in job_def
    else:
        assert job_def["propagateTags"] == propagate_tags


@mock_batch
@pytest.mark.parametrize("platform_capability", ["EC2", "FARGATE"])
def test_register_task_definition_with_platform_capability(platform_capability):
    _, _, _, _, batch_client = _get_clients()

    def_name = str(uuid4())[0:6]
    batch_client.register_job_definition(
        jobDefinitionName=def_name,
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 4,
            "command": ["exit", "0"],
        },
        platformCapabilities=[platform_capability],
    )

    resp = batch_client.describe_job_definitions(jobDefinitionName=def_name)
    assert resp["jobDefinitions"][0]["platformCapabilities"] == [platform_capability]


@mock_batch
def test_register_task_definition_with_retry_strategies():
    _, _, _, _, batch_client = _get_clients()

    def_name = str(uuid4())[0:6]
    batch_client.register_job_definition(
        jobDefinitionName=def_name,
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 4,
            "command": ["exit", "0"],
        },
        retryStrategy={
            "attempts": 4,
            "evaluateOnExit": [
                {"onStatusReason": "osr", "action": "RETRY"},
                {"onStatusReason": "osr2", "action": "Exit"},
            ],
        },
    )

    resp = batch_client.describe_job_definitions(jobDefinitionName=def_name)
    assert resp["jobDefinitions"][0]["retryStrategy"] == {
        "attempts": 4,
        "evaluateOnExit": [
            {"onStatusReason": "osr", "action": "retry"},
            {"onStatusReason": "osr2", "action": "exit"},
        ],
    }


@mock_batch
@pytest.mark.parametrize("use_resource_reqs", [True, False])
def test_reregister_task_definition(use_resource_reqs):
    # Reregistering task with the same name bumps the revision number
    _, _, _, _, batch_client = _get_clients()

    job_def_name = str(uuid4())[0:6]
    resp1 = register_job_def(
        batch_client, definition_name=job_def_name, use_resource_reqs=use_resource_reqs
    )

    assert "jobDefinitionArn" in resp1
    assert resp1["jobDefinitionName"] == job_def_name
    assert "revision" in resp1

    assert resp1["jobDefinitionArn"].endswith(
        f"{resp1['jobDefinitionName']}:{resp1['revision']}"
    )
    assert resp1["revision"] == 1

    resp2 = register_job_def(
        batch_client, definition_name=job_def_name, use_resource_reqs=use_resource_reqs
    )
    assert resp2["revision"] == 2

    assert resp2["jobDefinitionArn"] != resp1["jobDefinitionArn"]

    resp3 = register_job_def(
        batch_client, definition_name=job_def_name, use_resource_reqs=use_resource_reqs
    )
    assert resp3["revision"] == 3

    assert resp3["jobDefinitionArn"] != resp1["jobDefinitionArn"]
    assert resp3["jobDefinitionArn"] != resp2["jobDefinitionArn"]

    resp4 = register_job_def(
        batch_client, definition_name=job_def_name, use_resource_reqs=use_resource_reqs
    )
    assert resp4["revision"] == 4

    assert resp4["jobDefinitionArn"] != resp1["jobDefinitionArn"]
    assert resp4["jobDefinitionArn"] != resp2["jobDefinitionArn"]
    assert resp4["jobDefinitionArn"] != resp3["jobDefinitionArn"]


@mock_batch
def test_reregister_task_definition_should_not_reuse_parameters_from_inactive_definition():
    # Reregistering task with the same name bumps the revision number
    _, _, _, _, batch_client = _get_clients()

    job_def_name = str(uuid4())[0:6]
    # Register job definition with parameters
    resp = batch_client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 48,
            "command": ["sleep", "0"],
        },
        parameters={"param1": "val1"},
    )
    job_def_arn = resp["jobDefinitionArn"]

    definitions = batch_client.describe_job_definitions(jobDefinitionName=job_def_name)[
        "jobDefinitions"
    ]
    assert len(definitions) == 1

    assert definitions[0]["parameters"] == {"param1": "val1"}

    # Deactivate the definition
    batch_client.deregister_job_definition(jobDefinition=job_def_arn)

    # Second job definition does not provide any parameters
    batch_client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": 96,
            "command": ["sleep", "0"],
        },
    )

    definitions = batch_client.describe_job_definitions(jobDefinitionName=job_def_name)[
        "jobDefinitions"
    ]
    assert len(definitions) == 2

    # Only the inactive definition should have the parameters
    actual = [(d["revision"], d["status"], d.get("parameters")) for d in definitions]
    assert (1, "INACTIVE", {"param1": "val1"}) in actual
    assert (2, "ACTIVE", {}) in actual


@mock_batch
@pytest.mark.parametrize("use_resource_reqs", [True, False])
def test_delete_task_definition(use_resource_reqs):
    _, _, _, _, batch_client = _get_clients()

    resp = register_job_def(
        batch_client, definition_name=str(uuid4()), use_resource_reqs=use_resource_reqs
    )
    name = resp["jobDefinitionName"]

    batch_client.deregister_job_definition(jobDefinition=resp["jobDefinitionArn"])

    all_defs = batch_client.describe_job_definitions()["jobDefinitions"]
    assert name in [jobdef["jobDefinitionName"] for jobdef in all_defs]

    definitions = batch_client.describe_job_definitions(jobDefinitionName=name)[
        "jobDefinitions"
    ]
    assert len(definitions) == 1

    assert definitions[0]["revision"] == 1
    assert definitions[0]["status"] == "INACTIVE"


@mock_batch
@pytest.mark.parametrize("use_resource_reqs", [True, False])
def test_delete_task_definition_by_name(use_resource_reqs):
    _, _, _, _, batch_client = _get_clients()

    resp = register_job_def(
        batch_client, definition_name=str(uuid4()), use_resource_reqs=use_resource_reqs
    )
    name = resp["jobDefinitionName"]

    batch_client.deregister_job_definition(jobDefinition=f"{name}:{resp['revision']}")

    all_defs = batch_client.describe_job_definitions()["jobDefinitions"]
    # We should still see our job definition as INACTIVE, as it is kept for 180 days
    assert name in [jobdef["jobDefinitionName"] for jobdef in all_defs]

    # Registering the job definition again should up the revision number
    register_job_def(
        batch_client, definition_name=name, use_resource_reqs=use_resource_reqs
    )

    definitions = batch_client.describe_job_definitions(jobDefinitionName=name)[
        "jobDefinitions"
    ]
    assert len(definitions) == 2

    revision_status = [
        {"revision": d["revision"], "status": d["status"]} for d in definitions
    ]

    assert {"revision": 1, "status": "INACTIVE"} in revision_status
    assert {"revision": 2, "status": "ACTIVE"} in revision_status


@mock_batch
@pytest.mark.parametrize("use_resource_reqs", [True, False])
def test_describe_task_definition(use_resource_reqs):
    _, _, _, _, batch_client = _get_clients()

    sleep_def_name = f"sleep10_{str(uuid4())[0:6]}"
    other_name = str(uuid4())[0:6]
    tagged_name = str(uuid4())[0:6]
    register_job_def(
        batch_client,
        definition_name=sleep_def_name,
        use_resource_reqs=use_resource_reqs,
    )
    register_job_def(
        batch_client,
        definition_name=sleep_def_name,
        use_resource_reqs=use_resource_reqs,
    )
    register_job_def(
        batch_client, definition_name=other_name, use_resource_reqs=use_resource_reqs
    )
    register_job_def_with_tags(batch_client, definition_name=tagged_name)

    resp = batch_client.describe_job_definitions(jobDefinitionName=sleep_def_name)
    assert len(resp["jobDefinitions"]) == 2

    job_defs = batch_client.describe_job_definitions()["jobDefinitions"]
    all_names = [jd["jobDefinitionName"] for jd in job_defs]
    assert sleep_def_name in all_names
    assert other_name in all_names
    assert tagged_name in all_names

    resp = batch_client.describe_job_definitions(
        jobDefinitions=[sleep_def_name, other_name]
    )
    assert len(resp["jobDefinitions"]) == 3
    assert resp["jobDefinitions"][0]["tags"] == {}

    resp = batch_client.describe_job_definitions(jobDefinitionName=tagged_name)
    assert resp["jobDefinitions"][0]["tags"] == {"foo": "123", "bar": "456"}

    for job_definition in resp["jobDefinitions"]:
        assert job_definition["status"] == "ACTIVE"
        assert "platformCapabilities" not in job_definition
        assert "retryStrategy" not in job_definition


def register_job_def(batch_client, definition_name="sleep10", use_resource_reqs=True):
    container_properties = {"image": "busybox", "command": ["sleep", "10"]}

    if use_resource_reqs:
        container_properties.update(
            {
                "resourceRequirements": [
                    {"value": "0.25", "type": "VCPU"},
                    {"value": "512", "type": "MEMORY"},
                ]
            }
        )
    else:
        container_properties.update({"memory": 128, "vcpus": 1})

    return batch_client.register_job_definition(
        jobDefinitionName=definition_name,
        type="container",
        containerProperties=container_properties,
    )


def register_job_def_with_tags(
    batch_client, definition_name="sleep10", propagate_tags=False
):
    kwargs = {} if propagate_tags is None else {"propagateTags": propagate_tags}
    return batch_client.register_job_definition(
        jobDefinitionName=definition_name,
        type="container",
        containerProperties={
            "image": "busybox",
            "vcpus": 1,
            "memory": random.randint(4, 128),
            "command": ["sleep", "10"],
        },
        tags={"foo": "123", "bar": "456"},
        **kwargs,
    )
