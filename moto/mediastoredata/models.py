from __future__ import unicode_literals

import datetime
from collections import OrderedDict

from boto3 import Session

from moto.core import BaseBackend, BaseModel
from .exceptions import ClientError


class CreatedObject(BaseModel):
    def __init__(self, *args, **kwargs):
        self.path = kwargs.get("Path")
        self.content_sha256 = kwargs.get("ContentSHA256")
        self.etag = kwargs.get("ETag")
        self.storage_class = kwargs.get("StorageClass")

    def to_dict(self, exclude=None):
        data = {
            "ETag": self.etag,
            "Name": self.path,
            "Type": "FILE",
            "ContentLength": 123,
            "StorageClass": self.storage_class,
            "Path": self.path,
            "ContentSHA256": self.content_sha256,
        }
        if exclude:
            for key in exclude:
                del data[key]
        return data


class Object(BaseModel):
    def __init__(self, *args, **kwargs):
        self.etag = kwargs.get("ETag")
        self.content_type = kwargs.get("ContentType")
        self.content_length = kwargs.get("ContentLength")
        self.cache_control = kwargs.get("CacheControl")
        self.last_modified = datetime.datetime.now()

    def to_dict(self, exclude=None):
        data = {
            "ETag": self.etag,
            "ContentType": self.content_type,
            "ContentLength": self.content_length,
            "CacheControl": self.cache_control,
            "LastModified": self.last_modified,
        }
        if exclude:
            for key in exclude:
                del data[key]
        return data


class MediaStoreDataBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(MediaStoreDataBackend, self).__init__()
        self.region_name = region_name
        self._objects = OrderedDict()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def put_object(
        self,
        Body,
        Path,
        ContentType=None,
        CacheControl=None,
        StorageClass="TEMPORAL",
        UploadAvailability="STANDARD",
    ):
        new_object = CreatedObject(
            Path=Path, ContentSHA256=Body, ETag="etag", StorageClass="TEMPORAL"
        )
        self._objects[Path] = new_object
        return new_object

    def delete_object(self, path):
        if path not in self._objects:
            error = "ObjectNotFoundException"
            raise ClientError(error, "Object with id={} not found".format(path))
        del self._objects[path]
        return {}

    def get_object(self, Path, Range=None):
        objects_found = [item for item in self._objects.values() if item.path == Path]
        if len(objects_found) == 0:
            error = "ObjectNotFoundException"
            raise ClientError(error, "Object with id={} not found".format(Path))
        return objects_found[0]

    def list_items(self, Path, MaxResults=1000, NextToken=None) -> []:
        items = self._objects.values()
        response_items = [c.to_dict() for c in items]
        return response_items


mediastoredata_backends = {}
for region in Session().get_available_regions("mediastore-data"):
    mediastoredata_backends[region] = MediaStoreDataBackend(region)
for region in Session().get_available_regions(
    "mediastore-data", partition_name="aws-us-gov"
):
    mediastoredata_backends[region] = MediaStoreDataBackend(region)
for region in Session().get_available_regions(
    "mediastore-data", partition_name="aws-cn"
):
    mediastoredata_backends[region] = MediaStoreDataBackend(region)
