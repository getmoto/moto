"""EMRServerlessBackend class with methods for supported APIs."""

from datetime import datetime
from moto.core import BaseBackend, BaseModel, ACCOUNT_ID
from moto.core.utils import BackendDict, iso_8601_datetime_without_milliseconds
from moto.emrserverless.utils import (
    default_capacity_for_type,
    default_max_capacity,
    get_partition,
    random_appplication_id,
)

APPLICATION_ARN_TEMPLATE = (
    "arn:{partition}:emr-containers:{region}:"
    + str(ACCOUNT_ID)
    + ":/applications/{application_id}"
)


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
        self.state = "CREATING"
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


class EMRServerlessBackend(BaseBackend):
    """Implementation of EMRServerless APIs."""

    def __init__(self, region_name=None):
        super().__init__()
        self.region_name = region_name
        self.applications = dict()
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
        # implement here
        return [app.to_dict() for app in self.applications.values()], next_token
    

emrserverless_backends = BackendDict(EMRServerlessBackend, "emr-serverless")
