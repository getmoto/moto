"""EMRServerlessBackend class with methods for supported APIs."""
import re
from datetime import datetime
import inspect

from moto.core import ACCOUNT_ID, BaseBackend, BaseModel
from moto.core.utils import BackendDict, iso_8601_datetime_without_milliseconds
from .utils import (
    default_auto_start_configuration,
    default_auto_stop_configuration,
    get_partition,
    paginated_list,
    random_appplication_id,
    random_job_id,
)

from .exceptions import ResourceNotFoundException, ValidationException

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
        initial_capacity,
        maximum_capacity,
        tags,
        auto_start_configuration,
        auto_stop_configuration,
        network_configuration,
    ):
        # Provided parameters
        self.name = name
        self.release_label = release_label
        self.application_type = application_type.capitalize()
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
        self.tags = tags or {}

        # Service-generated-parameters
        self.id = random_appplication_id()
        self.arn = APPLICATION_ARN_TEMPLATE.format(
            partition="aws", region=region_name, application_id=self.id
        )
        self.state = APPLICATION_STATUS
        self.state_details = ""
        self.created_at = iso_8601_datetime_without_milliseconds(
            datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        )
        self.updated_at = self.created_at

    def __iter__(self):
        yield "applicationId", self.id
        yield "name", self.name
        yield "arn", self.arn
        yield "autoStartConfig", self.auto_start_configuration,
        yield "autoStopConfig", self.auto_stop_configuration,

    def to_dict(self):
        """
        Dictionary representation of an EMR Serverless Application.
        When used in `list-applications`, capacity, auto-start/stop configs, and tags are not returned. https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_ListApplications.html
        When used in `get-application`, more details are returned. https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_GetApplication.html#API_GetApplication_ResponseSyntax
        """
        caller_methods = inspect.stack()[1].function
        caller_methods_type = caller_methods.split("_")[0]

        if caller_methods_type == "get":
            response = {
                "applicationId": self.id,
                "name": self.name,
                "arn": self.arn,
                "releaseLabel": self.release_label,
                "type": self.application_type,
                "state": self.state,
                "stateDetails": self.state_details,
                "createdAt": self.created_at,
                "updatedAt": self.updated_at,
                "autoStartConfiguration": self.auto_start_configuration,
                "autoStopConfiguration": self.auto_stop_configuration,
                "tags": self.tags,
            }
        else:
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

        if self.network_configuration:
            response.update({"networkConfiguration": self.network_configuration})
        if self.initial_capacity:
            response.update({"initialCapacity": self.initial_capacity})
        if self.maximum_capacity:
            response.update({"maximumCapacity": self.maximum_capacity})

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
        self.created_at = iso_8601_datetime_without_milliseconds(
            datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        )
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

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.region_name = region_name
        self.applications = dict()
        self.jobs = dict()
        self.partition = get_partition(region_name)

    def create_application(
        self,
        name,
        release_label,
        type,
        client_token,
        initial_capacity,
        maximum_capacity,
        tags,
        auto_start_configuration,
        auto_stop_configuration,
        network_configuration,
    ):

        if type not in ["HIVE", "SPARK"]:
            raise ValidationException(f"Unsupported engine {type}")

        if not re.match(r"emr-[0-9]{1}\.[0-9]{1,2}\.0(" "|-[0-9]{8})", release_label):
            raise ValidationException(
                f"Type '{type}' is not supported for release label '{release_label}' or release label does not exist"
            )

        application = FakeApplication(
            name=name,
            release_label=release_label,
            application_type=type,
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

    def delete_application(self, application_id):
        if application_id not in self.applications.keys():
            raise ResourceNotFoundException(application_id)

        if self.applications[application_id].state not in ["CREATED", "STOPPED"]:
            raise ValidationException(
                f"Application {application_id} must be in one of the following statuses [CREATED, STOPPED]. "
                f"Current status: {self.applications[application_id].state}"
            )
        self.applications[application_id].state = "TERMINATED"

    def get_application(self, application_id):
        if application_id not in self.applications.keys():
            raise ResourceNotFoundException(application_id)

        return self.applications[application_id].to_dict()

    def list_applications(self, next_token, max_results, states):
        applications = [
            application.to_dict() for application in self.applications.values()
        ]
        if states:
            applications = [
                application
                for application in applications
                if application["state"] in states
            ]
        sort_key = "name"
        return paginated_list(applications, sort_key, max_results, next_token)

    def start_application(self, application_id):
        if application_id not in self.applications.keys():
            raise ResourceNotFoundException(application_id)
        self.applications[application_id].state = "STARTED"

    def stop_application(self, application_id):
        if application_id not in self.applications.keys():
            raise ResourceNotFoundException(application_id)
        self.applications[application_id].state = "STOPPED"

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
            raise ResourceNotFoundException(application_id)

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

    def list_job_runs(
        self,
        application_id,
        created_after,
        created_before,
        states,
        max_results,
        next_token,
    ):
        application_jobs = [
            job for job in self.jobs.values() if job.application_id == application_id
        ]

        if created_after:
            application_jobs = [
                job for job in application_jobs if job.createdAt >= created_after
            ]

        if created_before:
            application_jobs = [
                job for job in application_jobs if job.createdAt >= created_before
            ]

        if states:
            application_jobs = [job for job in application_jobs if job.state in states]

        sort_key = "createdAt"
        jobs_list = [job.to_dict() for job in application_jobs]
        return paginated_list(jobs_list, sort_key, max_results, next_token)

    def get_job_run(self, application_id, job_run_id):
        job = self.jobs[job_run_id]
        return job.to_dict(include_details=True)

    def cancel_job_run(self, application_id, job_run_id):
        job = self.jobs[job_run_id]
        job.state = "CANCELLED"
        job.updated_at = iso_8601_datetime_without_milliseconds(datetime.today())
        job.state_details = "Cancelled"
        return job.to_dict(include_details=True)


emrserverless_backends = BackendDict(EMRServerlessBackend, "emr-serverless")
