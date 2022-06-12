"""Handles incoming emrserverless requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import emrserverless_backends

DEFAULT_MAX_RESULTS = 100
DEFAULT_NEXT_TOKEN = ""

"""
These are the available methos:
    can_paginate()
    cancel_job_run()
    close()
    create_application() -> DONE
    delete_application() -> DONE
    get_application() -> DONE
    get_job_run()
    get_paginator()
    get_waiter()
    list_applications() -> DONE
    list_job_runs()
    list_tags_for_resource()
    start_application() -> DONE
    start_job_run()
    stop_application() -> DONE
    tag_resource()
    untag_resource()
    update_application()
"""


class EMRServerlessResponse(BaseResponse):
    """Handler for EMRServerless requests and responses."""

    SERVICE_NAME = "emr-serverless"

    @property
    def emrserverless_backend(self):
        """Return backend instance specific for this region."""
        return emrserverless_backends[self.region]

    def create_application(self):
        name = self._get_param("name")
        release_label = self._get_param("releaseLabel")
        type = self._get_param("type")
        client_token = self._get_param("clientToken")
        initial_capacity = self._get_param("initialCapacity")
        maximum_capacity = self._get_param("maximumCapacity")
        tags = self._get_param("tags")
        auto_start_configuration = self._get_param("autoStartConfig")
        auto_stop_configuration = self._get_param("autoStopConfig")
        network_configuration = self._get_param("networkConfiguration")

        application = self.emrserverless_backend.create_application(
            name=name,
            release_label=release_label,
            type=type,
            client_token=client_token,
            initial_capacity=initial_capacity,
            maximum_capacity=maximum_capacity,
            tags=tags,
            auto_start_configuration=auto_start_configuration,
            auto_stop_configuration=auto_stop_configuration,
            network_configuration=network_configuration,
        )
        return (200, {}, json.dumps(dict(application)))

    def delete_application(self):
        application_id = self._get_param("applicationId")

        self.emrserverless_backend.delete_application(application_id=application_id)
        return (200, {}, None)

    def get_application(self):
        application_id = self._get_param("applicationId")

        application = self.emrserverless_backend.get_application(
            application_id=application_id
        )
        response = {"application": application}
        return 200, {}, json.dumps(response)

    def list_applications(self):
        states = self.querystring.get("states", [])
        max_results = self._get_int_param("maxResults", DEFAULT_MAX_RESULTS)
        next_token = self._get_param("nextToken", DEFAULT_NEXT_TOKEN)

        applications, next_token = self.emrserverless_backend.list_applications(
            next_token=next_token,
            max_results=max_results,
            states=states,
        )
        response = {"applications": applications, "nextToken": next_token}
        return 200, {}, json.dumps(response)

    def start_application(self):
        application_id = self._get_param("applicationId")

        self.emrserverless_backend.start_application(application_id=application_id)
        return (200, {}, None)

    def stop_application(self):
        application_id = self._get_param("applicationId")

        self.emrserverless_backend.stop_application(application_id=application_id)
        return (200, {}, None)

    def update_application(self):
        name = self._get_param("applicationId")
        client_token = self._get_param("clientToken")
        initial_capacity = self._get_param("initialCapacity")
        maximum_capacity = self._get_param("maximumCapacity")
        auto_start_configuration = self._get_param("autoStartConfig")
        auto_stop_configuration = self._get_param("autoStopConfig")
        network_configuration = self._get_param("networkConfiguration")

        application = self.emrserverless_backend.update_application(
            name=name,
            client_token=client_token,
            initial_capacity=initial_capacity,
            maximum_capacity=maximum_capacity,
            auto_start_configuration=auto_start_configuration,
            auto_stop_configuration=auto_stop_configuration,
            network_configuration=network_configuration,
        )
        return (200, {}, json.dumps(dict(application)))

    def start_job_run(self):
        application_id = self._get_param("applicationId")
        job_driver = self._get_param("jobDriver")
        client_token = self._get_param("clientToken")
        configuration_overrides = self._get_param("configurationOverrides")
        execution_role_arn = self._get_param("executionRoleArn")
        tags = self._get_param("tags")

        app_id, job_id, arn = self.emrserverless_backend.start_job_run(
            application_id=application_id,
            client_token=client_token,
            configuration_overrides=configuration_overrides,
            execution_role_arn=execution_role_arn,
            job_driver=job_driver,
            tags=tags,
        )
        return 200, {}, json.dumps(dict(applicationId=app_id, arn=arn, jobRunId=job_id))

    def list_job_runs(self):
        params = self._get_params()
        next_token = self._get_param("nextToken", DEFAULT_NEXT_TOKEN)
        max_results = self._get_int_param("maxResults", DEFAULT_MAX_RESULTS)
        states = params.get("states")
        created_after = self._get_param("createdAfter")
        created_before = self._get_param("createdBefore")
        application_id = self._get_param("applicationId")

        jobs, next_token = self.emrserverless_backend.list_job_runs(
            application_id=application_id,
            created_after=created_after,
            created_before=created_before,
            next_token=next_token,
            max_results=max_results,
            states=states,
        )
        return 200, {}, json.dumps(dict(jobRuns=jobs, nextToken=next_token))

    def get_job_run(self):
        app_id = self._get_param("applicationId")
        job_id = self._get_param("jobRunId")

        job = self.emrserverless_backend.get_job_run(
            application_id=app_id, job_run_id=job_id
        )
        return 200, {}, json.dumps(dict(job=job))
