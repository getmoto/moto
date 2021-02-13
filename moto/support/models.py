from __future__ import unicode_literals
from boto3 import Session
from moto.core import BaseBackend
import json


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
        trusted_advisor_checks_file = open(
            "moto/support/resources/describe_trusted_advisor_checks.json"
        )
        json_file = json.load(trusted_advisor_checks_file)
        checks = json_file["checks"]
        return checks


support_backends = {}

# Only currently supported in us-east-1
support_backends["us-east-1"] = SupportBackend()
for region in Session().get_available_regions("support"):
    support_backends[region] = SupportBackend()
for region in Session().get_available_regions("support", partition_name="aws-us-gov"):
    support_backends[region] = SupportBackend()
for region in Session().get_available_regions("support", partition_name="aws-cn"):
    support_backends[region] = SupportBackend()
