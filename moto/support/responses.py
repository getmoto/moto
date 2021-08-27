from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import support_backends
import json


class SupportResponse(BaseResponse):
    SERVICE_NAME = "support"

    @property
    def support_backend(self):
        return support_backends[self.region]

    def describe_trusted_advisor_checks(self):
        language = self._get_param("language")
        checks = self.support_backend.describe_trusted_advisor_checks(
            language=language,
        )

        return json.dumps({"checks": checks})

    def refresh_trusted_advisor_check(self):
        check_id = self._get_param("checkId")
        status = self.support_backend.refresh_trusted_advisor_check(check_id=check_id,)

        return json.dumps(status)

    def resolve_case(self):
        case_id = self._get_param("caseId")
        resolve_case_response = self.support_backend.resolve_case(case_id=case_id,)
        return json.dumps(resolve_case_response)

    def create_case(self):
        subject = self._get_param("subject")
        service_code = self._get_param("serviceCode")
        severity_code = self._get_param("severityCode")
        category_code = self._get_param("categoryCode")
        communication_body = self._get_param("communicationBody")
        cc_email_addresses = self._get_param("ccEmailAddresses")
        language = self._get_param("language")
        issue_type = self._get_param("issueType")
        attachment_set_id = self._get_param("attachmentSetId")
        create_case_response = self.support_backend.create_case(
            subject=subject,
            service_code=service_code,
            severity_code=severity_code,
            category_code=category_code,
            communication_body=communication_body,
            cc_email_addresses=cc_email_addresses,
            language=language,
            issue_type=issue_type,
            attachment_set_id=attachment_set_id,
        )

        return json.dumps(create_case_response)

    def describe_cases(self):
        case_id_list = self._get_param("caseIdList")
        display_id = self._get_param("displayId")
        after_time = self._get_param("afterTime")
        before_time = self._get_param("beforeTime")
        include_resolved_cases = self._get_param("includeResolvedCases", False)
        next_token = self._get_param("nextToken")
        max_results = self._get_int_param("maxResults")
        language = self._get_param("language")
        include_communications = self._get_param("includeCommunications", True)

        describe_cases_response = self.support_backend.describe_cases(
            case_id_list=case_id_list,
            display_id=display_id,
            after_time=after_time,
            before_time=before_time,
            include_resolved_cases=include_resolved_cases,
            next_token=next_token,
            max_results=max_results,
            language=language,
            include_communications=include_communications,
        )

        return json.dumps(describe_cases_response)
