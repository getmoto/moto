from uuid import uuid4
from boto3 import Session
from moto.core import BaseBackend, BaseModel
from moto.wafv2 import utils

# from moto.ec2.models import elbv2_backends
from .utils import make_arn_for_wacl, pascal_to_underscores_dict
from .exceptions import WAFV2DuplicateItemException
from moto.core.utils import iso_8601_datetime_with_milliseconds
import datetime
from collections import OrderedDict


US_EAST_1_REGION = "us-east-1"
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
        self.capacity = 3
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


class WAFV2Backend(BaseBackend):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_Operations_AWS_WAFV2.html
    """

    def __init__(self, region_name=None):
        super(WAFV2Backend, self).__init__()
        self.region_name = region_name
        self.wacls = OrderedDict()  # self.wacls[ARN] = FakeWacl
        # TODO: self.load_balancers = OrderedDict()

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

    def _is_duplicate_name(self, name):
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
