import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.client import ClientError
from unittest import SkipTest

from moto import mock_glue, settings
from moto.moto_api import state_manager
from .test_glue import create_test_job, create_glue_client


@mock_glue
def test_start_job_run():
    client = create_glue_client()
    job_name = create_test_job(client)
    response = client.start_job_run(JobName=job_name)
    assert response["JobRunId"]


@mock_glue
def test_start_job_run__multiple_runs_allowed():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set transition directly in ServerMode")

    state_manager.set_transition(
        model_name="glue::job_run", transition={"progression": "manual", "times": 2}
    )

    glue = create_glue_client()
    glue.create_job(
        Name="somejobname",
        Role="some-role",
        ExecutionProperty={"MaxConcurrentRuns": 5},
        Command={
            "Name": "some-name",
            "ScriptLocation": "some-location",
            "PythonVersion": "some-version",
        },
    )
    for _ in range(5):
        glue.start_job_run(JobName="somejobname")

    # The 6th should fail
    with pytest.raises(ClientError) as exc:
        glue.start_job_run(JobName="somejobname")
    exc.value.response["Error"]["Code"].should.equal("ConcurrentRunsExceededException")
    exc.value.response["Error"]["Message"].should.match(
        "Job with name somejobname already running"
    )


@mock_glue
def test_start_job_run__single_run_allowed():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set transition directly in ServerMode")

    state_manager.set_transition(
        model_name="glue::job_run", transition={"progression": "manual", "times": 2}
    )

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
    state_manager.unset_transition("glue::job_run")
    client = create_glue_client()
    job_name = create_test_job(client)
    job_run_id = client.start_job_run(JobName=job_name)["JobRunId"]

    response = client.get_job_run(JobName=job_name, RunId=job_run_id)
    response["JobRun"].should.have.key("Id").equals(job_run_id)
    assert response["JobRun"]["Attempt"]
    assert response["JobRun"]["PreviousRunId"]
    assert response["JobRun"]["TriggerName"]
    assert response["JobRun"]["StartedOn"]
    assert response["JobRun"]["LastModifiedOn"]
    assert response["JobRun"]["CompletedOn"]
    response["JobRun"].should.have.key("JobRunState").equals("SUCCEEDED")
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
def test_get_job_run_that_doesnt_exist():
    client = create_glue_client()
    job_name = create_test_job(client)
    with pytest.raises(ClientError) as exc:
        client.get_job_run(JobName=job_name, RunId="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("EntityNotFoundException")


@mock_glue
def test_job_run_transition():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set transition directly in ServerMode")

    state_manager.set_transition(
        model_name="glue::job_run", transition={"progression": "manual", "times": 2}
    )

    client = create_glue_client()
    job_name = create_test_job(client)
    # set transition
    run_id = client.start_job_run(JobName=job_name)["JobRunId"]

    # The job should change over time
    expect_job_state(client, job_name, run_id, expected_state="STARTING")
    expect_job_state(client, job_name, run_id, expected_state="RUNNING")
    expect_job_state(client, job_name, run_id, expected_state="RUNNING")
    # But finishes afterwards
    expect_job_state(client, job_name, run_id, expected_state="SUCCEEDED")

    # unset transition
    state_manager.unset_transition("glue::job_run")


def expect_job_state(client, job_name, run_id, expected_state):
    client.get_job_run(JobName=job_name, RunId=run_id)["JobRun"][
        "JobRunState"
    ].should.equal(expected_state)
