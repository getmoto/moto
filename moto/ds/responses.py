"""Handles Directory Service requests, invokes methods, returns responses."""
import json

from moto.core.exceptions import InvalidToken
from moto.core.responses import BaseResponse
from moto.ds.exceptions import InvalidNextTokenException
from moto.ds.models import ds_backends


class DirectoryServiceResponse(BaseResponse):
    """Handler for DirectoryService requests and responses."""

    @property
    def ds_backend(self):
        """Return backend instance specific for this region."""
        return ds_backends[self.region]

    def create_directory(self):
        """Create a Simple AD directory."""
        name = self._get_param("Name")
        short_name = self._get_param("ShortName")
        password = self._get_param("Password")
        description = self._get_param("Description")
        size = self._get_param("Size")
        vpc_settings = self._get_param("VpcSettings")
        tags = self._get_list_prefix("Tags.member")
        directory_id = self.ds_backend.create_directory(
            region=self.region,
            name=name,
            short_name=short_name,
            password=password,
            description=description,
            size=size,
            vpc_settings=vpc_settings,
            tags=tags,
        )
        return json.dumps({"DirectoryId": directory_id})

    def delete_directory(self):
        """Delete a Directory Service directory."""
        directory_id_arg = self._get_param("DirectoryId")
        directory_id = self.ds_backend.delete_directory(directory_id_arg)
        return json.dumps({"DirectoryId": directory_id})

    def describe_directories(self):
        """Return directory info for the given IDs or all IDs."""
        directory_ids = self._get_param("DirectoryIds")
        next_token = self._get_param("NextToken")
        limit = self._get_int_param("Limit")
        try:
            (descriptions, next_token) = self.ds_backend.describe_directories(
                directory_ids, next_token=next_token, limit=limit
            )
        except InvalidToken as exc:
            raise InvalidNextTokenException() from exc

        response = {"DirectoryDescriptions": [x.to_json() for x in descriptions]}
        if next_token:
            response["NextToken"] = next_token
        return json.dumps(response)

    def get_directory_limits(self):
        """Return directory limit information for the current region."""
        limits = self.ds_backend.get_directory_limits()
        return json.dumps({"DirectoryLimits": limits})
