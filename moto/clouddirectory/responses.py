"""Handles incoming clouddirectory requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import clouddirectory_backends


class CloudDirectoryResponse(BaseResponse):
    """Handler for CloudDirectory requests and responses."""

    def __init__(self):
        super().__init__(service_name="clouddirectory")

    @property
    def clouddirectory_backend(self):
        """Return backend instance specific for this region."""
        # TODO
        # clouddirectory_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return clouddirectory_backends[self.current_account][self.region]

    # add methods from here

    
    def create_directory(self):
        params = self._get_params()
        name = params.get("Name")
        schema_arn = params.get("SchemaArn")
        directory_arn, name, object_identifier, applied_schema_arn = self.clouddirectory_backend.create_directory(
            name=name,
            schema_arn=schema_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(directoryArn=directory_arn, name=name, objectIdentifier=object_identifier, appliedSchemaArn=applied_schema_arn))

    
    def list_directories(self):
        params = self._get_params()
        next_token = params.get("NextToken")
        max_results = params.get("MaxResults")
        state = params.get("state")
        directories, next_token = self.clouddirectory_backend.list_directories(
            next_token=next_token,
            max_results=max_results,
            state=state,
        )
        # TODO: adjust response
        return json.dumps(dict(directories=directories, nextToken=next_token))
# add templates from here
    
    def tag_resource(self):
        params = self._get_params()
        resource_arn = params.get("ResourceArn")
        tags = params.get("Tags")
        self.clouddirectory_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict())
    
    def untag_resource(self):
        params = self._get_params()
        resource_arn = params.get("ResourceArn")
        tag_keys = params.get("TagKeys")
        self.clouddirectory_backend.untag_resource(
            resource_arn=resource_arn,
            tag_keys=tag_keys,
        )
        # TODO: adjust response
        return json.dumps(dict())
    
    def delete_directory(self):
        params = self._get_params()
        directory_arn = params.get("DirectoryArn")
        directory_arn = self.clouddirectory_backend.delete_directory(
            directory_arn=directory_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(directoryArn=directory_arn))
    
    def get_directory(self):
        params = self._get_params()
        directory_arn = params.get("DirectoryArn")
        directory = self.clouddirectory_backend.get_directory(
            directory_arn=directory_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(directory=directory))
