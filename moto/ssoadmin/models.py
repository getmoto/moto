from .exceptions import ResourceNotFound

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict, unix_time
from uuid import uuid4


class AccountAssignment(BaseModel):
    def __init__(
        self,
        instance_arn,
        target_id,
        target_type,
        permission_set_arn,
        principal_type,
        principal_id,
    ):
        self.request_id = str(uuid4())
        self.instance_arn = instance_arn
        self.target_id = target_id
        self.target_type = target_type
        self.permission_set_arn = permission_set_arn
        self.principal_type = principal_type
        self.principal_id = principal_id
        self.created_date = unix_time()

    def to_json(self, include_creation_date=False):
        summary = {
            "TargetId": self.target_id,
            "TargetType": self.target_type,
            "PermissionSetArn": self.permission_set_arn,
            "PrincipalType": self.principal_type,
            "PrincipalId": self.principal_id,
        }
        if include_creation_date:
            summary["CreatedDate"] = self.created_date
        return summary


class SSOAdminBackend(BaseBackend):
    """Implementation of SSOAdmin APIs."""

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.account_assignments = list()

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_account_assignment(
        self,
        instance_arn,
        target_id,
        target_type,
        permission_set_arn,
        principal_type,
        principal_id,
    ):
        assignment = AccountAssignment(
            instance_arn,
            target_id,
            target_type,
            permission_set_arn,
            principal_type,
            principal_id,
        )
        self.account_assignments.append(assignment)
        return assignment.to_json()

    def delete_account_assignment(
        self,
        instance_arn,
        target_id,
        target_type,
        permission_set_arn,
        principal_type,
        principal_id,
    ):
        account = self._find_account(
            instance_arn,
            target_id,
            target_type,
            permission_set_arn,
            principal_type,
            principal_id,
        )
        self.account_assignments.remove(account)
        return account.to_json(include_creation_date=True)

    def _find_account(
        self,
        instance_arn,
        target_id,
        target_type,
        permission_set_arn,
        principal_type,
        principal_id,
    ):
        for account in self.account_assignments:
            instance_arn_match = account.instance_arn == instance_arn
            target_id_match = account.target_id == target_id
            target_type_match = account.target_type == target_type
            permission_set_match = account.permission_set_arn == permission_set_arn
            principal_type_match = account.principal_type == principal_type
            principal_id_match = account.principal_id == principal_id
            if (
                instance_arn_match
                and target_id_match
                and target_type_match
                and permission_set_match
                and principal_type_match
                and principal_id_match
            ):
                return account
        raise ResourceNotFound

    def list_account_assignments(self, instance_arn, account_id, permission_set_arn):
        """
        Pagination has not yet been implemented
        """
        account_assignments = []
        for assignment in self.account_assignments:
            if (
                assignment.instance_arn == instance_arn
                and assignment.target_id == account_id
                and assignment.permission_set_arn == permission_set_arn
            ):
                account_assignments.append(
                    {
                        "AccountId": account_id,
                        "PermissionSetArn": assignment.permission_set_arn,
                        "PrincipalType": assignment.principal_type,
                        "PrincipalId": assignment.principal_id,
                    }
                )
        return account_assignments


ssoadmin_backends = BackendDict(SSOAdminBackend, "sso")
