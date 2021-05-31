from __future__ import unicode_literals
from boto3 import Session
from moto.core import BaseBackend, BaseModel


class WAFV2Backend(BaseBackend):
    def __init__(self, region_name=None):
        super(WAFV2Backend, self).__init__()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    # add methods from here


wafv2_backends = {}
for region in Session().get_available_regions("wafv2"):
    wafv2_backends[region] = WAFV2Backend()
for region in Session().get_available_regions("wafv2", partition_name="aws-us-gov"):
    wafv2_backends[region] = WAFV2Backend()
for region in Session().get_available_regions("wafv2", partition_name="aws-cn"):
    wafv2_backends[region] = WAFV2Backend()