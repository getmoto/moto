"""CloudDirectoryBackend class with methods for supported APIs."""

import datetime
from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel
from typing import List

class Directory(BaseModel):
    def __init__(self, account_id: str, region: str, name: str, schema_arn: str) -> None:
        self.name = name
        self.schema_arn = schema_arn
        self.directory_arn = f"arn:aws:clouddirectory:{region}:{account_id}:directory/{name}"
        self.state = "ENABLED"
        self.tags = {}
        self.creation_date_time = datetime.datetime.now()
        self.object_identifier = f"directory-{name}"


class CloudDirectoryBackend(BaseBackend):
    """Implementation of CloudDirectory APIs."""

    def __init__(self, region_name, account_id) -> None:
        super().__init__(region_name, account_id)
        self.directories = {}

    def create_directory(self, name: str, schema_arn: str) -> Directory:
        directory = Directory(self.account_id, self.region_name, name, schema_arn)
        self.directories[directory.directory_arn] = directory
        return directory
    
    def list_directories(self, state) -> List[Directory]:
        directories = list(self.directories.values())
        return directories
    
    def tag_resource(self, resource_arn, tags):
        # implement here
        return 
    
    def untag_resource(self, resource_arn, tag_keys):
        # implement here
        return 
    
    def delete_directory(self, directory_arn):
        # implement here
        return directory_arn
    
    def get_directory(self, directory_arn):
        # implement here
        return directory
    

clouddirectory_backends = BackendDict(CloudDirectoryBackend, "clouddirectory")
