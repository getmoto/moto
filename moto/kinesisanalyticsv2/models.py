"""KinesisAnalyticsV2Backend class with methods for supported APIs."""

import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.moto_api._internal import mock_random

from moto.utilities.tagging_service import TaggingService


class Application(BaseModel):
    def __init__(
        self,
        account_id: str,
        region_name: str,
        application_name: str,
        application_description: Optional[str],
        runtime_environment: str,
        service_execution_role: str,
        # application_configuration: Optional[Dict[str, Any]],
        cloud_watch_logging_options: Optional[List[Dict[str, str]]],
        application_mode: Optional[str],
    ):
        self.account_id = account_id
        self.region_name = region_name
        self.application_name = application_name
        self.application_description = application_description
        self.runtime_environment = runtime_environment
        self.service_execution_role = service_execution_role
        self.application_mode = application_mode

        # TO-DO: Do a conditional for application_configuration
        # self.application_configuration = application_configuration
        self.cloud_watch_logging_options = self._generate_logging_options(
            cloud_watch_logging_options
        )
        # self.cloud_watch_logging_options = cloud_watch_logging_options

        self.application_arn = self._generate_arn()
        self.application_status = "STARTING"
        self.application_version_id = 1
        self.creation_date_time = datetime.now().isoformat()
        self.last_updated_date_time = datetime.now().isoformat()
        self.conditional_token = str(mock_random.uuid4()).replace("-", "")

    def _generate_arn(self) -> str:
        return f"arn:aws:kinesisanalytics:{self.region_name}:{self.account_id}:application/{self.application_name}"

    def _generate_logging_options(
        self, cloud_watch_logging_options
    ) -> List[Dict[str, str]]:
        cloud_watch_logging_option_descriptions = []
        option_id = f"{str(random.randint(1,100))}.1"

        # Leaving out RoleARN since it is provided only sometimes for backward
        # compatibility. Current API versions do not have the resource-level
        # role.
        if cloud_watch_logging_options:
            for i in cloud_watch_logging_options:
                cloud_watch_logging_option_descriptions.append(
                    {
                        "CloudWatchLoggingOptionId": option_id,
                        "LogStreamARN": i["LogStreamARN"],
                    }
                )
            return cloud_watch_logging_option_descriptions

    # def _generate_app_config_description(
    #     self, application_configuration
    # ) -> Dict[str, Any]:
    #     # Update keys in app_config


    # def to_dict(self) -> Dict[str, Any]:
    #     # Leave out:
    #     # ApplicationVersionUpdatedFrom
    #     # ApplicationVersionRolledBackFrom
    #     # ApplicationVersionRolledBackTo

    #     return {
    #         "ApplicationARN": self.application_arn,
    #         "ApplicationDescription": self.application_description,
    #         "RuntimeEnvironment": self.runtime_environment,
    #         "ServiceExecutionRole": self.service_execution_role,
    #         "ApplicationStatus": self.application_status,
    #         "ApplicationVersionId": self.application_version_id,
    #         "CreateTimestamp": self.creation_date_time,
    #         "LastUpdateTimestamp": self.last_updated_date_time,
    #         "ApplicationConfigurationDescription": self.application_configuration,
    #         "CloudWatchLoggingOptionDescriptions": self.cloud_watch_logging_options,
    #         "ApplicationMaintenanceConfigurationDescription": {
    #             "ApplicationMaintenanceWindowStartTime": "06:00",
    #             "ApplicationMaintenanceWindowEndTime": "14:00",
    #         },
    #         "ApplicationVersionCreateTimestamp": self.creation_date_time,
    #         "ConditionalToken": self.conditional_token,
    #         "ApplicationMode": self.application_mode,
    #     }


class KinesisAnalyticsV2Backend(BaseBackend):
    """Implementation of KinesisAnalyticsV2 APIs."""

    def __init__(self, region_name, account_id) -> None:
        super().__init__(region_name, account_id)
        self.application: Dict[str, Application] = {}
        self.tagger = TaggingService(
            tag_name="Tags", key_name="Key", value_name="Value"
        )

    def create_application(
        self,
        application_name: str,
        application_description: Optional[str],
        runtime_environment: str,  # This can be 'SQL-1_0'|'FLINK-1_6'|'FLINK-1_8'|'ZEPPELIN-FLINK-1_0'|'FLINK-1_11'|'FLINK-1_13'|'ZEPPELIN-FLINK-2_0'|'FLINK-1_15'|'ZEPPELIN-FLINK-3_0'|'FLINK-1_18'|'FLINK-1_19'|'FLINK-1_20'
        service_execution_role: str,
        application_configuration: Optional[Dict[str, Any]],
        cloud_watch_logging_options: Optional[List[Dict[str, str]]],  # LogStreamARN
        tags: Optional[List[Dict[str, str]]],
        application_mode: Optional[str],
    ) -> Dict[str, Any]:
        app = Application(
            account_id=self.account_id,
            region_name=self.region_name,
            application_name=application_name,
            application_description=application_description,
            runtime_environment=runtime_environment,
            service_execution_role=service_execution_role,
            # application_configuration=application_configuration,
            cloud_watch_logging_options=cloud_watch_logging_options,
            application_mode=application_mode
        )
        # take out tagging
        if tags:
            self.tag_resource(
                resource_arn=app.application_arn, tags=tags
            )
        # self.tag_resource(app.application_arn, tags)
        return {
            "ApplicationARN": app.application_arn,
            "ApplicationDescription": app.application_description,
            "RuntimeEnvironment": app.runtime_environment,
            "ServiceExecutionRole": app.service_execution_role,
            "ApplicationStatus": app.application_status,
            "ApplicationVersionId": app.application_version_id,
            "CreateTimestamp": app.creation_date_time,
            "LastUpdateTimestamp": app.last_updated_date_time,
            # "ApplicationConfigurationDescription": app.application_configuration,
            "CloudWatchLoggingOptionDescriptions": app.cloud_watch_logging_options,
            "ApplicationMaintenanceConfigurationDescription": {
                "ApplicationMaintenanceWindowStartTime": "06:00",
                "ApplicationMaintenanceWindowEndTime": "14:00",
            },
            "ApplicationVersionCreateTimestamp": str(app.creation_date_time),
            "ConditionalToken": app.conditional_token,
            "ApplicationMode": app.application_mode,
        }

    # def list_tags_for_resource(self, resource_arn: str,
    #     tags: List[Dict[str, str]]) -> None:
    #     self.tagger.tag_resource(resource_arn, tags)

    def tag_resource(self, resource_arn: str, tags: List[Dict[str, str]]) -> None:
        self.tagger.tag_resource(resource_arn, tags)

    def list_tags_for_resource(self, resource_arn: str) -> List[Dict[str, str]]:
        return self.tagger.list_tags_for_resource(resource_arn)["Tags"]


kinesisanalyticsv2_backends = BackendDict(
    KinesisAnalyticsV2Backend, "kinesisanalyticsv2"
)
