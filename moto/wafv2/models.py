import datetime
import re
from typing import Dict
from moto.core import BaseBackend, BaseModel

from .utils import make_arn_for_wacl
from .exceptions import WAFV2DuplicateItemException, WAFNonexistentItemException
from moto.core.utils import iso_8601_datetime_with_milliseconds, BackendDict
from moto.moto_api._internal import mock_random
from moto.utilities.tagging_service import TaggingService
from collections import OrderedDict


US_EAST_1_REGION = "us-east-1"
GLOBAL_REGION = "global"
APIGATEWAY_REGEX = (
    r"arn:aws:apigateway:[a-zA-Z0-9-]+::/restapis/[a-zA-Z0-9]+/stages/[a-zA-Z0-9]+"
)


# TODO: Add remaining properties
class FakeWebACL(BaseModel):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_WebACL.html
    """

    def __init__(
        self, name, arn, wacl_id, visibility_config, default_action, description, rules
    ):
        self.name = name
        self.created_time = iso_8601_datetime_with_milliseconds(datetime.datetime.now())
        self.id = wacl_id
        self.arn = arn
        self.description = description or ""
        self.capacity = 3
        self.rules = rules
        self.visibility_config = visibility_config
        self.default_action = default_action
        self.lock_token = str(mock_random.uuid4())[0:6]

    def update(self, default_action, rules, description, visibility_config):
        if default_action is not None:
            self.default_action = default_action
        if rules is not None:
            self.rules = rules
        if description is not None:
            self.description = description
        if visibility_config is not None:
            self.visibility_config = visibility_config
        self.lock_token = str(mock_random.uuid4())[0:6]

    def to_dict(self):
        # Format for summary https://docs.aws.amazon.com/waf/latest/APIReference/API_CreateWebACL.html (response syntax section)
        return {
            "ARN": self.arn,
            "Description": self.description,
            "Id": self.id,
            "Name": self.name,
            "Rules": self.rules,
            "DefaultAction": self.default_action,
            "VisibilityConfig": self.visibility_config,
        }


class WAFV2Backend(BaseBackend):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_Operations_AWS_WAFV2.html
    """

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.wacls: Dict[str, FakeWebACL] = OrderedDict()
        self.tagging_service = TaggingService()
        # TODO: self.load_balancers = OrderedDict()

    def associate_web_acl(self, web_acl_arn, resource_arn):
        """
        Only APIGateway Stages can be associated at the moment.
        """
        if web_acl_arn not in self.wacls:
            raise WAFNonexistentItemException
        stage = self._find_apigw_stage(resource_arn)
        if stage:
            stage["webAclArn"] = web_acl_arn

    def disassociate_web_acl(self, resource_arn):
        stage = self._find_apigw_stage(resource_arn)
        if stage:
            stage.pop("webAclArn", None)

    def get_web_acl_for_resource(self, resource_arn):
        stage = self._find_apigw_stage(resource_arn)
        if stage and stage.get("webAclArn"):
            wacl_arn = stage.get("webAclArn")
            return self.wacls.get(wacl_arn)
        return None

    def _find_apigw_stage(self, resource_arn):
        try:
            if re.search(APIGATEWAY_REGEX, resource_arn):
                region = resource_arn.split(":")[3]
                rest_api_id = resource_arn.split("/")[-3]
                stage_name = resource_arn.split("/")[-1]

                from moto.apigateway import apigateway_backends

                apigw = apigateway_backends[self.account_id][region]
                return apigw.get_stage(rest_api_id, stage_name)
        except:  # noqa: E722 Do not use bare except
            return None

    def create_web_acl(
        self, name, visibility_config, default_action, scope, description, tags, rules
    ):
        """
        The following parameters are not yet implemented: CustomResponseBodies, CaptchaConfig
        """
        wacl_id = str(mock_random.uuid4())
        arn = make_arn_for_wacl(
            name=name,
            account_id=self.account_id,
            region_name=self.region_name,
            wacl_id=wacl_id,
            scope=scope,
        )
        if arn in self.wacls or self._is_duplicate_name(name):
            raise WAFV2DuplicateItemException()
        new_wacl = FakeWebACL(
            name, arn, wacl_id, visibility_config, default_action, description, rules
        )
        self.wacls[arn] = new_wacl
        self.tag_resource(arn, tags)
        return new_wacl

    def delete_web_acl(self, name, _id):
        """
        The LockToken-parameter is not yet implemented
        """
        self.wacls = {
            arn: wacl
            for arn, wacl in self.wacls.items()
            if wacl.name != name and wacl.id != _id
        }

    def get_web_acl(self, name, _id) -> FakeWebACL:
        for wacl in self.wacls.values():
            if wacl.name == name and wacl.id == _id:
                return wacl
        raise WAFNonexistentItemException

    def list_web_acls(self):
        return [wacl.to_dict() for wacl in self.wacls.values()]

    def _is_duplicate_name(self, name):
        allWaclNames = set(wacl.name for wacl in self.wacls.values())
        return name in allWaclNames

    def list_rule_groups(self):
        return []

    def list_tags_for_resource(self, arn):
        """
        Pagination is not yet implemented
        """
        return self.tagging_service.list_tags_for_resource(arn)["Tags"]

    def tag_resource(self, arn, tags):
        self.tagging_service.tag_resource(arn, tags)

    def untag_resource(self, arn, tag_keys):
        self.tagging_service.untag_resource_using_names(arn, tag_keys)

    def update_web_acl(
        self, name, _id, default_action, rules, description, visibility_config
    ):
        """
        The following parameters are not yet implemented: LockToken, CustomResponseBodies, CaptchaConfig
        """
        acl = self.get_web_acl(name, _id)
        acl.update(default_action, rules, description, visibility_config)
        return acl.lock_token


wafv2_backends = BackendDict(
    WAFV2Backend, "waf-regional", additional_regions=["global"]
)
