"""CloudDirectoryBackend class with methods for supported APIs."""

import datetime
from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel
from moto.utilities.tagging_service import TaggingService
from typing import List
from .exceptions import InvalidArnException

class Directory(BaseModel):
    def __init__(self, account_id: str, region: str, name: str, schema_arn: str) -> None:
        self.name = name
        self.schema_arn = schema_arn
        self.directory_arn = f"arn:aws:clouddirectory:{region}:{account_id}:directory/{name}"
        self.state = "ENABLED"
        self.tags = {}
        self.creation_date_time = datetime.datetime.now()
        self.object_identifier = f"directory-{name}"
    
    def to_dict(self):
        return {
            "Name": self.name,
            "SchemaArn": self.schema_arn,
            "DirectoryArn": self.directory_arn,
            "State": self.state,
            "Tags": self.tags,
            "CreationDateTime": str(self.creation_date_time),
            "ObjectIdentifier": self.object_identifier,
        }


class CloudDirectoryBackend(BaseBackend):
    """Implementation of CloudDirectory APIs."""

    def __init__(self, region_name, account_id) -> None:
        super().__init__(region_name, account_id)
        self.directories = {}
        self.tagger = TaggingService()

    def create_directory(self, name: str, schema_arn: str) -> Directory:
        directory = Directory(self.account_id, self.region_name, name, schema_arn)
        self.directories[directory.directory_arn] = directory
        return directory
    
    def list_directories(self, state) -> List[Directory]:
        directories = list(self.directories.values())
        return directories
    
    def tag_resource(self, resource_arn, tags) -> None:
        self.tagger.tag_resource(
            resource_arn, self.tagger.convert_dict_to_tags_input(tags)
        )
        return
    
    def untag_resource(self, resource_arn, tag_keys) -> None:
        if not isinstance(tag_keys, list):
            tag_keys = [tag_keys]
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)
        return
    
    def delete_directory(self, directory_arn:str) -> str:
        directory = self.directories.pop(directory_arn)
        return directory.directory_arn
    
    def get_directory(self, directory_arn: str):
        directory = self.directories.get(directory_arn)
        if not directory:
            raise InvalidArnException(directory_arn)
        return directory
    

clouddirectory_backends = BackendDict(CloudDirectoryBackend, "clouddirectory")
