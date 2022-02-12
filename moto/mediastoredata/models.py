import hashlib
from collections import OrderedDict

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict
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
    def __init__(self, region_name=None):
        super().__init__()
        self.region_name = region_name
        self._objects = OrderedDict()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def put_object(
        self,
        body,
        path,
        content_type=None,
        cache_control=None,
        storage_class="TEMPORAL",
        upload_availability="STANDARD",
    ):
        new_object = Object(
            path=path, body=body, etag="etag", storage_class=storage_class
        )
        self._objects[path] = new_object
        return new_object

    def delete_object(self, path):
        if path not in self._objects:
            error = "ObjectNotFoundException"
            raise ClientError(error, "Object with id={} not found".format(path))
        del self._objects[path]
        return {}

    def get_object(self, path, object_range=None):
        """
        The Range-parameter is not yet supported.
        """
        objects_found = [item for item in self._objects.values() if item.path == path]
        if len(objects_found) == 0:
            error = "ObjectNotFoundException"
            raise ClientError(error, "Object with id={} not found".format(path))
        return objects_found[0]

    def list_items(self, path, max_results=1000, next_token=None):
        """
        The Path- and MaxResults-parameters are not yet supported.
        """
        items = self._objects.values()
        response_items = [c.to_dict() for c in items]
        return response_items


mediastoredata_backends = BackendDict(MediaStoreDataBackend, "mediastore-data")
