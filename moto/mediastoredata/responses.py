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
        result = self.mediastoredata_backend.get_object(path=path)
        headers = {"Path": result.path}
        return result.body, headers

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
        items = self.mediastoredata_backend.list_items()
        return json.dumps(dict(Items=items))
