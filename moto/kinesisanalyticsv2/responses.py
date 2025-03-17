"""Handles incoming kinesisanalyticsv2 requests, invokes methods, returns responses."""

import json
from typing import Any, Dict, List, Optional

from moto.core.responses import BaseResponse

from .models import KinesisAnalyticsV2Backend, kinesisanalyticsv2_backends


class KinesisAnalyticsV2Response(BaseResponse):
    """Handler for KinesisAnalyticsV2 requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="kinesisanalyticsv2")

    @property
    def kinesisanalyticsv2_backend(self) -> KinesisAnalyticsV2Backend:
        """Return backend instance specific for this region."""
        return kinesisanalyticsv2_backends[self.current_account][self.region]

    def create_application(self):
        # params = self._get_params()
        # application_name = params.get("ApplicationName")
        # application_description = params.get("ApplicationDescription")
        # runtime_environment = params.get("RuntimeEnvironment")
        # service_execution_role = params.get("ServiceExecutionRole")
        # application_configuration = params.get("ApplicationConfiguration")
        # cloud_watch_logging_options = params.get("CloudWatchLoggingOptions")
        # tags = params.get("Tags")
        # application_mode = params.get("ApplicationMode")
        # application_detail = self.kinesisanalyticsv2_backend.create_application(
        #     application_name=application_name,
        #     application_description=application_description,
        #     runtime_environment=runtime_environment,
        #     service_execution_role=service_execution_role,
        #     application_configuration=application_configuration,
        #     cloud_watch_logging_options=cloud_watch_logging_options,
        #     tags=tags,
        #     application_mode=application_mode,
        # )

        application_name = self._get_param("ApplicationName")
        application_description = self._get_param("ApplicationDescription")
        runtime_environment = self._get_param("RuntimeEnvironment")
        service_execution_role = self._get_param("ServiceExecutionRole")
        application_configuration = self._get_param("ApplicationConfiguration")
        cloud_watch_logging_options = self._get_param("CloudWatchLoggingOptions")
        tags = self._get_param("Tags")
        application_mode = self._get_param("ApplicationMode")
        application_detail = self.kinesisanalyticsv2_backend.create_application(
            application_name=application_name,
            application_description=application_description,
            runtime_environment=runtime_environment,
            service_execution_role=service_execution_role,
            application_configuration=application_configuration,
            cloud_watch_logging_options=cloud_watch_logging_options,
            tags=tags,
            application_mode=application_mode,
        )
        return json.dumps(dict(ApplicationDetail=application_detail))

    def list_tags_for_resource(self) -> str:
        params = json.loads(self.body)
        resource_arn = params.get("ResourceARN")
        tags = self.kinesisanalyticsv2_backend.list_tags_for_resource(
            resource_arn=resource_arn,
        )
        # import pytest; pytest.set_trace()
        # update to capital Tags
        return json.dumps(dict(Tags=tags))


    def tag_resource(self) -> str:
        params = json.loads(self.body)
        resource_arn = params.get("ResourceARN")
        tags = params.get("Tags")
        self.kinesisanalyticsv2_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags
        )
        return json.dumps(dict())
