from __future__ import unicode_literals
from uuid import UUID, uuid4
from boto3 import Session
from moto.core import BaseBackend, BaseModel
from moto.wafv2 import utils
# from moto.ec2.models import elbv2_backends
from .utils import make_arn_for_wacl
from .exceptions import (
    WAFV2DuplicateItemException,
)
from moto.core.utils import (
    camelcase_to_underscores,
    underscores_to_camelcase,
    iso_8601_datetime_with_milliseconds,
)
import datetime
from collections import OrderedDict
from typing import List,Tuple


US_EAST_1_REGION = "us-east-1"
GLOBAL_REGION = "global"


class VisibilityConfig(BaseModel):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_VisibilityConfig.html
    """

    def __init__(self, MetricName: str, SampledRequestsEnabled: dict, CloudWatchMetricsEnabled: dict):
        self.cloud_watch_metrics_enabled = CloudWatchMetricsEnabled
        self.metric_name = MetricName
        self.sampled_requests_enabled = SampledRequestsEnabled


class DefaultAction(BaseModel):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_DefaultAction.html
    """

    def __init__(self, Allow: dict = {}, Block: dict = {}):
        self.allow = Allow
        self.block = Block


# TODO: Add remaining properties
class FakeWebACL(BaseModel):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_WebACL.html
    """

    def __init__(self, name: str, arn: str, id: str, visibility_config: dict, default_action: dict):
        self.name = name if name else utils.create_test_name("Mock-WebACL-name")
        self.created_time = iso_8601_datetime_with_milliseconds(datetime.datetime.now())
        self.id = id
        self.arn = arn
        self.description = "Mock WebACL named {0}".format(self.name)
        self.capacity = 3
        self.VisibilityConfig = VisibilityConfig(**visibility_config)
        self.DefaultAction = DefaultAction(**default_action)

    def to_dict(self) -> dict:
        # Format for summary https://docs.aws.amazon.com/waf/latest/APIReference/API_CreateWebACL.html (response syntax section)
        return {
            "ARN": self.arn,
            "Description": self.description,
            "Id": self.id,
            "LockToken": "Not Implemented",
            "Name": self.name
        }


class WAFV2Backend(BaseBackend):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_Operations_AWS_WAFV2.html
    """

    def __init__(self, region_name=None):
        super(WAFV2Backend, self).__init__()
        self.region_name = region_name
        self.wacls = OrderedDict[str,FakeWebACL]()  # self.wacls[ARN] = FakeWacl
        # TODO: self.load_balancers = OrderedDict()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_web_acl(self, name: str, visibility_config: dict, default_action: dict, scope:str) -> FakeWebACL:
        wacl_id = str(uuid4())
        arn = make_arn_for_wacl(name=name, region_name=self.region_name, id=wacl_id, scope=scope)
        if arn in self.wacls or self._is_duplicate_name(name):
            raise WAFV2DuplicateItemException()
        new_wacl = FakeWebACL(name, arn, wacl_id, visibility_config, default_action)
        self.wacls[arn] = new_wacl
        return new_wacl

    def list_web_acls(self) -> List[dict]:
        return [wacl.to_dict() for wacl in self.wacls.values()]

    def _is_duplicate_name(self, name: str) -> bool:
        allWaclNames = set(wacl.name for wacl in self.wacls.values())
        return name in allWaclNames

    # TODO: This is how you link wacl to ALB
    # @property
    # def elbv2_backend(self):
    #     """
    #     EC2 backend

    #     :return: EC2 Backend
    #     :rtype: moto.ec2.models.EC2Backend
    #     """
    #     return ec2_backends[self.region_name]


wafv2_backends = {}
wafv2_backends[GLOBAL_REGION] = WAFV2Backend(GLOBAL_REGION)  # never used? cloudfront is global and uses us-east-1
for region in Session().get_available_regions("waf-regional"):
    wafv2_backends[region] = WAFV2Backend(region)
for region in Session().get_available_regions("waf-regional", partition_name="aws-us-gov"):
    wafv2_backends[region] = WAFV2Backend(region)
for region in Session().get_available_regions("waf-regional", partition_name="aws-cn"):
    wafv2_backends[region] = WAFV2Backend(region)
