from __future__ import unicode_literals
from boto3 import Session
from pkg_resources import resource_filename
from moto.core import BaseBackend
from moto.utilities.utils import load_resource
import datetime
import random


checks_json = "resources/describe_trusted_advisor_checks.json"
ADVISOR_CHECKS = load_resource(resource_filename(__name__, checks_json))


class SupportBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(SupportBackend, self).__init__()
        self.region_name = region_name
        self.check_status = {}
        self.case_id = {}
        self.case_severities = {}

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

    def advance_case_status(self, case_id):
        """
        Fake an advancement through case statuses
        """
        if case_id not in self.case_id:
            self.case_id[case_id] = "opened"

        elif self.case_id[case_id] == "opened":
            self.case_id[case_id] = "pending-customer-action"

        elif self.case_id[case_id] == "pending-customer-action":
            self.case_id[case_id] = "reopened"

        elif self.case_id[case_id] == "reopened":
            self.case_id[case_id] = "resolved"

        elif self.case_id[case_id] == "resolved":
            self.case_id[case_id] = "unassigned"

        elif self.case_id[case_id] == "unassigned":
            self.case_id[case_id] = "work-in-progress"

        elif self.case_id[case_id] == "work-in-progress":
            self.case_id[case_id] = "opened"

    def advance_case_severity_codes(self, case_id):
        """
        Fake an advancement through case status severities
        """
        if case_id not in self.case_severities:
            self.case_severities[case_id] = "low"

        elif self.case_severities[case_id] == "low":
            self.case_severities[case_id] = "normal"

        elif self.case_severities[case_id] == "normal":
            self.case_severities[case_id] = "high"

        elif self.case_severities[case_id] == "high":
            self.case_severities[case_id] = "urgent"

        elif self.case_severities[case_id] == "urgent":
            self.case_severities[case_id] = "critical"

        elif self.case_severities[case_id] == "critical":
            self.case_severities[case_id] = "low"

    def resolve_case(self, case_id):
        self.advance_case_status(case_id)

        initial_case_status = self.case_id[case_id]
        resolved_case = {
            "initialCaseStatus": initial_case_status,
            "finalCaseStatus": "resolved",
        }

        return resolved_case

    def create_case(
        self,
        subject,
        service_code,
        severity_code,
        category_code,
        communication_body,
        cc_email_addresses,
        language,
        issue_type,
        attachment_set_id,
    ):
        # Random case ID
        random_case_id = "".join(
            random.choice("0123456789ABCDEFGHIJKLMabcdefghijklm") for i in range(16)
        )
        case_id = "case-12345678910-2020-%s" % random_case_id
        return {"caseId": case_id}

    def describe_cases(
        self,
        case_id_list,
        display_id,
        after_time,
        before_time,
        include_resolved_cases,
        next_token,
        max_results,
        language,
        include_communications,
    ):
        cases = []

        support_user = "moto_user"
        now_time_format = (str(datetime.datetime.now().isoformat()),)

        for case in case_id_list:
            self.advance_case_status(case)
            self.advance_case_severity_codes(case)
            formatted_case = {
                "caseId": case,
                "displayId": display_id,
                "subject": "case subject",
                "status": self.case_id[case],
                "serviceCode": "1",
                "categoryCode": "2",
                "severityCode": self.case_severities[case],
                "submittedBy": support_user,
                "timeCreated": str(datetime.datetime.now().isoformat()),
                "ccEmailAddresses": ["%s@moto.com" % support_user,],
                "language": language,
            }

            if include_communications:
                communications = {
                    "recentCommunications": {
                        "communications": [
                            {
                                "caseId": case,
                                "body": "this is a body response.",
                                "submittedBy": support_user,
                                "timeCreated": now_time_format,
                                "attachmentSet": [
                                    {
                                        "attachmentId": "attachment-id-01",
                                        "fileName": "support_file.txt",
                                    },
                                ],
                            }
                        ],
                        "nextToken": next_token,
                    }
                }
                formatted_case.update(communications)

            if (
                include_resolved_cases is False
                and formatted_case["status"] == "resolved"
            ):
                continue

            cases.append(formatted_case)
        case_values = {"cases": cases}
        case_values.update({"nextToken": next_token})

        return case_values


support_backends = {}

# Only currently supported in us-east-1
support_backends["us-east-1"] = SupportBackend("us-east-1")
for region in Session().get_available_regions("support"):
    support_backends[region] = SupportBackend(region)
for region in Session().get_available_regions("support", partition_name="aws-us-gov"):
    support_backends[region] = SupportBackend(region)
for region in Session().get_available_regions("support", partition_name="aws-cn"):
    support_backends[region] = SupportBackend(region)
