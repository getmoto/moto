"""CloudDirectoryBackend class with methods for supported APIs."""

import datetime
from typing import Dict, List

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.utilities.tagging_service import TaggingService

from .exceptions import InvalidArnException


class Directory(BaseModel):
    def __init__(
        self, account_id: str, region: str, name: str, schema_arn: str
    ) -> None:
        self.name = name
        self.schema_arn = schema_arn
        self.directory_arn = (
            f"arn:aws:clouddirectory:{region}:{account_id}:directory/{name}"
        )
        self.state = "ENABLED"
        self.creation_date_time = datetime.datetime.now()
        self.object_identifier = f"directory-{name}"

    def to_dict(self) -> Dict[str, str]:
        return {
            "Name": self.name,
            "SchemaArn": self.schema_arn,
            "DirectoryArn": self.directory_arn,
            "State": self.state,
            "CreationDateTime": str(self.creation_date_time),
            "ObjectIdentifier": self.object_identifier,
        }


class CloudDirectoryBackend(BaseBackend):
    """Implementation of CloudDirectory APIs."""

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.directories: Dict[str, Directory] = {}
        self.tagger = TaggingService()

    def create_directory(self, name: str, schema_arn: str) -> Directory:
        directory = Directory(self.account_id, self.region_name, name, schema_arn)
        self.directories[directory.directory_arn] = directory
        return directory

    def list_directories(self, state: str) -> List[Directory]:
        directories = list(self.directories.values())
        return directories

    def tag_resource(self, resource_arn: str, tags: List[Dict[str, str]]) -> None:
        self.tagger.tag_resource(resource_arn, tags)
        return

    def untag_resource(self, resource_arn: str, tag_keys: List[str]) -> None:
        if not isinstance(tag_keys, list):
            tag_keys = [tag_keys]
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)
        return

    def delete_directory(self, directory_arn: str) -> str:
        directory = self.directories.pop(directory_arn)
        return directory.directory_arn

    def get_directory(self, directory_arn: str) -> Directory:
        directory = self.directories.get(directory_arn)
        if not directory:
            raise InvalidArnException(directory_arn)
        return directory

    def list_tags_for_resource(
        self, resource_arn: str, next_token: str, max_results: int
    ) -> List[Dict[str, str]]:
        tags = self.tagger.list_tags_for_resource(resource_arn)["Tags"]
        return tags


clouddirectory_backends = BackendDict(CloudDirectoryBackend, "clouddirectory")
