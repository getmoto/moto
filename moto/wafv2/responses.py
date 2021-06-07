from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from .models import wafv2_backends, GLOBAL_REGION, US_EAST_1_REGION


class WAFV2Response(BaseResponse):
    SERVICE_NAME = "wafv2"

    @property
    def wafv2_backend(self):
        return wafv2_backends[self.region]

    def list_web_ac_ls(self):
        scope = json.loads(self.body)["Scope"]
        if scope.upper() == "REGIONAL":
            wacl = wafv2_backends[GLOBAL_REGION]
        else:
            wacl = wafv2_backends[US_EAST_1_REGION]
        wacls = [w.to_dict() for w in wacl.wacls]
        wacls_json = json.dumps(wacls)
        response = '{"WebACLs": ' + wacls_json + "}"
        return 200, {"Content-Type": "application/json"}, response
