"""EMRServerlessBackend class with methods for supported APIs."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional, Union

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.utils import utcnow
from moto.utilities.utils import get_partition

from .exceptions import (
    AccessDeniedException,
    ResourceNotFoundException,
    ValidationException,
)
from .utils import (
    default_auto_start_configuration,
    default_auto_stop_configuration,
    random_appplication_id,
    random_job_id,
)

APPLICATION_ARN_TEMPLATE = "arn:{partition}:emr-serverless:{region}:{account_id}:/applications/{application_id}"
JOB_RUN_ARN_TEMPLATE = "arn:{partition}:emr-serverless:{region}:{account_id}:/applications/{application_id}/jobruns/{job_run_id}"

# Defaults used for creating an EMR Serverless application
APPLICATION_STATUS = "STARTED"
JOB_STATUS = "SUCCESS"


class Application(BaseModel):
    def __init__(
        self,
        name: str,
        release_label: str,
        application_type: str,
        client_token: str,
        account_id: str,
        region_name: str,
        initial_capacity: str,
        maximum_capacity: str,
        tags: dict[str, str],
        auto_start_configuration: str,
        auto_stop_configuration: str,
        network_configuration: Optional[dict[str, Any]],
    ):
        # Provided parameters
        self.name = name
        self.release_label = release_label
        self.type = application_type.capitalize()
        self.client_token = client_token
        self.initial_capacity = initial_capacity
        self.maximum_capacity = maximum_capacity
        self.auto_start_configuration = (
            auto_start_configuration or default_auto_start_configuration()
        )
        self.auto_stop_configuration = (
            auto_stop_configuration or default_auto_stop_configuration()
        )
        self.network_configuration = network_configuration
        self.tags: dict[str, str] = tags or {}

        # Service-generated-parameters
        self.id = random_appplication_id()
        self.arn = APPLICATION_ARN_TEMPLATE.format(
            partition="aws",
            region=region_name,
            account_id=account_id,
            application_id=self.id,
        )
        self.state = APPLICATION_STATUS
        self.state_details = ""
        self.created_at = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        self.updated_at = self.created_at


class JobRun(BaseModel):
    def __init__(
        self,
        application_id: str,
        client_token: str,
        execution_role_arn: str,
        account_id: str,
        region_name: str,
        release_label: str,
        application_type: str,
        job_driver: Optional[dict[str, dict[str, Union[str, list[str]]]]],
        configuration_overrides: Optional[dict[str, Union[list[Any], dict[str, Any]]]],
        tags: Optional[dict[str, str]],
        network_configuration: Optional[dict[str, list[str]]],
        execution_timeout_minutes: Optional[int],
        name: Optional[str],
    ):
        self.name = name
        self.application_id = application_id
        self.client_token = client_token
        self.execution_role_arn = execution_role_arn
        self.job_driver = job_driver
        self.configuration_overrides = configuration_overrides
        self.network_configuration = network_configuration
        self.execution_timeout_minutes = execution_timeout_minutes or 720

        # Service-generated-parameters
        self.id = random_job_id()

        self.arn = JOB_RUN_ARN_TEMPLATE.format(
            partition="aws",
            account_id=account_id,
            application_id=self.application_id,
            region=region_name,
            job_run_id=self.id,
        )

        self.release_label = release_label
        self.application_type = application_type

        self.state = JOB_STATUS
        self.state_details: Optional[str] = None

        self.created_by: Optional[str] = None

        self.created_at = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        self.updated_at = self.created_at

        self.total_execution_duration_seconds: int = 0
        self.billed_resource_utilization: dict[str, float] = {
            "vCPUHour": 0.0,
            "memoryGBHour": 0.0,
            "storageGBHour": 0.0,
        }

        self.tags = tags


class EMRServerlessBackend(BaseBackend):
    """Implementation of EMRServerless APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.region_name = region_name
        self.partition = get_partition(region_name)
        self.applications: dict[str, Application] = {}
        self.job_runs: dict[
            str, list[JobRun]
        ] = {}  # {application_id: [job_run1, job_run2]}

    def create_application(
        self,
        name: str,
        release_label: str,
        application_type: str,
        client_token: str,
        initial_capacity: str,
        maximum_capacity: str,
        tags: dict[str, str],
        auto_start_configuration: str,
        auto_stop_configuration: str,
        network_configuration: Optional[dict[str, Any]],
    ) -> Application:
        if application_type not in ["HIVE", "SPARK"]:
            raise ValidationException(f"Unsupported engine {application_type}")

        if not re.match(r"emr-[0-9]{1}\.[0-9]{1,2}\.0(" "|-[0-9]{8})", release_label):
            raise ValidationException(
                f"Type '{application_type}' is not supported for release label '{release_label}' or release label does not exist"
            )

        application = Application(
            name=name,
            release_label=release_label,
            application_type=application_type,
            account_id=self.account_id,
            region_name=self.region_name,
            client_token=client_token,
            initial_capacity=initial_capacity,
            maximum_capacity=maximum_capacity,
            tags=tags,
            auto_start_configuration=auto_start_configuration,
            auto_stop_configuration=auto_stop_configuration,
            network_configuration=network_configuration,
        )
        self.applications[application.id] = application
        return application

    def delete_application(self, application_id: str) -> None:
        if application_id not in self.applications.keys():
            raise ResourceNotFoundException(application_id)

        if self.applications[application_id].state not in ["CREATED", "STOPPED"]:
            raise ValidationException(
                f"Application {application_id} must be in one of the following statuses [CREATED, STOPPED]. "
                f"Current status: {self.applications[application_id].state}"
            )
        self.applications[application_id].state = "TERMINATED"

    def get_application(self, application_id: str) -> Application:
        if application_id not in self.applications.keys():
            raise ResourceNotFoundException(application_id)

        return self.applications[application_id]

    def list_applications(self, states: Optional[list[str]]) -> list[Application]:
        applications = list(self.applications.values())
        if states:
            applications = [
                application
                for application in applications
                if application.state in states
            ]
        return applications

    def start_application(self, application_id: str) -> None:
        if application_id not in self.applications.keys():
            raise ResourceNotFoundException(application_id)
        self.applications[application_id].state = "STARTED"

    def stop_application(self, application_id: str) -> None:
        if application_id not in self.applications.keys():
            raise ResourceNotFoundException(application_id)
        self.applications[application_id].state = "STOPPED"

    def update_application(
        self,
        application_id: str,
        initial_capacity: Optional[str],
        maximum_capacity: Optional[str],
        auto_start_configuration: Optional[str],
        auto_stop_configuration: Optional[str],
        network_configuration: Optional[dict[str, Any]],
    ) -> Application:
        if application_id not in self.applications.keys():
            raise ResourceNotFoundException(application_id)

        if self.applications[application_id].state not in ["CREATED", "STOPPED"]:
            raise ValidationException(
                f"Application {application_id} must be in one of the following statuses [CREATED, STOPPED]. "
                f"Current status: {self.applications[application_id].state}"
            )

        if initial_capacity:
            self.applications[application_id].initial_capacity = initial_capacity

        if maximum_capacity:
            self.applications[application_id].maximum_capacity = maximum_capacity

        if auto_start_configuration:
            self.applications[
                application_id
            ].auto_start_configuration = auto_start_configuration

        if auto_stop_configuration:
            self.applications[
                application_id
            ].auto_stop_configuration = auto_stop_configuration

        if network_configuration:
            self.applications[
                application_id
            ].network_configuration = network_configuration

        self.applications[application_id].updated_at = utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        return self.applications[application_id]

    def start_job_run(
        self,
        application_id: str,
        client_token: str,
        execution_role_arn: str,
        job_driver: Optional[dict[str, dict[str, Union[str, list[str]]]]],
        configuration_overrides: Optional[dict[str, Union[list[Any], dict[str, Any]]]],
        tags: Optional[dict[str, str]],
        execution_timeout_minutes: Optional[int],
        name: Optional[str],
    ) -> JobRun:
        role_account_id = execution_role_arn.split(":")[4]
        if role_account_id != self.account_id:
            raise AccessDeniedException("Cross-account pass role is not allowed.")

        if execution_timeout_minutes and execution_timeout_minutes < 5:
            raise ValidationException("RunTimeout must be at least 5 minutes.")

        application = self.get_application(application_id)
        job_run = JobRun(
            application_id=application_id,
            client_token=client_token,
            execution_role_arn=execution_role_arn,
            account_id=self.account_id,
            region_name=self.region_name,
            release_label=application.release_label,
            application_type=application.type,
            job_driver=job_driver,
            configuration_overrides=configuration_overrides,
            tags=tags,
            network_configuration=application.network_configuration,
            execution_timeout_minutes=execution_timeout_minutes,
            name=name,
        )

        if application.state == "TERMINATED":
            raise ValidationException(
                f"Application {application_id} is terminated. Cannot start job run."
            )

        if application_id not in self.job_runs:
            self.job_runs[application_id] = []
        self.job_runs[application_id].append(job_run)

        return job_run

    def get_job_run(self, application_id: str, job_run_id: str) -> JobRun:
        if application_id not in self.job_runs.keys():
            raise ResourceNotFoundException(application_id, "Application")
        job_run_ids = [job_run.id for job_run in self.job_runs[application_id]]
        if job_run_id not in job_run_ids:
            raise ResourceNotFoundException(job_run_id, "JobRun")

        filtered_job_runs = [
            job_run
            for job_run in self.job_runs[application_id]
            if job_run.id == job_run_id
        ]
        assert len(filtered_job_runs) == 1
        job_run: JobRun = filtered_job_runs[0]

        return job_run

    def cancel_job_run(self, application_id: str, job_run_id: str) -> tuple[str, str]:
        # implement here
        if application_id not in self.job_runs.keys():
            raise ResourceNotFoundException(application_id, "Application")
        job_run_ids = [job_run.id for job_run in self.job_runs[application_id]]
        if job_run_id not in job_run_ids:
            raise ResourceNotFoundException(job_run_id, "JobRun")

        self.job_runs[application_id][job_run_ids.index(job_run_id)].state = "CANCELLED"

        return application_id, job_run_id

    def list_job_runs(
        self,
        application_id: str,
        created_at_after: Optional[datetime],
        created_at_before: Optional[datetime],
        states: Optional[list[str]],
    ) -> list[JobRun]:
        if application_id not in self.job_runs.keys():
            raise ResourceNotFoundException(application_id, "Application")
        job_runs = self.job_runs[application_id]
        if states:
            job_runs = [job_run for job_run in job_runs if job_run.state in states]
        if created_at_after:
            job_runs = [
                job_run for job_run in job_runs if job_run.created_at > created_at_after
            ]
        if created_at_before:
            job_runs = [
                job_run
                for job_run in job_runs
                if job_run.created_at < created_at_before
            ]

        return job_runs


emrserverless_backends = BackendDict(EMRServerlessBackend, "emr-serverless")
