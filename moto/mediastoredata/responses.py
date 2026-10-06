import json

from moto.core.responses import BaseResponse
from moto.core.utils import rfc_1123_datetime

from .models import MediaStoreDataBackend, mediastoredata_backends


class MediaStoreDataResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="mediastore-data")

    @property
    def mediastoredata_backend(self) -> MediaStoreDataBackend:
        return mediastoredata_backends[self.current_account][self.region]

    def get_object(self) -> tuple[str, dict[str, str]]:
        path = self._get_param("Path")
        result = self.mediastoredata_backend.get_object(path=path)
        headers = {"Path": result.path}
        return result.body, headers

    def put_object(self) -> str:
        body = self.body
        path = self._get_param("Path")
        content_type = self.headers.get("Content-Type")
        cache_control = self.headers.get("Cache-Control")
        new_object = self.mediastoredata_backend.put_object(
            body, path, content_type=content_type, cache_control=cache_control
        )
        object_dict = new_object.to_dict()
        return json.dumps(object_dict)

    def describe_object(self) -> tuple[str, dict[str, str]]:
        path = self._get_param("Path")
        result = self.mediastoredata_backend.describe_object(path=path)
        headers = {
            "ETag": result.etag,
            "content-length": str(result.content_length),
            "Last-Modified": rfc_1123_datetime(result.last_modified),
        }
        if result.content_type:
            headers["Content-Type"] = result.content_type
        if result.cache_control:
            headers["Cache-Control"] = result.cache_control
        return "", headers

    def delete_object(self) -> str:
        item_id = self._get_param("Path")
        self.mediastoredata_backend.delete_object(path=item_id)
        return "{}"

    def list_items(self) -> str:
        items = self.mediastoredata_backend.list_items()
        return json.dumps({"Items": items})
