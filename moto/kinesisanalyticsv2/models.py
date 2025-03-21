"""KinesisAnalyticsV2Backend class with methods for supported APIs."""

import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.moto_api._internal import mock_random

from moto.utilities.tagging_service import TaggingService

FAKE_VPC_ID = "vpc-0123456789abcdef0"

class Application(BaseModel):
    def __init__(
        self,
        account_id: str,
        region_name: str,
        application_name: str,
        application_description: Optional[str],
        runtime_environment: str,
        service_execution_role: str,
        application_configuration: Optional[Dict[str, Any]],
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

        self.app_config_description = self._generate_app_config_description(
            application_configuration
        )
        self.cloud_watch_logging_description = self._generate_logging_options(
            cloud_watch_logging_options
        )

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

        # Leaving out RoleARN since it is provided only sometimes for backwards
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


    # Keys that do not have extra values in the description besides renamed keys
    UPDATABLE_APP_CONFIG_TOP_LEVEL_KEYS = {
        # "FlinkApplicationConfiguration": "FlinkApplicationConfigurationDescription",
        "EnvironmentProperties": "EnvironmentPropertyDescriptions",
        # "ApplicationCodeConfiguration": "ApplicationCodeConfigurationDescription",
        "ApplicationSnapshotConfiguration": "ApplicationSnapshotConfigurationDescription",
        "ApplicationSystemRollbackConfiguration": "ApplicationSystemRollbackConfigurationDescription",
        "ZeppelinApplicationConfiguration": "ZeppelinApplicationConfigurationDescription"
    }

    APP_CONFIG_SUBFIELD_KEYS = {
        # "ApplicationCodeConfiguration": "ApplicationCodeConfigurationDescription",
        # "S3ContentLocation": "S3ApplicationCodeLocationDescription",
        # "CodeContent": "CodeContentDescription",
        "PropertyGroups": "PropertyGroupDescriptions",
        "MonitoringConfiguration": "MonitoringConfigurationDescription",
        "CatalogConfiguration": "CatalogConfigurationDescription",
        "DeployAsApplicationConfiguration": "DeployAsApplicationConfigurationDescription",
        "S3ContentLocation": "S3ContentLocationDescription",
        "CustomArtifactsConfiguration": "CustomArtifactsConfigurationDescription",
        "GlueDataCatalogConfiguration": "GlueDataCatalogConfigurationDescription",
        "MavenReference": "MavenReferenceDescription"
    }

    def _generate_app_config_description(
        self, app_config
    ) -> Dict[str, Any]:
        if app_config:
            app_config_description = {}

            if "FlinkApplicationConfiguration" in app_config:
                app_config_description["FlinkApplicationConfigurationDescription"] = self.__generate_flink_app_description(
                app_config)

            # for config_key, config_value in app_config.items():
            #     if config_key in self.UPDATABLE_APP_CONFIG_TOP_LEVEL_KEYS:
            #         if config_key == "FlinkApplicationConfiguration":
            #             app_config_description[new_key] = self.__generate_flink_app_description(
            #     app_config)
            #         else:

            for old_key, new_key in self.UPDATABLE_APP_CONFIG_TOP_LEVEL_KEYS.items():
                if old_key in app_config:
                    app_config_description[new_key] = self.__update_keys(app_config[old_key], self.APP_CONFIG_SUBFIELD_KEYS)
            #     if old_key == "FlinkApplicationConfiguration" and old_key in app_config:
            #         app_config_description[new_key] = self.__generate_flink_app_description(
            #     app_config)


                # elif old_key in app_config:
                #     app_config_description[new_key] = self.__update_keys(app_config[old_key], self.APP_CONFIG_SUBFIELD_KEYS)


            if "ApplicationCodeConfiguration" in app_config:
                old_key = "ApplicationCodeConfiguration"
                new_key = "ApplicationCodeConfigurationDescription"
                # S3ContentLocation has a different output value here
                app_code_config_keys = {
                    "S3ContentLocation": "S3ApplicationCodeLocationDescription",
                    "CodeContent": "CodeContentDescription",
                }

                app_config_description[new_key] = self.__update_keys(
                    app_config["ApplicationCodeConfiguration"],
                    app_code_config_keys
                )

                if app_config[old_key]["CodeContentType"] == "ZIPFILE":
                    app_config_description[new_key]["CodeContentDescription"]["CodeMD5"] = "fakechecksum"
                    app_config_description[new_key]["CodeContentDescription"]["CodeSize"] = 123


            if "VpcConfigurations" in app_config:
                app_config_description["VpcConfigurationDescriptions"] = app_config["VpcConfigurations"]
                for index, vpc_config in enumerate(app_config_description["VpcConfigurationDescriptions"]):
                    vpc_config["VpcConfigurationId"] = f"{index+1}.1"
                    # FAKE_VPC_ID hardcoded, not a value from the parameters
                    vpc_config["VpcId"] = FAKE_VPC_ID

            # if "EnvironmentProperties" in app_config:
            #     app_config_description["EnvironmentPropertyDescriptions"] = self.__update_keys(app_config["EnvironmentProperties"], self.APP_CONFIG_ALT_FIELD_NAMES)
            #     # app_config_description["EnvironmentPropertyDescriptions"]["PropertyGroupDescriptions"] = app_config["EnvironmentProperties"].get("PropertyGroups")

            # if "ApplicationCodeConfiguration" in app_config:
            #     # Do I need to add CodeMDD5, CodeSize?
            #     app_config_description["ApplicationCodeConfigurationDescription"] = self.__update_keys(app_config["ApplicationCodeConfiguration"], self.APP_CONFIG_ALT_FIELD_NAMES)



            return app_config_description
        else:
            return None

    def __generate_flink_app_description(
            self, application_configuration) -> Dict[str, Any]:
        if "FlinkApplicationConfiguration" in application_configuration:
            flink_config_description = {}
            flink_config = application_configuration.get(
                "FlinkApplicationConfiguration")
            if "CheckpointConfiguration" in flink_config:
                checkpoint_config = flink_config["CheckpointConfiguration"]
                if checkpoint_config.get(
                    "ConfigurationType") == "DEFAULT":
                    flink_config_description["CheckpointConfigurationDescription"] = {
                        "ConfigurationType": "DEFAULT",
                        "CheckpointingEnabled": True,
                        "CheckpointInterval": 60000,
                        "MinPauseBetweenCheckpoints": 5000
                    }
                elif checkpoint_config.get(
                    "ConfigurationType") == "CUSTOM":
                    flink_config_description["CheckpointConfigurationDescription"] = {
                        "ConfigurationType": "CUSTOM",
                        "CheckpointingEnabled": checkpoint_config.get("CheckpointingEnabled", True),
                        "CheckpointInterval": checkpoint_config.get("CheckpointInterval", 60000),
                        "MinPauseBetweenCheckpoints": checkpoint_config.get("MinPauseBetweenCheckpoints", 5000)
                    }

            if "MonitoringConfiguration" in flink_config:
                monitoring_config = flink_config["MonitoringConfiguration"]
                if monitoring_config.get("ConfigurationType") == "DEFAULT":
                    flink_config_description["MonitoringConfigurationDescription"] = {
                        "ConfigurationType": "DEFAULT",
                        "MetricsLevel": "APPLICATION",
                        "LogLevel": "INFO"
                    }
                elif monitoring_config.get("ConfigurationType") == "CUSTOM":
                    flink_config_description["MonitoringConfigurationDescription"] = {
                        "ConfigurationType": "CUSTOM",
                        "MetricsLevel": monitoring_config.get("MetricsLevel", "APPLICATION"),
                        "LogLevel": monitoring_config.get("LogLevel", "INFO")
                    }

            if "ParallelismConfiguration" in flink_config:
                parallel_config = flink_config["ParallelismConfiguration"]
                if parallel_config.get("ConfigurationType") == "DEFAULT":
                    flink_config_description["ParallelismConfigurationDescription"] = {
                        "ConfigurationType": "DEFAULT",
                        "Parallelism": 1,
                        "ParallelismPerKPU": 1,
                        "AutoScalingEnabled": False,
                        "CurrentParallelism": 1
                    }
                elif parallel_config.get("ConfigurationType") == "CUSTOM":
                    flink_config_description["ParallelismConfigurationDescription"] = {
                        "ConfigurationType": "CUSTOM",
                        "Parallelism": parallel_config.get("Parallelism", 1),
                        "ParallelismPerKPU": parallel_config.get("ParallelismPerKPU", 1),
                        "AutoScalingEnabled": parallel_config.get("AutoScalingEnabled", False),
                        "CurrentParallelism": parallel_config.get("Parallelism", 1)
                    }
            return flink_config_description
        else:
            return None

    def __update_keys(self, old_dict, key_map) -> None:
        if not isinstance(old_dict, dict):
            return old_dict

        updated_dict = {}
        for old_key, value in old_dict.items():
            # Check if the current key is in key_map, else keep old_key
            new_key = key_map.get(old_key, old_key)

            if isinstance(value, dict):
                updated_dict[new_key] = self.__update_keys(value, key_map)
            elif isinstance(value, list):
                updated_dict[new_key] = [self.__update_keys(list_item, key_map) for list_item in value]
            else:
                updated_dict[new_key] = value
        return updated_dict

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
            application_configuration=application_configuration,
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
            "ApplicationConfigurationDescription": app.app_config_description,
            "CloudWatchLoggingOptionDescriptions": app.cloud_watch_logging_description,
            "ApplicationMaintenanceConfigurationDescription": {
                "ApplicationMaintenanceWindowStartTime": "06:00",
                "ApplicationMaintenanceWindowEndTime": "14:00",
            },
            "ApplicationVersionCreateTimestamp": str(app.creation_date_time),
            "ConditionalToken": app.conditional_token,
            "ApplicationMode": app.application_mode
        }

    def tag_resource(self, resource_arn: str, tags: List[Dict[str, str]]) -> None:
        self.tagger.tag_resource(resource_arn, tags)

    def list_tags_for_resource(self, resource_arn: str) -> List[Dict[str, str]]:
        return self.tagger.list_tags_for_resource(resource_arn)["Tags"]


kinesisanalyticsv2_backends = BackendDict(
    KinesisAnalyticsV2Backend, "kinesisanalyticsv2"
)
