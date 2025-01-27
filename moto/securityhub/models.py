"""SecurityHubBackend class with methods for supported APIs."""

from typing import Any, Dict, List, Optional, Tuple

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.securityhub.exceptions import InvalidInputException


class Finding(BaseModel):
    def __init__(self, finding_id: str, finding_data: Dict[str, Any]):
        self.id = finding_id
        self.data = finding_data

        # # Ensure required fields exist with default values
        # self.data.setdefault("Id", finding_id)
        # self.data.setdefault("AwsAccountId", "")
        # self.data.setdefault("CreatedAt", "")
        # self.data.setdefault("Description", "")
        # self.data.setdefault("GeneratorId", "")
        # self.data.setdefault("ProductArn", "")
        # self.data.setdefault("Title", "")
        # self.data.setdefault("Types", [])

        # # Required but with nested structure
        # self.data.setdefault("Severity", {"Label": ""})
        # self.data.setdefault("Resources", [])

        # # Optional fields with default values
        # self.data.setdefault("UpdatedAt", "")
        # self.data.setdefault("FirstObservedAt", "")
        # self.data.setdefault("LastObservedAt", "")
        # self.data.setdefault("Confidence", 0)
        # self.data.setdefault("Criticality", 0)
        # self.data.setdefault("RecordState", "ACTIVE")
        # self.data.setdefault("WorkflowState", "NEW")
        # self.data.setdefault("VerificationState", "UNKNOWN")

    # def _get_sortable_value(self, field: str) -> Any:
    #     """Get a value from the finding data using dot notation"""
    #     if "." in field:
    #         parent, child = field.split(".")
    #         return self.data.get(parent, {}).get(child)
    #     elif "/" in field:
    #         parent, child = field.split("/")
    #         return self.data.get(parent, {}).get(child)
    #     return self.data.get(field)

    def as_dict(self) -> Dict[str, Any]:
        return self.data


class SecurityHubBackend(BaseBackend):
    """Implementation of SecurityHub APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.findings: List[Finding] = []

    def get_findings(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_criteria: Optional[List[Dict[str, str]]] = None,
        next_token: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Gets findings from SecurityHub based on provided filters and sorting criteria"""
        findings = self.findings

        # Validate max_results if provided
        if max_results is not None:
            try:
                max_results = int(max_results)
                if max_results < 1 or max_results > 100:
                    raise InvalidInputException(
                        op="GetFindings",
                        msg="MaxResults must be a number between 1 and 100",
                    )
            except ValueError:
                raise InvalidInputException(
                    op="GetFindings", msg="MaxResults must be a number greater than 0"
                )

        # Handle pagination
        if next_token:
            start_idx = int(next_token)
        else:
            start_idx = 0

        end_idx = len(findings)
        if max_results:
            end_idx = min(start_idx + max_results, len(findings))

        paginated_findings = findings[start_idx:end_idx]

        # Generate next token if there are more results
        next_token = str(end_idx) if end_idx < len(findings) else None

        return {
            "Findings": [f.as_dict() for f in paginated_findings],
            "NextToken": next_token,
        }

    def batch_import_findings(
        self, findings: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        Import findings in batch to SecurityHub.

        Args:
            findings: List of finding dictionaries to import

        Returns:
            Tuple of (failed_count, success_count, failed_findings)
        """
        failed_count = 0
        success_count = 0
        failed_findings = []

        for finding_data in findings:
            try:
                if (
                    not isinstance(finding_data["Resources"], list)
                    or len(finding_data["Resources"]) == 0
                ):
                    raise InvalidInputException(
                        op="BatchImportFindings",
                        msg="Finding must contain at least one resource in the Resources array",
                    )

                finding_id = finding_data["Id"]

                existing_finding = next(
                    (f for f in self.findings if f.id == finding_id), None
                )

                if existing_finding:
                    # Update existing finding
                    existing_finding.data.update(finding_data)
                else:
                    # Create new finding
                    new_finding = Finding(finding_id, finding_data)
                    self.findings.append(new_finding)

                success_count += 1

            except Exception as e:
                failed_count += 1
                failed_findings.append(
                    {
                        "Id": finding_data.get("Id", ""),
                        "ErrorCode": "InvalidInput",
                        "ErrorMessage": str(e),
                    }
                )

        return failed_count, success_count, failed_findings


securityhub_backends = BackendDict(SecurityHubBackend, "securityhub")
