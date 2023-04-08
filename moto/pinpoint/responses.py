"""Handles incoming pinpoint requests, invokes methods, returns responses."""
import json
from typing import Any

from moto.core.common_types import TYPE_RESPONSE
from moto.core.responses import BaseResponse
from urllib.parse import unquote
from .models import pinpoint_backends, PinpointBackend


class PinpointResponse(BaseResponse):
    """Handler for Pinpoint requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="pinpoint")

    @property
    def pinpoint_backend(self) -> PinpointBackend:
        """Return backend instance specific for this region."""
        return pinpoint_backends[self.current_account][self.region]

    def app(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "DELETE":
            return self.delete_app()
        if request.method == "GET":
            return self.get_app()

    def apps(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.get_apps()
        if request.method == "POST":
            return self.create_app()

    def app_settings(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.get_application_settings()
        if request.method == "PUT":
            return self.update_application_settings()

    def eventstream(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "DELETE":
            return self.delete_event_stream()
        if request.method == "GET":
            return self.get_event_stream()
        if request.method == "POST":
            return self.put_event_stream()

    def tags(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "DELETE":
            return self.untag_resource()
        if request.method == "GET":
            return self.list_tags_for_resource()
        if request.method == "POST":
            return self.tag_resource()

    def create_app(self) -> TYPE_RESPONSE:
        params = json.loads(self.body)
        name = params.get("Name")
        tags = params.get("tags", {})
        app = self.pinpoint_backend.create_app(name=name, tags=tags)
        return 201, {}, json.dumps(app.to_json())

    def delete_app(self) -> TYPE_RESPONSE:
        application_id = self.path.split("/")[-1]
        app = self.pinpoint_backend.delete_app(application_id=application_id)
        return 200, {}, json.dumps(app.to_json())

    def get_app(self) -> TYPE_RESPONSE:
        application_id = self.path.split("/")[-1]
        app = self.pinpoint_backend.get_app(application_id=application_id)
        return 200, {}, json.dumps(app.to_json())

    def get_apps(self) -> TYPE_RESPONSE:
        apps = self.pinpoint_backend.get_apps()
        resp = {"Item": [a.to_json() for a in apps]}
        return 200, {}, json.dumps(resp)

    def update_application_settings(self) -> TYPE_RESPONSE:
        application_id = self.path.split("/")[-2]
        settings = json.loads(self.body)
        app_settings = self.pinpoint_backend.update_application_settings(
            application_id=application_id, settings=settings
        )
        response = app_settings.to_json()
        response["ApplicationId"] = application_id
        return 200, {}, json.dumps(response)

    def get_application_settings(self) -> TYPE_RESPONSE:
        application_id = self.path.split("/")[-2]
        app_settings = self.pinpoint_backend.get_application_settings(
            application_id=application_id
        )
        response = app_settings.to_json()
        response["ApplicationId"] = application_id
        return 200, {}, json.dumps(response)

    def list_tags_for_resource(self) -> TYPE_RESPONSE:
        resource_arn = unquote(self.path).split("/tags/")[-1]
        tags = self.pinpoint_backend.list_tags_for_resource(resource_arn=resource_arn)
        return 200, {}, json.dumps(tags)

    def tag_resource(self) -> TYPE_RESPONSE:
        resource_arn = unquote(self.path).split("/tags/")[-1]
        tags = json.loads(self.body).get("tags", {})
        self.pinpoint_backend.tag_resource(resource_arn=resource_arn, tags=tags)
        return 200, {}, "{}"

    def untag_resource(self) -> TYPE_RESPONSE:
        resource_arn = unquote(self.path).split("/tags/")[-1]
        tag_keys = self.querystring.get("tagKeys")
        self.pinpoint_backend.untag_resource(
            resource_arn=resource_arn, tag_keys=tag_keys  # type: ignore[arg-type]
        )
        return 200, {}, "{}"

    def put_event_stream(self) -> TYPE_RESPONSE:
        application_id = self.path.split("/")[-2]
        params = json.loads(self.body)
        stream_arn = params.get("DestinationStreamArn")
        role_arn = params.get("RoleArn")
        event_stream = self.pinpoint_backend.put_event_stream(
            application_id=application_id, stream_arn=stream_arn, role_arn=role_arn
        )
        resp = event_stream.to_json()
        resp["ApplicationId"] = application_id
        return 200, {}, json.dumps(resp)

    def get_event_stream(self) -> TYPE_RESPONSE:
        application_id = self.path.split("/")[-2]
        event_stream = self.pinpoint_backend.get_event_stream(
            application_id=application_id
        )
        resp = event_stream.to_json()
        resp["ApplicationId"] = application_id
        return 200, {}, json.dumps(resp)

    def delete_event_stream(self) -> TYPE_RESPONSE:
        application_id = self.path.split("/")[-2]
        event_stream = self.pinpoint_backend.delete_event_stream(
            application_id=application_id
        )
        resp = event_stream.to_json()
        resp["ApplicationId"] = application_id
        return 200, {}, json.dumps(resp)
