from datetime import datetime
from moto.core import get_account_id, BaseBackend, BaseModel
from moto.core.utils import BackendDict, unix_time
from moto.utilities.tagging_service import TaggingService
from uuid import uuid4

from .exceptions import ApplicationNotFound, EventStreamNotFound


class App(BaseModel):
    def __init__(self, name):
        self.application_id = str(uuid4()).replace("-", "")
        self.arn = f"arn:aws:mobiletargeting:us-east-1:{get_account_id()}:apps/{self.application_id}"
        self.name = name
        self.created = unix_time()
        self.settings = AppSettings()
        self.event_stream = None

    def get_settings(self):
        return self.settings

    def update_settings(self, settings):
        self.settings.update(settings)
        return self.settings

    def delete_event_stream(self):
        stream = self.event_stream
        self.event_stream = None
        return stream

    def get_event_stream(self):
        if self.event_stream is None:
            raise EventStreamNotFound()
        return self.event_stream

    def put_event_stream(self, stream_arn, role_arn):
        self.event_stream = EventStream(stream_arn, role_arn)
        return self.event_stream

    def to_json(self):
        return {
            "Arn": self.arn,
            "Id": self.application_id,
            "Name": self.name,
            "CreationDate": self.created,
        }


class AppSettings(BaseModel):
    def __init__(self):
        self.settings = dict()
        self.last_modified = unix_time()

    def update(self, settings):
        self.settings = settings
        self.last_modified = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def to_json(self):
        return {
            "CampaignHook": self.settings.get("CampaignHook", {}),
            "CloudWatchMetricsEnabled": self.settings.get(
                "CloudWatchMetricsEnabled", False
            ),
            "LastModifiedDate": self.last_modified,
            "Limits": self.settings.get("Limits", {}),
            "QuietTime": self.settings.get("QuietTime", {}),
        }


class EventStream(BaseModel):
    def __init__(self, stream_arn, role_arn):
        self.stream_arn = stream_arn
        self.role_arn = role_arn
        self.last_modified = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def to_json(self):
        return {
            "DestinationStreamArn": self.stream_arn,
            "RoleArn": self.role_arn,
            "LastModifiedDate": self.last_modified,
        }


class PinpointBackend(BaseBackend):
    """Implementation of Pinpoint APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.apps = {}
        self.tagger = TaggingService()

    def create_app(self, name, tags):
        app = App(name)
        self.apps[app.application_id] = app
        tags = self.tagger.convert_dict_to_tags_input(tags)
        self.tagger.tag_resource(app.arn, tags)
        return app

    def delete_app(self, application_id):
        self.get_app(application_id)
        return self.apps.pop(application_id)

    def get_app(self, application_id):
        if application_id not in self.apps:
            raise ApplicationNotFound()
        return self.apps[application_id]

    def get_apps(self):
        """
        Pagination is not yet implemented
        """
        return self.apps.values()

    def update_application_settings(self, application_id, settings):
        app = self.get_app(application_id)
        return app.update_settings(settings)

    def get_application_settings(self, application_id):
        app = self.get_app(application_id)
        return app.get_settings()

    def list_tags_for_resource(self, resource_arn):
        tags = self.tagger.get_tag_dict_for_resource(resource_arn)
        return {"tags": tags}

    def tag_resource(self, resource_arn, tags):
        tags = TaggingService.convert_dict_to_tags_input(tags)
        self.tagger.tag_resource(resource_arn, tags)

    def untag_resource(self, resource_arn, tag_keys):
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)
        return

    def put_event_stream(self, application_id, stream_arn, role_arn):
        app = self.get_app(application_id)
        return app.put_event_stream(stream_arn, role_arn)

    def get_event_stream(self, application_id):
        app = self.get_app(application_id)
        return app.get_event_stream()

    def delete_event_stream(self, application_id):
        app = self.get_app(application_id)
        return app.delete_event_stream()


pinpoint_backends = BackendDict(PinpointBackend, "pinpoint")
