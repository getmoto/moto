import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from moto.core import BaseBackend, BackendDict, BaseModel

from .utils import make_arn_for_wacl
from .exceptions import WAFV2DuplicateItemException, WAFNonexistentItemException
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.moto_api._internal import mock_random
from moto.utilities.tagging_service import TaggingService
from collections import OrderedDict

if TYPE_CHECKING:
    from moto.apigateway.models import Stage


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
        self,
        name: str,
        arn: str,
        wacl_id: str,
        visibility_config: Dict[str, Any],
        default_action: Dict[str, Any],
        description: Optional[str],
        rules: List[Dict[str, Any]],
    ):
        self.name = name
        self.created_time = iso_8601_datetime_with_milliseconds()
        self.id = wacl_id
        self.arn = arn
        self.description = description or ""
        self.capacity = 3
        self.rules = rules
        self.visibility_config = visibility_config
        self.default_action = default_action
        self.lock_token = str(mock_random.uuid4())[0:6]

    def update(
        self,
        default_action: Optional[Dict[str, Any]],
        rules: Optional[List[Dict[str, Any]]],
        description: Optional[str],
        visibility_config: Optional[Dict[str, Any]],
    ) -> None:
        if default_action is not None:
            self.default_action = default_action
        if rules is not None:
            self.rules = rules
        if description is not None:
            self.description = description
        if visibility_config is not None:
            self.visibility_config = visibility_config
        self.lock_token = str(mock_random.uuid4())[0:6]

    def to_dict(self) -> Dict[str, Any]:
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

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.wacls: Dict[str, FakeWebACL] = OrderedDict()
        self.tagging_service = TaggingService()
        # TODO: self.load_balancers = OrderedDict()

    def associate_web_acl(self, web_acl_arn: str, resource_arn: str) -> None:
        """
        Only APIGateway Stages can be associated at the moment.
        """
        if web_acl_arn not in self.wacls:
            raise WAFNonexistentItemException
        stage = self._find_apigw_stage(resource_arn)
        if stage:
            stage.web_acl_arn = web_acl_arn

    def disassociate_web_acl(self, resource_arn: str) -> None:
        stage = self._find_apigw_stage(resource_arn)
        if stage:
            stage.web_acl_arn = None

    def get_web_acl_for_resource(self, resource_arn: str) -> Optional[FakeWebACL]:
        stage = self._find_apigw_stage(resource_arn)
        if stage and stage.web_acl_arn is not None:
            wacl_arn = stage.web_acl_arn
            return self.wacls.get(wacl_arn)
        return None

    def _find_apigw_stage(self, resource_arn: str) -> Optional["Stage"]:  # type: ignore
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
        self,
        name: str,
        visibility_config: Dict[str, Any],
        default_action: Dict[str, Any],
        scope: str,
        description: str,
        tags: List[Dict[str, str]],
        rules: List[Dict[str, Any]],
    ) -> FakeWebACL:
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

    def delete_web_acl(self, name: str, _id: str) -> None:
        """
        The LockToken-parameter is not yet implemented
        """
        self.wacls = {
            arn: wacl
            for arn, wacl in self.wacls.items()
            if wacl.name != name and wacl.id != _id
        }

    def get_web_acl(self, name: str, _id: str) -> FakeWebACL:
        for wacl in self.wacls.values():
            if wacl.name == name and wacl.id == _id:
                return wacl
        raise WAFNonexistentItemException

    def list_web_acls(self) -> List[Dict[str, Any]]:
        return [wacl.to_dict() for wacl in self.wacls.values()]

    def _is_duplicate_name(self, name: str) -> bool:
        allWaclNames = set(wacl.name for wacl in self.wacls.values())
        return name in allWaclNames

    def list_rule_groups(self) -> List[Any]:
        return []

    def list_tags_for_resource(self, arn: str) -> List[Dict[str, str]]:
        """
        Pagination is not yet implemented
        """
        return self.tagging_service.list_tags_for_resource(arn)["Tags"]

    def tag_resource(self, arn: str, tags: List[Dict[str, str]]) -> None:
        self.tagging_service.tag_resource(arn, tags)

    def untag_resource(self, arn: str, tag_keys: List[str]) -> None:
        self.tagging_service.untag_resource_using_names(arn, tag_keys)

    def update_web_acl(
        self,
        name: str,
        _id: str,
        default_action: Optional[Dict[str, Any]],
        rules: Optional[List[Dict[str, Any]]],
        description: Optional[str],
        visibility_config: Optional[Dict[str, Any]],
    ) -> str:
        """
        The following parameters are not yet implemented: LockToken, CustomResponseBodies, CaptchaConfig
        """
        acl = self.get_web_acl(name, _id)
        acl.update(default_action, rules, description, visibility_config)
        return acl.lock_token


wafv2_backends = BackendDict(
    WAFV2Backend, "waf-regional", additional_regions=["global"]
)
