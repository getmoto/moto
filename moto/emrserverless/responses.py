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

    def __init__(self):
        super().__init__("emr-serverless")

    @property
    def emrserverless_backend(self):
        """Return backend instance specific for this region."""
        return emrserverless_backends[self.current_account][self.region]

    def create_application(self):
        name = self._get_param("name")
        release_label = self._get_param("releaseLabel")
        application_type = self._get_param("type")
        client_token = self._get_param("clientToken")
        initial_capacity = self._get_param("initialCapacity")
        maximum_capacity = self._get_param("maximumCapacity")
        tags = self._get_param("tags")
        auto_start_configuration = self._get_param("autoStartConfiguration")
        auto_stop_configuration = self._get_param("autoStopConfiguration")
        network_configuration = self._get_param("networkConfiguration")

        application = self.emrserverless_backend.create_application(
            name=name,
            release_label=release_label,
            application_type=application_type,
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
        application_id = self._get_param("applicationId")
        initial_capacity = self._get_param("initialCapacity")
        maximum_capacity = self._get_param("maximumCapacity")
        auto_start_configuration = self._get_param("autoStartConfiguration")
        auto_stop_configuration = self._get_param("autoStopConfiguration")
        network_configuration = self._get_param("networkConfiguration")

        application = self.emrserverless_backend.update_application(
            application_id=application_id,
            initial_capacity=initial_capacity,
            maximum_capacity=maximum_capacity,
            auto_start_configuration=auto_start_configuration,
            auto_stop_configuration=auto_stop_configuration,
            network_configuration=network_configuration,
        )
        response = {"application": application}
        return 200, {}, json.dumps(response)
