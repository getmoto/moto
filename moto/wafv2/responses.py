from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import wafv2_backends
import json


class WAFV2Response(BaseResponse):
    SERVICE_NAME = 'wafv2'
    @property
    def wafv2_backend(self):
        return wafv2_backends[self.region]

    # add methods from here


# add templates from here
