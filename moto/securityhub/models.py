"""SecurityHubBackend class with methods for supported APIs."""

import datetime
from typing import Any, Dict, List, Optional, Tuple

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.exceptions import RESTError
from moto.organizations.exceptions import AWSOrganizationsNotInUseException
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

    # Class-level variables to store organization-wide configuration
    _org_admin_account_id: Optional[str] = None
    _org_auto_enable: bool = False
    _org_auto_enable_standards: str = "DEFAULT"
    _org_configuration: Dict[str, Any] = {
        "ConfigurationType": "LOCAL",
        "Status": "ENABLED",
        "StatusMessage": "",
    }

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.findings: List[Finding] = []
        self.region_name = region_name

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
        """
        from moto.organizations.models import organizations_backends

        # Organizations is a global service, so we use 'aws' as the region
        org_backend = organizations_backends[self.account_id]["aws"]

        try:
            org = org_backend.describe_organization()
        except RESTError:
            raise AWSOrganizationsNotInUseException()

        # Verify this is being called by the management account
        if self.account_id != org["Organization"]["MasterAccountId"]:
            raise RESTError(
                "AccessDeniedException",
                "You do not have sufficient access to perform this action.",
            )

        # Verify the admin account exists in the organization
        try:
            org_backend.get_account_by_id(admin_account_id)
        except RESTError:
            raise RESTError(
                "ValidationException",
                f"Account {admin_account_id} is not part of organization {org['Organization']['Id']}",
            )

        SecurityHubBackend._org_admin_account_id = admin_account_id

    def update_organization_configuration(
        self,
        auto_enable: bool,
        auto_enable_standards: Optional[str] = None,
        organization_configuration: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Updates Security Hub configuration settings for an organization.
        Can only be called by the Security Hub administrator account.
        """
        from moto.organizations.models import organizations_backends

        # Organizations is a global service, so we use 'aws' as the region
        org_backend = organizations_backends[self.account_id]["aws"]

        try:
            org = org_backend.describe_organization()
        except RESTError:
            raise AWSOrganizationsNotInUseException()

        # Verify this is being called by the admin account
        if not SecurityHubBackend._org_admin_account_id:
            raise RESTError(
                "AccessDeniedException", "No administrator account has been designated"
            )

        if self.account_id != SecurityHubBackend._org_admin_account_id:
            raise RESTError(
                "AccessDeniedException",
                "You do not have sufficient access to perform this action.",
            )

        # If organization_configuration is provided, validate and apply it
        if organization_configuration:
            config_type = organization_configuration.get("ConfigurationType")
            if config_type not in ["CENTRAL", "LOCAL"]:
                raise RESTError(
                    "ValidationException",
                    "ConfigurationType must be either CENTRAL or LOCAL",
                )

            status = organization_configuration.get("Status")
            if status not in ["PENDING", "ENABLED", "FAILED"]:
                raise RESTError(
                    "ValidationException",
                    "Status must be one of PENDING, ENABLED, or FAILED",
                )

            # If ConfigurationType is CENTRAL, enforce restrictions
            if config_type == "CENTRAL":
                if auto_enable:
                    raise RESTError(
                        "ValidationException",
                        "AutoEnable must be false when ConfigurationType is CENTRAL",
                    )
                if auto_enable_standards != "NONE":
                    raise RESTError(
                        "ValidationException",
                        "AutoEnableStandards must be NONE when ConfigurationType is CENTRAL",
                    )

            SecurityHubBackend._org_configuration = organization_configuration

        # Update auto_enable setting
        SecurityHubBackend._org_auto_enable = auto_enable

        # Update auto_enable_standards if provided
        if auto_enable_standards is not None:
            if auto_enable_standards not in ["NONE", "DEFAULT"]:
                raise RESTError(
                    "ValidationException",
                    "AutoEnableStandards must be either NONE or DEFAULT",
                )
            SecurityHubBackend._org_auto_enable_standards = auto_enable_standards

    def get_administrator_account(self) -> Dict[str, Any]:
        """
        Returns details about the Security Hub administrator account for the current member account.
        Can be used by both member accounts that are managed using Organizations and accounts that were invited manually.
        """
        if not SecurityHubBackend._org_admin_account_id:
            return {}

        from moto.organizations.models import organizations_backends

        # Organizations is a global service, so we use 'aws' as the region
        org_backend = organizations_backends[self.account_id]["aws"]

        try:
            org = org_backend.describe_organization()
            management_account_id = org["Organization"]["MasterAccountId"]
        except RESTError:
            return {}

        # Return empty response if this is the management account or admin account
        if (
            self.account_id == management_account_id
            or self.account_id == SecurityHubBackend._org_admin_account_id
        ):
            return {}

        # Return administrator details for member accounts
        return {
            "Administrator": {
                "AccountId": SecurityHubBackend._org_admin_account_id,
                "MemberStatus": "ENABLED",
                "InvitationId": f"invitation-{SecurityHubBackend._org_admin_account_id}",
                "InvitedAt": datetime.datetime.now().isoformat(),
            }
        }

    def describe_organization_configuration(self) -> Dict[str, Any]:
        """
        Returns details about the Security Hub organization configuration.
        Only the Security Hub administrator account can invoke this operation.
        """
        from moto.organizations.models import organizations_backends

        # Organizations is a global service, so we use 'aws' as the region
        org_backend = organizations_backends[self.account_id]["aws"]

        try:
            org = org_backend.describe_organization()
        except RESTError:
            raise AWSOrganizationsNotInUseException()

        # Verify this is being called by the admin account
        if not SecurityHubBackend._org_admin_account_id:
            raise RESTError(
                "AccessDeniedException", "No administrator account has been designated"
            )

        if self.account_id != SecurityHubBackend._org_admin_account_id:
            raise RESTError(
                "AccessDeniedException",
                "You do not have sufficient access to perform this action.",
            )

        return {
            "AutoEnable": SecurityHubBackend._org_auto_enable,
            "MemberAccountLimitReached": False,
            "AutoEnableStandards": SecurityHubBackend._org_auto_enable_standards,
            "OrganizationConfiguration": SecurityHubBackend._org_configuration,
        }


securityhub_backends = BackendDict(SecurityHubBackend, "securityhub")
