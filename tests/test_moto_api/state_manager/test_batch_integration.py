from tests.markers import requires_docker
from tests.test_batch import _get_clients, _setup
from tests.test_batch.test_batch_jobs import prepare_job, _wait_for_job_status

from moto import mock_batch, mock_iam, mock_ec2, mock_ecs, mock_logs, settings
from moto.moto_api import state_manager
from unittest import SkipTest


@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
@requires_docker
def test_cancel_pending_job():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't use state_manager in ServerMode directly")

    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, _, iam_arn = _setup(ec2_client, iam_client)

    # We need to be able to cancel a job that has not been started yet
    # Locally, our jobs start so fast that we can't cancel them in time
    # So artificially delay the status progression

    state_manager.set_transition(
        "batch::job", transition={"progression": "time", "seconds": 2}
    )

    commands = ["echo", "hello"]
    job_def_arn, queue_arn = prepare_job(batch_client, commands, iam_arn, "test")

    resp = batch_client.submit_job(
        jobName="test_job_name",
        jobQueue=queue_arn,
        jobDefinition=job_def_arn,
    )
    job_id = resp["jobId"]

    batch_client.cancel_job(jobId=job_id, reason="test_cancel")
    _wait_for_job_status(batch_client, job_id, "FAILED", seconds_to_wait=20)

    resp = batch_client.describe_jobs(jobs=[job_id])
    assert resp["jobs"][0]["jobName"] == "test_job_name"
    assert resp["jobs"][0]["statusReason"] == "test_cancel"


@mock_batch
def test_state_manager_should_return_registered_model():
    assert "batch::job" in state_manager.get_registered_models()
