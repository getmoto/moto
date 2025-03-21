"""AppRegistryBackend class with methods for supported APIs."""

import datetime
from typing import Any, Dict, List

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.moto_api._internal import mock_random
from moto.utilities.tagging_service import TaggingService
from moto.utilities.utils import get_partition


class AssociatedResource(BaseBackend):
    def __init__(self, resource_type: str, resource: str, options: List[str]):
        self.resource = resource
        self.resource_type = resource_type
        self.options = options


class Application(BaseModel):
    def __init__(
        self,
        name: str,
        description: str,
        region: str,
        account_id: str,
    ):
        self.id = mock_random.get_random_string(
            length=27, include_digits=True, lower_case=True
        )
        self.arn = f"arn:{get_partition(region)}:servicecatalog:{region}:{account_id}:applications/{self.id}"
        self.name = name
        self.description = description
        self.creationTime = datetime.datetime.now()
        self.lastUpdateTime = self.creationTime
        self.tags: Dict[str, str] = dict()
        self.applicationTag: Dict[str, str] = {"awsApplication": self.arn}

        self.associated_resources: Dict[str, AssociatedResource] = dict()

    def to_json(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "arn": self.arn,
            "name": self.name,
            "description": self.description,
            "creationTime": str(self.creationTime),
            "lastUpdateTime": str(self.lastUpdateTime),
            "tags": self.tags,
            "applicationTag": self.applicationTag,
        }


class AppRegistryBackend(BaseBackend):
    """Implementation of AppRegistry APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.applications: Dict[str, Application] = dict()
        self.tagger = TaggingService()

    # add methods from here

    def create_application(
        self, name: str, description: str, tags: Dict[str, str], client_token: str
    ) -> Application:
        app = Application(
            name,
            description,
            region=self.region_name,
            account_id=self.account_id,
        )
        self.applications[app.id] = app
        self.tag_resource(app.arn, tags)
        return app

    def list_applications(self) -> List[Application]:
        return list(self.applications.values())

    def list_tags_for_resource(self, arn: str) -> Dict[str, str]:
        return self.tagger.get_tag_dict_for_resource(arn)

    def tag_resource(self, arn: str, tags: Dict[str, str]) -> None:
        self.tagger.tag_resource(arn, TaggingService.convert_dict_to_tags_input(tags))

    def untag_resource(self, arn: str, tag_keys: List[str]) -> None:
        self.tagger.untag_resource_using_names(arn, tag_keys)


servicecatalogappregistry_backends = BackendDict(
    AppRegistryBackend, "servicecatalog-appregistry"
)
