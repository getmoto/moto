from __future__ import unicode_literals
from boto3 import Session
from pkg_resources import resource_filename
from moto.core import BaseBackend
from moto.utilities.utils import load_resource
import datetime
import random


checks_json = "resources/describe_trusted_advisor_checks.json"
ADVISOR_CHECKS = load_resource(resource_filename(__name__, checks_json))


class SupportCase(object):
    def __init__(self, **kwargs):
        self.case_id = kwargs.get("case_id")
        self.display_id = "foo_display_id"
        self.subject = kwargs.get("subject")
        self.status = "opened"
        self.service_code = kwargs.get("service_code")
        self.category_code = kwargs.get("category_code")
        self.severity_code = kwargs.get("severity_code")
        self.submitted_by = "moto@moto.com"
        self.time_created = self.get_datetime()
        self.attachment_set_id = kwargs.get("attachment_set_id")
        self.communication_body = kwargs.get("communication_body")
        self.language = kwargs.get("language")
        self.cc_email_addresses = kwargs.get("cc_email_addresses")
        self.communications = {
            "recentCommunications": {
                "communications": [
                    {
                        "caseId": self.case_id,
                        "body": self.communication_body,
                        "submittedBy": self.submitted_by,
                        "timeCreated": self.get_datetime(),
                        "attachmentSet": [
                            {
                                "attachmentId": self.attachment_set_id,
                                "fileName": "support_file.txt",
                            },
                        ],
                    }
                ],
                "nextToken": "foo_next_token",
            }
        }

    def get_datetime(self):
        return str(datetime.datetime.now().isoformat())


class SupportBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(SupportBackend, self).__init__()
        self.region_name = region_name
        self.check_status = {}
        self.cases = {}

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

        if self.cases[case_id].status == "opened":
            self.cases[case_id].status = "pending-customer-action"

        elif self.cases[case_id].status == "pending-customer-action":
            self.cases[case_id].status = "reopened"

        elif self.cases[case_id].status == "reopened":
            self.cases[case_id].status = "resolved"

        elif self.cases[case_id].status == "resolved":
            self.cases[case_id].status = "unassigned"

        elif self.cases[case_id].status == "unassigned":
            self.cases[case_id].status = "work-in-progress"

        elif self.cases[case_id].status == "work-in-progress":
            self.cases[case_id].status = "opened"

    def advance_case_severity_codes(self, case_id):
        """
        Fake an advancement through case status severities
        """
        if self.cases[case_id].severity_code == "low":
            self.cases[case_id].severity_code = "normal"

        elif self.cases[case_id].severity_code == "normal":
            self.cases[case_id].severity_code = "high"

        elif self.cases[case_id].severity_code == "high":
            self.cases[case_id].severity_code = "urgent"

        elif self.cases[case_id].severity_code == "urgent":
            self.cases[case_id].severity_code = "critical"

        elif self.cases[case_id].severity_code == "critical":
            self.cases[case_id].severity_code = "low"

    def resolve_case(self, case_id):
        self.advance_case_status(case_id)

        resolved_case = {
            "initialCaseStatus": self.cases[case_id].status,
            "finalCaseStatus": "resolved",
        }

        return resolved_case

    # persist case details to self.cases
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
        case = SupportCase(
            case_id=case_id,
            subject=subject,
            service_code=service_code,
            severity_code=severity_code,
            category_code=category_code,
            communication_body=communication_body,
            cc_email_addresses=cc_email_addresses,
            language=language,
            attachment_set_id=attachment_set_id,
        )
        self.cases[case_id] = case

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
        requested_case_ids = case_id_list or self.cases.keys()

        for case in requested_case_ids:
            self.advance_case_status(case)
            self.advance_case_severity_codes(case)
            formatted_case = {
                "caseId": self.cases[case].case_id,
                "displayId": self.cases[case].display_id,
                "subject": self.cases[case].subject,
                "status": self.cases[case].status,
                "serviceCode": self.cases[case].service_code,
                "categoryCode": self.cases[case].category_code,
                "severityCode": self.cases[case].severity_code,
                "submittedBy": self.cases[case].submitted_by,
                "timeCreated": self.cases[case].time_created,
                "ccEmailAddresses": self.cases[case].cc_email_addresses,
                "language": self.cases[case].language,
            }

            if include_communications:
                formatted_case.update(self.cases[case].communications)

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
