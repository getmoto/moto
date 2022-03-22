"""Handles incoming pinpoint requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from urllib.parse import unquote
from .models import pinpoint_backends


class PinpointResponse(BaseResponse):
    """Handler for Pinpoint requests and responses."""

    @property
    def pinpoint_backend(self):
        """Return backend instance specific for this region."""
        return pinpoint_backends[self.region]

    def app(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "DELETE":
            return self.delete_app()
        if request.method == "GET":
            return self.get_app()

    def apps(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.get_apps()
        if request.method == "POST":
            return self.create_app()

    def app_settings(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.get_application_settings()
        if request.method == "PUT":
            return self.update_application_settings()

    def eventstream(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "DELETE":
            return self.delete_event_stream()
        if request.method == "GET":
            return self.get_event_stream()
        if request.method == "POST":
            return self.put_event_stream()

    def tags(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "DELETE":
            return self.untag_resource()
        if request.method == "GET":
            return self.list_tags_for_resource()
        if request.method == "POST":
            return self.tag_resource()

    def create_app(self):
        params = json.loads(self.body)
        name = params.get("Name")
        tags = params.get("tags", {})
        app = self.pinpoint_backend.create_app(name=name, tags=tags)
        return 201, {}, json.dumps(app.to_json())

    def delete_app(self):
        application_id = self.path.split("/")[-1]
        app = self.pinpoint_backend.delete_app(application_id=application_id)
        return 200, {}, json.dumps(app.to_json())

    def get_app(self):
        application_id = self.path.split("/")[-1]
        app = self.pinpoint_backend.get_app(application_id=application_id)
        return 200, {}, json.dumps(app.to_json())

    def get_apps(self):
        apps = self.pinpoint_backend.get_apps()
        resp = {"Item": [a.to_json() for a in apps]}
        return 200, {}, json.dumps(resp)

    def update_application_settings(self):
        application_id = self.path.split("/")[-2]
        settings = json.loads(self.body)
        app_settings = self.pinpoint_backend.update_application_settings(
            application_id=application_id, settings=settings
        )
        app_settings = app_settings.to_json()
        app_settings["ApplicationId"] = application_id
        return 200, {}, json.dumps(app_settings)

    def get_application_settings(self):
        application_id = self.path.split("/")[-2]
        app_settings = self.pinpoint_backend.get_application_settings(
            application_id=application_id
        )
        app_settings = app_settings.to_json()
        app_settings["ApplicationId"] = application_id
        return 200, {}, json.dumps(app_settings)

    def list_tags_for_resource(self):
        resource_arn = unquote(self.path).split("/tags/")[-1]
        tags = self.pinpoint_backend.list_tags_for_resource(resource_arn=resource_arn)
        return 200, {}, json.dumps(tags)

    def tag_resource(self):
        resource_arn = unquote(self.path).split("/tags/")[-1]
        tags = json.loads(self.body).get("tags", {})
        self.pinpoint_backend.tag_resource(resource_arn=resource_arn, tags=tags)
        return 200, {}, "{}"

    def untag_resource(self):
        resource_arn = unquote(self.path).split("/tags/")[-1]
        tag_keys = self.querystring.get("tagKeys")
        self.pinpoint_backend.untag_resource(
            resource_arn=resource_arn, tag_keys=tag_keys
        )
        return 200, {}, "{}"

    def put_event_stream(self):
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

    def get_event_stream(self):
        application_id = self.path.split("/")[-2]
        event_stream = self.pinpoint_backend.get_event_stream(
            application_id=application_id
        )
        resp = event_stream.to_json()
        resp["ApplicationId"] = application_id
        return 200, {}, json.dumps(resp)

    def delete_event_stream(self):
        application_id = self.path.split("/")[-2]
        event_stream = self.pinpoint_backend.delete_event_stream(
            application_id=application_id
        )
        resp = event_stream.to_json()
        resp["ApplicationId"] = application_id
        return 200, {}, json.dumps(resp)
