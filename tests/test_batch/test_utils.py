from unittest.mock import patch

import pytest

from moto.batch.exceptions import ValidationError
from moto.batch.models import Job
from moto.batch.utils import JobStatus


@pytest.mark.parametrize(
    "job_already_started, job_status",
    [
        (None, "InvalidJobStatus"),
        (False, "SUBMITTED"),
        (False, "PENDING"),
        (False, "RUNNABLE"),
        (False, "STARTING"),
        (True, "RUNNING"),
        (True, "SUCCEEDED"),
        (True, "FAILDED"),
    ],
)
def test_JobStatus_is_job_already_sarted(job_already_started, job_status):
    if job_status not in JobStatus.job_statuses():
        with pytest.raises(ValidationError) as e:
            _ = JobStatus.is_job_already_started("InvalidJobStatus")
        assert (
            e.value.message
            == "1 validation error detected: Value at 'current_status' failed to satisfy constraint: Member must satisfy enum value set: ['FAILED', 'PENDING', 'RUNNABLE', 'RUNNING', 'STARTING', 'SUBMITTED', 'SUCCEEDED']"
        )
        return

    assert JobStatus.is_job_already_started(job_status) is job_already_started


@pytest.mark.parametrize(
    "job_before_starting, job_status",
    [
        (None, "InvalidJobStatus"),
        (True, "SUBMITTED"),
        (True, "PENDING"),
        (True, "RUNNABLE"),
        (False, "STARTING"),
        (False, "RUNNING"),
        (False, "SUCCEEDED"),
        (False, "FAILDED"),
    ],
)
def test_JobStatus_is_job_before_starting(job_before_starting, job_status):
    if job_status not in JobStatus.job_statuses():
        with pytest.raises(ValidationError) as e:
            _ = JobStatus.is_job_before_starting("InvalidJobStatus")
        assert (
            e.value.message
            == "1 validation error detected: Value at 'current_status' failed to satisfy constraint: Member must satisfy enum value set: ['FAILED', 'PENDING', 'RUNNABLE', 'RUNNING', 'STARTING', 'SUBMITTED', 'SUCCEEDED']"
        )
        return

    assert JobStatus.is_job_before_starting(job_status) is job_before_starting


def test_JobStatus_status_transitions():
    for before_status, after_status in JobStatus.status_transitions():
        if before_status == JobStatus.SUBMITTED:
            assert after_status == JobStatus.PENDING
        elif before_status == JobStatus.PENDING:
            assert after_status == JobStatus.RUNNABLE
        elif before_status == JobStatus.RUNNABLE:
            assert after_status == JobStatus.STARTING
        else:
            assert before_status == JobStatus.STARTING
            assert after_status == JobStatus.RUNNING


@patch.object(Job, "__init__", lambda self, *args, **kwargs: None)
def test_add_parameters_to_command():
    _parameters = {"dossier_md5": "abc", "study_id": "T123BC00001"}
    _command = ["--dossier_md5", "Ref::dossier_md5", "--study_id", "Ref::study_id"]

    job = Job()  # noqa
    job.parameters = _parameters
    output = job._add_parameters_to_command(command=_command)
    assert output == ["--dossier_md5", "abc", "--study_id", "T123BC00001"]
