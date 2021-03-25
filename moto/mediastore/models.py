from __future__ import unicode_literals
from boto3 import Session
from moto.core import BaseBackend, BaseModel
from collections import OrderedDict

class LifecyclePolicy(BaseModel):
    def __init__(self, *args, **kwargs):
        self.container_name = kwargs.get("container_name")
        self.lifecycle_policy = kwargs.get("lifecycle_policy")
    
    def to_dict(self): 
        data = {
            "ContainerName": self.container_name,
            "LifecylcePolicy": self.lifecycle_policy
        }


class MediaStoreBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(MediaStoreBackend, self).__init__()
        self.region_name = region_name
        self._lifecycle_policies = OrderedDict()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def put_lifecycle_policy(self, container_name, lifecycle_policy):
        self._lifecycle_policies[container_name].lifecycle_policy = lifecycle_policy
        print(lifecycle_policy)
        print(container_name)
        return {}

    
    # add methods from here


mediastore_backends = {}
for region in Session().get_available_regions("mediastore"):
    mediastore_backends[region] = MediaStoreBackend()
for region in Session().get_available_regions("mediastore", partition_name="aws-us-gov"):
    mediastore_backends[region] = MediaStoreBackend()
for region in Session().get_available_regions("mediastore", partition_name="aws-cn"):
    mediastore_backends[region] = MediaStoreBackend()
