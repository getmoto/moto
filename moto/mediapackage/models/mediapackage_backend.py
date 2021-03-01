from __future__ import unicode_literals

from collections import OrderedDict
from uuid import uuid4

from boto3 import Session

from moto.core import BaseBackend


class MediaPackageBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(MediaPackageBackend, self).__init__()
        self.region_name = region_name
        self._channels = OrderedDict()
        self._inputs = OrderedDict()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_channel(self):
        pass

    def describe_channel(self, channel_id):
        pass

    def delete_channel(self, channel_id):
        pass

    def create_origin_endpoint(self):
        pass

    def describe_origin_endpoint(self, channel_id):
        pass

    def delete_origin_endpoint(self, channel_id):
        pass

 

