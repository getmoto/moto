"""Handles incoming securityhub requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import SecurityHubBackend, securityhub_backends


class SecurityHubResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="securityhub")

    @property
    def securityhub_backend(self) -> SecurityHubBackend:
        return securityhub_backends[self.current_account][self.region]

    def get_findings(self) -> str:
        raw_params = self._get_params()

        params = json.loads(next(iter(raw_params.keys()), "{}"))

        sort_criteria = params.get("SortCriteria", [])
        filters = params.get("Filters", {})
        next_token = params.get("NextToken", None)
        max_results = params.get("MaxResults", 100)

        result = self.securityhub_backend.get_findings(
            filters=filters,
            sort_criteria=sort_criteria,
            next_token=next_token,
            max_results=max_results,
        )

        return json.dumps(result)

    def batch_import_findings(self) -> str:
        raw_body = self.body
        if isinstance(raw_body, bytes):
            raw_body = raw_body.decode("utf-8")
        body = json.loads(raw_body)

        findings = body.get("Findings", [])

        failed_count, success_count, failed_findings = (
            self.securityhub_backend.batch_import_findings(
                findings=findings,
            )
        )

        return json.dumps(
            {
                "FailedCount": failed_count,
                "FailedFindings": [
                    {
                        "ErrorCode": finding.get("ErrorCode"),
                        "ErrorMessage": finding.get("ErrorMessage"),
                        "Id": finding.get("Id"),
                    }
                    for finding in failed_findings
                ],
                "SuccessCount": success_count,
            }
        )
