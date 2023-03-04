"""EMRServerlessBackend class with methods for supported APIs."""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Iterator
import inspect

from moto.core import BaseBackend, BackendDict, BaseModel
from moto.core.utils import iso_8601_datetime_without_milliseconds
from moto.emrcontainers.utils import get_partition, paginated_list
from .utils import (
    default_auto_start_configuration,
    default_auto_stop_configuration,
    random_appplication_id,
)

from .exceptions import ResourceNotFoundException, ValidationException

APPLICATION_ARN_TEMPLATE = "arn:{partition}:emr-containers:{region}:{account_id}:/applications/{application_id}"

# Defaults used for creating an EMR Serverless application
APPLICATION_STATUS = "STARTED"
JOB_STATUS = "RUNNING"


class FakeApplication(BaseModel):
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
        tags: Dict[str, str],
        auto_start_configuration: str,
        auto_stop_configuration: str,
        network_configuration: str,
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
        self.tags: Dict[str, str] = tags or {}

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
        self.created_at = iso_8601_datetime_without_milliseconds(
            datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        )
        self.updated_at = self.created_at

    def __iter__(self) -> Iterator[Tuple[str, Any]]:
        yield "applicationId", self.id
        yield "name", self.name
        yield "arn", self.arn
        yield "autoStartConfig", self.auto_start_configuration,
        yield "autoStopConfig", self.auto_stop_configuration,

    def to_dict(self) -> Dict[str, Any]:
        """
        Dictionary representation of an EMR Serverless Application.
        When used in `list-applications`, capacity, auto-start/stop configs, and tags are not returned. https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_ListApplications.html
        When used in `get-application`, more details are returned. https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_GetApplication.html#API_GetApplication_ResponseSyntax
        """
        caller_methods = inspect.stack()[1].function
        caller_methods_type = caller_methods.split("_")[0]

        if caller_methods_type in ["get", "update"]:
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


class EMRServerlessBackend(BaseBackend):
    """Implementation of EMRServerless APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.region_name = region_name
        self.applications: Dict[str, FakeApplication] = dict()
        self.partition = get_partition(region_name)

    def create_application(
        self,
        name: str,
        release_label: str,
        application_type: str,
        client_token: str,
        initial_capacity: str,
        maximum_capacity: str,
        tags: Dict[str, str],
        auto_start_configuration: str,
        auto_stop_configuration: str,
        network_configuration: str,
    ) -> FakeApplication:

        if application_type not in ["HIVE", "SPARK"]:
            raise ValidationException(f"Unsupported engine {application_type}")

        if not re.match(r"emr-[0-9]{1}\.[0-9]{1,2}\.0(" "|-[0-9]{8})", release_label):
            raise ValidationException(
                f"Type '{application_type}' is not supported for release label '{release_label}' or release label does not exist"
            )

        application = FakeApplication(
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

    def get_application(self, application_id: str) -> Dict[str, Any]:
        if application_id not in self.applications.keys():
            raise ResourceNotFoundException(application_id)

        return self.applications[application_id].to_dict()

    def list_applications(
        self, next_token: Optional[str], max_results: int, states: Optional[List[str]]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
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
        network_configuration: Optional[str],
    ) -> Dict[str, Any]:
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

        self.applications[
            application_id
        ].updated_at = iso_8601_datetime_without_milliseconds(
            datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        )

        return self.applications[application_id].to_dict()


emrserverless_backends = BackendDict(EMRServerlessBackend, "emr-serverless")
