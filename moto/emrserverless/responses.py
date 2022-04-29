"""Handles incoming emrserverless requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import emrserverless_backends


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
        auto_start_config = self._get_param("autoStartConfig")
        auto_stop_config = self._get_param("autoStopConfig")
        application_id, name, arn = self.emrserverless_backend.create_application(
            name=name,
            release_label=release_label,
            type=type,
            client_token=client_token,
            initial_capacity=initial_capacity,
            maximum_capacity=maximum_capacity,
            tags=tags,
            auto_start_config=auto_start_config,
            auto_stop_config=auto_stop_config,
        )
        return (
            200,
            {},
            json.dumps(dict(applicationId=application_id, name=name, arn=arn)),
        )

    
    def list_applications(self):
        params = self._get_params()
        next_token = params.get("nextToken")
        max_results = params.get("maxResults")
        states = params.get("states")
        applications, next_token = self.emrserverless_backend.list_applications(
            next_token=next_token,
            max_results=max_results,
            states=states,
        )
        # TODO: adjust response
        return 200, {}, json.dumps(dict(applications=applications, nextToken=next_token))

# add templates from here
