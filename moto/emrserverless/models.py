"""EMRServerlessBackend class with methods for supported APIs."""

from datetime import datetime
from xml.etree.ElementInclude import include

from moto.core import ACCOUNT_ID, BaseBackend, BaseModel
from moto.core.utils import BackendDict, iso_8601_datetime_without_milliseconds
from moto.emrserverless.utils import (
    default_capacity_for_type,
    default_max_capacity,
    get_partition,
    random_appplication_id,
    random_job_id,
)

from .exceptions import ResourceNotFoundException

APPLICATION_ARN_TEMPLATE = (
    "arn:{partition}:emr-containers:{region}:"
    + str(ACCOUNT_ID)
    + ":/applications/{application_id}"
)

JOB_ARN_TEMPLATE = (
    "arn:{partition}:emr-containers:{region}:"
    + str(ACCOUNT_ID)
    + ":/applications/{application_id}/jobruns/{job_id}"
)

# Defaults used for creating an EMR Serverless application
APPLICATION_STATUS = "STARTED"
JOB_STATUS = "RUNNING"


class FakeApplication(BaseModel):
    def __init__(
        self,
        name,
        release_label,
        application_type,
        client_token,
        region_name,
        initial_capacity=None,
        maximum_capacity=None,
    ):
        # Provided parameters
        self.name = name
        self.release_label = release_label
        self.application_type = application_type
        self.client_token = client_token
        self.initial_capacity = initial_capacity or default_capacity_for_type(
            application_type
        )
        self.maximum_capacity = maximum_capacity or default_max_capacity()

        # Service-generated-parameters
        self.id = random_appplication_id()
        self.arn = APPLICATION_ARN_TEMPLATE.format(
            partition="aws", region=region_name, application_id=self.id
        )
        self.state = APPLICATION_STATUS
        self.state_details = ""
        self.created_at = iso_8601_datetime_without_milliseconds(datetime.today())
        self.updated_at = self.created_at
        self.auto_start_enabled = True
        self.auto_stop_enabled = True
        self.auto_stop_idle_timeout_mins = 15
        self.tags = {}

    def to_dict(self, include_details=False):
        """
        Dictionary representation of an EMR Serverless Application.
        When used in `list-applications`, capacity, auto-start/stop configs, and tags are not returned. https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_ListApplications.html
        When used in `get-application`, more details are returned. https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_GetApplication.html#API_GetApplication_ResponseSyntax
        """
        response = {
            "id": self.id,
            "name": self.name,
            "arn": self.arn,
            "releaseLabel": self.release_label,
            "type": self.application_type,
            "state": self.state,
            "stateDetails": self.state_details,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if include_details:
            response.update(
                {
                    "autoStartConfig": {"enabled": self.auto_start_enabled},
                    "autoStopConfig": {
                        "enabled": self.auto_stop_enabled,
                        "idleTimeout": self.auto_stop_idle_timeout_mins,
                    },
                    "tags": self.tags,
                    "initialCapacity": self.initial_capacity,
                    "maximumCapacity": self.maximum_capacity,
                }
            )

        return response


class FakeJob(BaseModel):
    def __init__(
        self,
        application_id,
        client_token,
        region_name,
        configuration_overrides,
        execution_role_arn,
        job_driver,
        tags,
    ):
        # Provided parameters
        self.application_id = application_id
        self.client_token = client_token
        self.configuration_overrides = configuration_overrides
        self.execution_role_arn = execution_role_arn
        self.job_driver = job_driver
        self.tags = tags

        # Service-generated-parameters
        self.id = random_job_id()
        self.arn = JOB_ARN_TEMPLATE.format(
            partition="aws",
            region=region_name,
            application_id=application_id,
            job_id=self.id,
        )
        self.state = JOB_STATUS
        self.state_details = ""
        self.created_at = iso_8601_datetime_without_milliseconds(datetime.today())
        self.updated_at = self.created_at

    def to_dict(self, include_details=False):
        """
        Dictionary representation of an EMR Serverless Application.
        """
        response = {
            "applicationId": self.application_id,
            "id": self.id,
            "arn": self.arn,
            "createdBy": "arn:aws:sts::568026268536:assumed-role/Admin/dcortesi-Isengard",
            "createdAt": self.created_at,
            "stateUpdatedAt": self.updated_at,
            "executionRole": self.execution_role_arn,
            "state": self.state,
            "stateDetails": self.state_details,
            # TODO: Figure out how to propagate releaseLabel
            "releaseLabel": "emr-6.5.0-preview",
            "type": "SPARK_SUBMIT",
        }
        if include_details:
            # In the detailed response, `id` is replaced with `jobRunId`
            response["jobRunId"] = response.pop("id")
            response.update(
                {
                    "configurationOverrides": self.configuration_overrides,
                    "jobDriver": self.job_driver,
                    "tags": self.tags,
                }
            )
        return response


class EMRServerlessBackend(BaseBackend):
    """Implementation of EMRServerless APIs."""

    def __init__(self, region_name=None):
        super().__init__()
        self.region_name = region_name
        self.applications = dict()
        self.jobs = dict()
        self.partition = get_partition(region_name)

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    # add methods from here

    def create_application(
        self,
        name,
        release_label,
        type,
        client_token,
        initial_capacity,
        maximum_capacity,
        tags,
        auto_start_config,
        auto_stop_config,
    ):
        application = FakeApplication(
            name=name,
            release_label=release_label,
            application_type=type,
            region_name=self.region_name,
            client_token=client_token,
            initial_capacity=initial_capacity,
            maximum_capacity=maximum_capacity,
        )
        self.applications[application.id] = application
        return application.id, application.name, application.arn

    def list_applications(self, next_token, max_results, states):
        return [app.to_dict() for app in self.applications.values()], next_token

    def get_application(self, application_id):
        return self.applications[application_id].to_dict(include_details=True)

    def start_job_run(
        self,
        application_id,
        client_token,
        configuration_overrides,
        execution_role_arn,
        job_driver,
        tags,
    ):
        if application_id not in self.applications.keys():
            raise ResourceNotFoundException(
                f"Application {application_id} does not exist"
            )

        job = FakeJob(
            application_id=application_id,
            client_token=client_token,
            execution_role_arn=execution_role_arn,
            job_driver=job_driver,
            configuration_overrides=configuration_overrides,
            tags=tags,
            region_name=self.region_name,
        )
        self.jobs[job.id] = job
        return job.application_id, job.id, job.arn

    def list_job_runs(self, application_id, next_token, max_results, states):
        application_jobs = [
            job for job in self.jobs.values() if job.application_id == application_id
        ]
        return [job.to_dict() for job in application_jobs], next_token

    def get_job_run(self, application_id, job_run_id):
        job = self.jobs[job_run_id]
        return job.to_dict(include_details=True)


emrserverless_backends = BackendDict(EMRServerlessBackend, "emr-serverless")
