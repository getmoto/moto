from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from .models import mediastoredata_backends


class MediaStoreDataResponse(BaseResponse):
    SERVICE_NAME = "mediastore-data"

    @property
    def mediastoredata_backend(self):
        return mediastoredata_backends[self.region]

    def get_object(self):
        path = self._get_param("Path")
        range = self._get_param("Range")
        result = self.mediastoredata_backend.get_object(Path=path, Range=range)
        headers = {"Path": result.path}
        return "body of item", headers

    def put_object(self):
        body = self.body
        path = self._get_param("Path")
        new_object = self.mediastoredata_backend.put_object(body, path)
        object_dict = new_object.to_dict()
        return json.dumps(object_dict)

    def delete_object(self):
        item_id = self._get_param("Path")
        result = self.mediastoredata_backend.delete_object(path=item_id)
        return json.dumps(result)

    def list_items(self):
        path = self._get_param("Path")
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        items = self.mediastoredata_backend.list_items(
            Path=path, MaxResults=max_results, NextToken=next_token
        )
        response_items = json.dumps(dict(Items=items))
        return response_items
