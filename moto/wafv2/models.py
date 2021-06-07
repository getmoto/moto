from __future__ import unicode_literals

import uuid

from boto3 import Session

from moto.core import BaseBackend, BaseModel
from moto.wafv2 import utils
from moto.wafv2.utils import make_webacl_arn

US_EAST_1_REGION = "us-east-1"
GLOBAL_REGION = "global"


class WAFV2Backend(BaseBackend):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_Types_AWS_WAFV2.html
    """

    def __init__(self, region_name=None):
        super(WAFV2Backend, self).__init__()
        self.region_name = region_name
        self.wacls = [WebACL("first-mock-webacl"), WebACL("second-mock-webacl")]

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)


class WebACL(BaseModel):
    def __init__(self, name="Mock-WebACL-name"):
        self.Id = str(uuid.uuid4())
        """
        The name must have 1-128 characters. Valid characters: A-Z, a-z, 0-9, - (hyphen), and _ (underscore).
        """
        self.Name = utils.create_test_name(name)
        self.ARN = make_webacl_arn(US_EAST_1_REGION, self.Name)
        self.Capacity = 3
        self.Description = "Mock WebACL named {0}".format(self.Name)
        self.VisibilityConfig = VisibilityConfig(self.Name)
        """
        TODO: create classes for the below fields:
        """
        self.DefaultAction = {"Allow": {}}

    def to_dict(self):
        return {
            "Id": self.Id,
            "Name": self.Name,
            "ARN": self.ARN,
            "Capacity": self.Capacity,
            "Description": self.Description,
            "VisibilityConfig": self.VisibilityConfig.__dict__,
        }


class VisibilityConfig(BaseModel):
    """
    https://docs.aws.amazon.com/waf/latest/APIReference/API_VisibilityConfig.html
    """

    def __init__(self, metric_name):
        self.SampledRequestsEnabled = True
        self.CloudWatchMetricsEnabled = False
        self.MetricName = metric_name


wafv2_backends = {}
wafv2_backends["global"] = WAFV2Backend(GLOBAL_REGION)
for region in Session().get_available_regions("waf-regional"):
    wafv2_backends[region] = WAFV2Backend(region)
for region in Session().get_available_regions(
    "waf-regional", partition_name="aws-us-gov"
):
    wafv2_backends[region] = WAFV2Backend(region)
for region in Session().get_available_regions("waf-regional", partition_name="aws-cn"):
    wafv2_backends[region] = WAFV2Backend(region)
