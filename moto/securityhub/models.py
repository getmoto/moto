"""SecurityHubBackend class with methods for supported APIs."""

import datetime
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

    org_admin_account_details = {
        "admin_account_id": None,
        "auto_enable": False,
        "auto_enable_standards": "DEFAULT",
        "organization_configuration": {
            "ConfigurationType": "LOCAL",
            "Status": "ENABLED",
            "StatusMessage": "",
        },
    }

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.findings: List[Finding] = []

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
        SecurityHubBackend.org_admin_account_details["admin_account_id"] = (
            admin_account_id
        )

    def update_organization_configuration(
        self,
        auto_enable: bool,
        auto_enable_standards: Optional[str] = None,
        organization_configuration: Optional[Dict[str, Any]] = None,
    ) -> None:
        SecurityHubBackend.org_admin_account_details["auto_enable"] = auto_enable

        if auto_enable_standards is not None:
            SecurityHubBackend.org_admin_account_details["auto_enable_standards"] = (
                auto_enable_standards
            )

        if organization_configuration is not None:
            SecurityHubBackend.org_admin_account_details[
                "organization_configuration"
            ] = organization_configuration

    def get_administrator_account(self) -> Dict[str, Any]:
        admin_account_id = SecurityHubBackend.org_admin_account_details[
            "admin_account_id"
        ]
        auto_enable = SecurityHubBackend.org_admin_account_details["auto_enable"]

        if not admin_account_id:
            return {}

        if self.account_id == admin_account_id:
            pass
        elif not auto_enable:
            return {}

        return {
            "Administrator": {
                "AccountId": admin_account_id,
                "MemberStatus": "ENABLED",
                "InvitationId": f"invitation-{admin_account_id}",
                "InvitedAt": datetime.datetime.now().isoformat(),
            }
        }

    def describe_organization_configuration(self) -> Dict[str, Any]:
        return {
            "AutoEnable": SecurityHubBackend.org_admin_account_details["auto_enable"],
            "MemberAccountLimitReached": False,
            "AutoEnableStandards": SecurityHubBackend.org_admin_account_details[
                "auto_enable_standards"
            ],
            "OrganizationConfiguration": SecurityHubBackend.org_admin_account_details[
                "organization_configuration"
            ],
        }


securityhub_backends = BackendDict(SecurityHubBackend, "securityhub")
