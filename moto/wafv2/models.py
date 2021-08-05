from __future__ import unicode_literals
from uuid import uuid4
from boto3 import Session
from moto.core import BaseBackend, BaseModel
from moto.wafv2 import utils

from .utils import (
    make_arn_for_wacl,
    pascal_to_underscores_dict,
    underscores_to_pascal_dict,
)
from .exceptions import WAFV2DuplicateItemException, WAFNonexistentItemException
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.elbv2.models import elbv2_backends
import datetime
from collections import OrderedDict


GLOBAL_REGION = "global"


class VisibilityConfig(BaseModel):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_VisibilityConfig.html
    """

    def __init__(
        self, metric_name, sampled_requests_enabled, cloud_watch_metrics_enabled
    ):
        self.cloud_watch_metrics_enabled = cloud_watch_metrics_enabled
        self.metric_name = metric_name
        self.sampled_requests_enabled = sampled_requests_enabled


class DefaultAction(BaseModel):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_DefaultAction.html
    """

    def __init__(self, allow={}, block={}):
        self.allow = allow
        self.block = block


# TODO: Add remaining properties


class FakeWebACL(BaseModel):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_WebACL.html
    """

    def __init__(self, name, arn, id, visibility_config, default_action):
        self.name = name if name else utils.create_test_name("Mock-WebACL-name")
        self.created_time = iso_8601_datetime_with_milliseconds(datetime.datetime.now())
        self.id = id
        self.arn = arn
        self.description = "Mock WebACL named {0}".format(self.name)
        self.capacity = "Not Implemented"
        self.visibility_config = VisibilityConfig(
            **pascal_to_underscores_dict(visibility_config)
        )
        self.default_action = DefaultAction(
            **pascal_to_underscores_dict(default_action)
        )

    def to_dict(self):
        # Format for summary https://docs.aws.amazon.com/waf/latest/APIReference/API_CreateWebACL.html (response syntax section)
        return {
            "ARN": self.arn,
            "Description": self.description,
            "Id": self.id,
            "LockToken": "Not Implemented",
            "Name": self.name,
        }

    def to_dict_long(self):
        # https://docs.aws.amazon.com/waf/latest/APIReference/API_GetWebACLForResource.html (response syntax section)
        return {
            "ARN": self.arn,
            "Description": self.description,
            "Id": self.id,
            "Name": self.name,
            "Capacity": self.capacity,
            "DefaultAction": underscores_to_pascal_dict(self.default_action.__dict__),
            "VisibilityConfig": underscores_to_pascal_dict(
                self.visibility_config.__dict__
            ),
        }


class WAFV2Backend(BaseBackend):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_Operations_AWS_WAFV2.html
    """

    def __init__(self, region_name=None):
        super(WAFV2Backend, self).__init__()
        self.region_name = region_name
        self.wacls = OrderedDict()  # self.wacls[ARN] = FakeWacl
        self.alb_to_wacl = {}  # self.alb_to_wacl[alb_ARN] = wacl_arn

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_web_acl(self, name, visibility_config, default_action, scope):
        wacl_id = str(uuid4())
        arn = make_arn_for_wacl(
            name=name, region_name=self.region_name, id=wacl_id, scope=scope
        )
        if arn in self.wacls or self._is_duplicate_name(name):
            raise WAFV2DuplicateItemException()
        new_wacl = FakeWebACL(name, arn, wacl_id, visibility_config, default_action)
        self.wacls[arn] = new_wacl
        return new_wacl

    def list_web_acls(self):
        return [wacl.to_dict() for wacl in self.wacls.values()]

    # A wacl can be on many ALBS, but an ALB can only have one wacl
    def associate_web_acl(self, resource_arn, web_acl_arn):
        # verify valid ALB and valid wacl
        if (
            resource_arn not in self.elbv2_backend.load_balancers
            or web_acl_arn not in self.wacls
        ):
            raise WAFNonexistentItemException()
        self.alb_to_wacl[resource_arn] = web_acl_arn

    def disassociate_web_acl(self, resource_arn):
        if resource_arn not in self.elbv2_backend.load_balancers:
            raise WAFNonexistentItemException()
        self.alb_to_wacl.pop(resource_arn, None)

    def get_web_acl_for_resource(self, resource_arn):
        self._updateActiveELBv2s()
        if resource_arn not in self.elbv2_backend.load_balancers:
            raise WAFNonexistentItemException()
        if resource_arn not in self.alb_to_wacl:
            return None
        return self.wacls[self.alb_to_wacl[resource_arn]].to_dict_long()

    def _is_duplicate_name(self, name):
        allWaclNames = set(wacl.name for wacl in self.wacls.values())
        return name in allWaclNames

    # If you deleted a load balancer in an elbv2, then it should also be deleted here
    def _updateActiveELBv2s(self):
        for alb_arn in self.alb_to_wacl:
            if alb_arn not in self.elbv2_backend.load_balancers:
                self.alb_to_wacl.pop(alb_arn, None)

    @property
    def elbv2_backend(self):
        """
        elbv2 backend

        :return: elbv2 Backend
        :rtype: moto.elbv2.models.ELBv2Backend
        """
        return elbv2_backends[self.region_name]


wafv2_backends = {}
wafv2_backends[GLOBAL_REGION] = WAFV2Backend(
    GLOBAL_REGION
)  # never used? cloudfront is global and uses us-east-1
for region in Session().get_available_regions("waf-regional"):
    wafv2_backends[region] = WAFV2Backend(region)
for region in Session().get_available_regions(
    "waf-regional", partition_name="aws-us-gov"
):
    wafv2_backends[region] = WAFV2Backend(region)
for region in Session().get_available_regions("waf-regional", partition_name="aws-cn"):
    wafv2_backends[region] = WAFV2Backend(region)
