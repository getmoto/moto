from __future__ import unicode_literals
from boto3 import Session
from pkg_resources import resource_filename
from moto.core import BaseBackend
from moto.utilities.utils import load_resource


checks_json = "resources/describe_trusted_advisor_checks.json"
ADVISOR_CHECKS = load_resource(resource_filename(__name__, checks_json))


class SupportBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(SupportBackend, self).__init__()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def describe_trusted_advisor_checks(self, language):
        # The checks are a static response
        checks = ADVISOR_CHECKS["checks"]
        return checks


support_backends = {}

# Only currently supported in us-east-1
support_backends["us-east-1"] = SupportBackend("us-east-1")
for region in Session().get_available_regions("support"):
    support_backends[region] = SupportBackend(region)
for region in Session().get_available_regions("support", partition_name="aws-us-gov"):
    support_backends[region] = SupportBackend(region)
for region in Session().get_available_regions("support", partition_name="aws-cn"):
    support_backends[region] = SupportBackend(region)
