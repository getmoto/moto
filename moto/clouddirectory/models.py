"""CloudDirectoryBackend class with methods for supported APIs."""

from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel

class Directory(BaseModel):
    def __init__(self, name, schema_arn):
        self.name = name
        self.schema_arn = schema_arn
        self.directory_arn = f"arn:aws:clouddirectory:us-east-1:123456789012:directory/{name}"
        self.state = "ENABLED"
        self.tags = {}
        self.creation_date_time = datetime.now()


class CloudDirectoryBackend(BaseBackend):
    """Implementation of CloudDirectory APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)

    # add methods from here

    def create_directory(self, name, schema_arn):
        # implement here
        return directory_arn, name, object_identifier, applied_schema_arn
    
    def list_directories(self, next_token, max_results, state):
        # implement here
        return directories, next_token
    
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
