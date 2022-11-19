import hashlib
from collections import OrderedDict

from moto.core import BaseBackend, BackendDict, BaseModel
from .exceptions import ClientError


class Object(BaseModel):
    def __init__(self, path, body, etag, storage_class="TEMPORAL"):
        self.path = path
        self.body = body
        self.content_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
        self.etag = etag
        self.storage_class = storage_class

    def to_dict(self):
        data = {
            "ETag": self.etag,
            "Name": self.path,
            "Type": "FILE",
            "ContentLength": 123,
            "StorageClass": self.storage_class,
            "Path": self.path,
            "ContentSHA256": self.content_sha256,
        }

        return data


class MediaStoreDataBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self._objects = OrderedDict()

    def put_object(self, body, path, storage_class="TEMPORAL"):
        """
        The following parameters are not yet implemented: ContentType, CacheControl, UploadAvailability
        """
        new_object = Object(
            path=path, body=body, etag="etag", storage_class=storage_class
        )
        self._objects[path] = new_object
        return new_object

    def delete_object(self, path):
        if path not in self._objects:
            error = "ObjectNotFoundException"
            raise ClientError(error, f"Object with id={path} not found")
        del self._objects[path]
        return {}

    def get_object(self, path):
        """
        The Range-parameter is not yet supported.
        """
        objects_found = [item for item in self._objects.values() if item.path == path]
        if len(objects_found) == 0:
            error = "ObjectNotFoundException"
            raise ClientError(error, f"Object with id={path} not found")
        return objects_found[0]

    def list_items(self):
        """
        The Path- and MaxResults-parameters are not yet supported.
        """
        items = self._objects.values()
        response_items = [c.to_dict() for c in items]
        return response_items


mediastoredata_backends = BackendDict(MediaStoreDataBackend, "mediastore-data")
