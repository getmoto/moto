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
        self.check_status = {}

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def describe_trusted_advisor_checks(self, language):
        # The checks are a static response
        checks = ADVISOR_CHECKS["checks"]
        return checks

    def refresh_trusted_advisor_check(self, check_id):
        self.advance_check_status(check_id)
        status = {
            "status": {
                "checkId": check_id,
                "status": self.check_status[check_id],
                "millisUntilNextRefreshable": 123,
            }
        }
        return status

    def advance_check_status(self, check_id):
        """
        Fake an advancement through statuses on refreshing TA checks
        """
        if check_id not in self.check_status:
            self.check_status[check_id] = "none"

        elif self.check_status[check_id] == "none":
            self.check_status[check_id] = "enqueued"

        elif self.check_status[check_id] == "enqueued":
            self.check_status[check_id] = "processing"

        elif self.check_status[check_id] == "processing":
            self.check_status[check_id] = "success"

        elif self.check_status[check_id] == "success":
            self.check_status[check_id] = "abandoned"

        elif self.check_status[check_id] == "abandoned":
            self.check_status[check_id] = "none"


support_backends = {}

# Only currently supported in us-east-1
support_backends["us-east-1"] = SupportBackend("us-east-1")
for region in Session().get_available_regions("support"):
    support_backends[region] = SupportBackend(region)
for region in Session().get_available_regions("support", partition_name="aws-us-gov"):
    support_backends[region] = SupportBackend(region)
for region in Session().get_available_regions("support", partition_name="aws-cn"):
    support_backends[region] = SupportBackend(region)
