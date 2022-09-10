import json
from moto.core.utils import amzn_request_id

from moto.core.responses import BaseResponse
from .models import GLOBAL_REGION, wafv2_backends


class WAFV2Response(BaseResponse):
    def __init__(self):
        super().__init__(service_name="wafv2")

    @property
    def wafv2_backend(self):
        return wafv2_backends[self.current_account][self.region]

    @amzn_request_id
    def associate_web_acl(self):
        body = json.loads(self.body)
        web_acl_arn = body["WebACLArn"]
        resource_arn = body["ResourceArn"]
        self.wafv2_backend.associate_web_acl(web_acl_arn, resource_arn)
        return 200, {}, "{}"

    @amzn_request_id
    def disassociate_web_acl(self):
        body = json.loads(self.body)
        resource_arn = body["ResourceArn"]
        self.wafv2_backend.disassociate_web_acl(resource_arn)
        return 200, {}, "{}"

    @amzn_request_id
    def get_web_acl_for_resource(self):
        body = json.loads(self.body)
        resource_arn = body["ResourceArn"]
        web_acl = self.wafv2_backend.get_web_acl_for_resource(resource_arn)
        response = {"WebACL": web_acl.to_dict() if web_acl else None}
        response_headers = {"Content-Type": "application/json"}
        return 200, response_headers, json.dumps(response)

    @amzn_request_id
    def create_web_acl(self):
        """https://docs.aws.amazon.com/waf/latest/APIReference/API_CreateWebACL.html (response syntax section)"""

        scope = self._get_param("Scope")
        if scope == "CLOUDFRONT":
            self.region = GLOBAL_REGION
        name = self._get_param("Name")
        body = json.loads(self.body)
        description = body.get("Description")
        tags = body.get("Tags", [])
        rules = body.get("Rules", [])
        web_acl = self.wafv2_backend.create_web_acl(
            name,
            body["VisibilityConfig"],
            body["DefaultAction"],
            scope,
            description,
            tags,
            rules,
        )
        response = {"Summary": web_acl.to_dict()}
        response_headers = {"Content-Type": "application/json"}
        return 200, response_headers, json.dumps(response)

    @amzn_request_id
    def delete_web_acl(self):
        scope = self._get_param("Scope")
        if scope == "CLOUDFRONT":
            self.region = GLOBAL_REGION
        name = self._get_param("Name")
        _id = self._get_param("Id")
        self.wafv2_backend.delete_web_acl(name, _id)
        response_headers = {"Content-Type": "application/json"}
        return 200, response_headers, "{}"

    @amzn_request_id
    def get_web_acl(self):
        scope = self._get_param("Scope")
        if scope == "CLOUDFRONT":
            self.region = GLOBAL_REGION
        name = self._get_param("Name")
        _id = self._get_param("Id")
        web_acl = self.wafv2_backend.get_web_acl(name, _id)
        response = {"WebACL": web_acl.to_dict(), "LockToken": web_acl.lock_token}
        response_headers = {"Content-Type": "application/json"}
        return 200, response_headers, json.dumps(response)

    @amzn_request_id
    def list_web_ac_ls(self):
        """https://docs.aws.amazon.com/waf/latest/APIReference/API_ListWebACLs.html (response syntax section)"""

        scope = self._get_param("Scope")
        if scope == "CLOUDFRONT":
            self.region = GLOBAL_REGION
        all_web_acls = self.wafv2_backend.list_web_acls()
        response = {"NextMarker": "Not Implemented", "WebACLs": all_web_acls}
        response_headers = {"Content-Type": "application/json"}
        return 200, response_headers, json.dumps(response)

    @amzn_request_id
    def list_rule_groups(self):
        scope = self._get_param("Scope")
        if scope == "CLOUDFRONT":
            self.region = GLOBAL_REGION
        rule_groups = self.wafv2_backend.list_rule_groups()
        response = {"RuleGroups": [rg.to_dict() for rg in rule_groups]}
        response_headers = {"Content-Type": "application/json"}
        return 200, response_headers, json.dumps(response)

    @amzn_request_id
    def list_tags_for_resource(self):
        arn = self._get_param("ResourceARN")
        self.region = arn.split(":")[3]
        tags = self.wafv2_backend.list_tags_for_resource(arn)
        response = {"TagInfoForResource": {"ResourceARN": arn, "TagList": tags}}
        response_headers = {"Content-Type": "application/json"}
        return 200, response_headers, json.dumps(response)

    @amzn_request_id
    def tag_resource(self):
        body = json.loads(self.body)
        arn = body.get("ResourceARN")
        self.region = arn.split(":")[3]
        tags = body.get("Tags")
        self.wafv2_backend.tag_resource(arn, tags)
        return 200, {}, "{}"

    @amzn_request_id
    def untag_resource(self):
        body = json.loads(self.body)
        arn = body.get("ResourceARN")
        self.region = arn.split(":")[3]
        tag_keys = body.get("TagKeys")
        self.wafv2_backend.untag_resource(arn, tag_keys)
        return 200, {}, "{}"

    @amzn_request_id
    def update_web_acl(self):
        body = json.loads(self.body)
        name = body.get("Name")
        _id = body.get("Id")
        scope = body.get("Scope")
        if scope == "CLOUDFRONT":
            self.region = GLOBAL_REGION
        default_action = body.get("DefaultAction")
        rules = body.get("Rules")
        description = body.get("Description")
        visibility_config = body.get("VisibilityConfig")
        lock_token = self.wafv2_backend.update_web_acl(
            name, _id, default_action, rules, description, visibility_config
        )
        return 200, {}, json.dumps({"NextLockToken": lock_token})


# notes about region and scope
# --scope = CLOUDFRONT is ALWAYS us-east-1 (but we use "global" instead to differentiate between REGIONAL us-east-1)
# --scope = REGIONAL defaults to us-east-1, but could be anything if specified with --region=<anyRegion>
# region is grabbed from the auth header, NOT from the body - even with --region flag
# The CLOUDFRONT wacls in aws console are located in us-east-1 but the us-east-1 REGIONAL wacls are not included
