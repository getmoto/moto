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
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return clouddirectory_backends[self.current_account][self.region]

    def create_directory(self) -> str:
        name = self._get_param("Name")
        schema_arn = self._get_param("SchemaArn")
        directory = self.clouddirectory_backend.create_directory(
            name=name,
            schema_arn=schema_arn,
        )

        return json.dumps(
            dict(
                DirectoryArn=directory.directory_arn,
                Name=name,
                ObjectIdentifier=directory.object_identifier,
                AppliedSchemaArn=directory.schema_arn,
            )
        )

    def list_directories(self) -> str:
        next_token = self._get_param("NextToken")
        # max_results = self._get_param("MaxResults")
        state = self._get_param("State")
        directories = self.clouddirectory_backend.list_directories(
            state=state,
        )
        directory_list = [directory.to_dict() for directory in directories]
        return json.dumps(dict(Directories=directory_list, NextToken=next_token))

    def tag_resource(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        tags = self._get_param("Tags")
        self.clouddirectory_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        return json.dumps(dict())

    def untag_resource(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        tag_keys = self._get_param("TagKeys")
        self.clouddirectory_backend.untag_resource(
            resource_arn=resource_arn,
            tag_keys=tag_keys,
        )
        return json.dumps(dict())

    def delete_directory(self) -> str:
        # Retrieve arn from headers
        # https://docs.aws.amazon.com/clouddirectory/latest/APIReference/API_DeleteDirectory.html
        arn = self.headers.get("x-amz-data-partition")
        directory_arn = self.clouddirectory_backend.delete_directory(
            directory_arn=arn,
        )
        return json.dumps(dict(DirectoryArn=directory_arn))

    def get_directory(self) -> str:
        # Retrieve arn from headers
        # https://docs.aws.amazon.com/clouddirectory/latest/APIReference/API_GetDirectory.html
        arn = self.headers.get("x-amz-data-partition")
        directory = self.clouddirectory_backend.get_directory(
            directory_arn=arn,
        )
        return json.dumps(dict(Directory=directory.to_dict()))

    def list_tags_for_resource(self) -> str:
        resource_arn = self._get_param("ResourceArn")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")
        tags = self.clouddirectory_backend.list_tags_for_resource(
            resource_arn=resource_arn,
            next_token=next_token,
            max_results=max_results,
        )
        return json.dumps(dict(Tags=tags, NextToken=next_token))
