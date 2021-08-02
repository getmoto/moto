from __future__ import unicode_literals
import json
from moto.core.utils import amzn_request_id

from moto.core.responses import BaseResponse
from .models import GLOBAL_REGION, wafv2_backends


class WAFV2Response(BaseResponse):
    @property
    def wafv2_backend(self):
        return wafv2_backends[self.region]  # default region is "us-east-1"

    @amzn_request_id
    def create_web_acl(self):
        """  https://docs.aws.amazon.com/waf/latest/APIReference/API_CreateWebACL.html (response syntax section) """

        scope = self._get_param("Scope")
        if scope == "CLOUDFRONT":
            self.region = GLOBAL_REGION
        name = self._get_param("Name")
        body = json.loads(self.body)
        web_acl = self.wafv2_backend.create_web_acl(
            name, body["VisibilityConfig"], body["DefaultAction"], scope
        )
        response = {
            "Summary": web_acl.to_dict(),
        }
        response_headers = {"Content-Type": "application/json"}
        return 200, response_headers, json.dumps(response)

    @amzn_request_id
    def list_web_ac_ls(self):
        """  https://docs.aws.amazon.com/waf/latest/APIReference/API_ListWebACLs.html (response syntax section) """

        scope = self._get_param("Scope")
        if scope == "CLOUDFRONT":
            self.region = GLOBAL_REGION
        all_web_acls = self.wafv2_backend.list_web_acls()
        response = {"NextMarker": "Not Implemented", "WebACLs": all_web_acls}
        response_headers = {"Content-Type": "application/json"}
        return 200, response_headers, json.dumps(response)


# notes about region and scope
# --scope = CLOUDFRONT is ALWAYS us-east-1 (but we use "global" instead to differentiate between REGIONAL us-east-1)
# --scope = REGIONAL defaults to us-east-1, but could be anything if specified with --region=<anyRegion>
# region is grabbed from the auth header, NOT from the body - even with --region flag
# The CLOUDFRONT wacls in aws console are located in us-east-1 but the us-east-1 REGIONAL wacls are not included
