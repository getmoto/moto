"""SecurityHubBackend class with methods for supported APIs."""

from typing import Any, Dict, List, Optional, Tuple

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.securityhub.exceptions import InvalidInputException
from moto.utilities.paginator import paginate


class Finding(BaseModel):
    def __init__(self, finding_id: str, finding_data: Dict[str, Any]):
        self.id = finding_id
        self.data = finding_data

    def as_dict(self) -> Dict[str, Any]:
        return self.data


class SecurityHubBackend(BaseBackend):
    """Implementation of SecurityHub APIs."""

    PAGINATION_MODEL = {
        "get_findings": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "Id",
            "fail_on_invalid_token": True,
        }
    }

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.findings: List[Finding] = []
        self.org_admin_account_id: Optional[str] = (
            None  # Only one admin account can exist
        )
        # Default organization configuration
        self.org_auto_enable: bool = False
        self.org_auto_enable_standards: str = "DEFAULT"
        self.org_configuration: Dict[str, Any] = {
            "ConfigurationType": "LOCAL",
            "Status": "ENABLED",
            "StatusMessage": "",
        }

    @paginate(pagination_model=PAGINATION_MODEL)
    def get_findings(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_criteria: Optional[List[Dict[str, str]]] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Returns findings based on optional filters and sort criteria.
        """
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

        findings = self.findings

        # TODO: Apply filters if provided
        # TODO: Apply sort criteria if provided

        return [f.as_dict() for f in findings]

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
                    existing_finding.data.update(finding_data)
                else:
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

    def enable_organization_admin_account(self, admin_account_id: str) -> None:
        """
        Designates the Security Hub administrator account for an organization.
        Can only be called by the organization management account.
        Only one admin account can be designated at a time.

        Args:
            admin_account_id: The AWS account identifier of the account to designate as the Security Hub administrator account.
        """
        self.org_admin_account_id = admin_account_id

    def update_organization_configuration(
        self,
        auto_enable: bool,
        auto_enable_standards: Optional[str] = None,
        organization_configuration: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Updates the configuration of the organization in Security Hub.
        Only the Security Hub administrator account can invoke this operation.

        Args:
            auto_enable: Whether to automatically enable Security Hub in new member accounts
                when they join the organization.
            auto_enable_standards: Whether to automatically enable Security Hub default standards
                in new member accounts. Values: "NONE" or "DEFAULT".
            organization_configuration: Information about the way an organization is configured.
        """
        self.org_auto_enable = auto_enable

        if auto_enable_standards is not None:
            self.org_auto_enable_standards = auto_enable_standards

        if organization_configuration is not None:
            self.org_configuration.update(organization_configuration)

    def get_administrator_account(self) -> Dict[str, Any]:
        """
        Provides the details for the Security Hub administrator account for the current member account.
        Can be used by both member accounts that are managed using Organizations and accounts that were invited manually.

        Returns:
            A dictionary containing the administrator account details.
        """
        print("org_admin_account_id", self.org_admin_account_id)
        if not self.org_admin_account_id:
            # No administrator account has been set
            return {}

        return {
            "Administrator": {
                "AccountId": self.org_admin_account_id,
                "MemberStatus": "ENABLED",
                # For organization members, InvitationId and InvitedAt are not applicable
                # but we include them with default values for consistency
                "InvitationId": f"7327d78c-{self.org_admin_account_id}",
                "InvitedAt": "2023-01-01T00:00:00.000Z",
            }
        }

    def describe_organization_configuration(self) -> Dict[str, Any]:
        """
        Returns the organization configuration for Security Hub.

        Returns:
            A dictionary containing the organization configuration details.
        """

        return {
            "AutoEnable": self.org_auto_enable,
            "MemberAccountLimitReached": False,  # Always false in moto implementation
            "AutoEnableStandards": self.org_auto_enable_standards,
            "OrganizationConfiguration": self.org_configuration,
        }


securityhub_backends = BackendDict(SecurityHubBackend, "securityhub")
