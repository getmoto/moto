from typing import Any, Dict, List

from moto.core import BaseBackend, BackendDict, BaseModel
from moto.core.utils import unix_time
from moto.moto_api._internal import mock_random as random
from moto.utilities.paginator import paginate
from .exceptions import ResourceNotFound
from .utils import PAGINATION_MODEL


class AccountAssignment(BaseModel):
    def __init__(
        self,
        instance_arn: str,
        target_id: str,
        target_type: str,
        permission_set_arn: str,
        principal_type: str,
        principal_id: str,
    ):
        self.request_id = str(random.uuid4())
        self.instance_arn = instance_arn
        self.target_id = target_id
        self.target_type = target_type
        self.permission_set_arn = permission_set_arn
        self.principal_type = principal_type
        self.principal_id = principal_id
        self.created_date = unix_time()

    def to_json(self, include_creation_date: bool = False) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "TargetId": self.target_id,
            "TargetType": self.target_type,
            "PermissionSetArn": self.permission_set_arn,
            "PrincipalType": self.principal_type,
            "PrincipalId": self.principal_id,
        }
        if include_creation_date:
            summary["CreatedDate"] = self.created_date
        return summary


class PermissionSet(BaseModel):
    def __init__(
        self,
        name: str,
        description: str,
        instance_arn: str,
        session_duration: str,
        relay_state: str,
        tags: List[Dict[str, str]],
    ):
        self.name = name
        self.description = description
        self.instance_arn = instance_arn
        self.permission_set_arn = PermissionSet.generate_id(instance_arn)
        self.session_duration = session_duration
        self.relay_state = relay_state
        self.tags = tags
        self.created_date = unix_time()

    def to_json(self, include_creation_date: bool = False) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "Name": self.name,
            "Description": self.description,
            "PermissionSetArn": self.permission_set_arn,
            "SessionDuration": self.session_duration,
            "RelayState": self.relay_state,
        }
        if include_creation_date:
            summary["CreatedDate"] = self.created_date
        return summary

    @staticmethod
    def generate_id(instance_arn: str) -> str:
        chars = list(range(10)) + ["a", "b", "c", "d", "e", "f"]
        return (
            instance_arn
            + "/ps-"
            + "".join(str(random.choice(chars)) for _ in range(16))
        )


class SSOAdminBackend(BaseBackend):
    """Implementation of SSOAdmin APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.account_assignments: List[AccountAssignment] = list()
        self.permission_sets: List[PermissionSet] = list()

    def create_account_assignment(
        self,
        instance_arn: str,
        target_id: str,
        target_type: str,
        permission_set_arn: str,
        principal_type: str,
        principal_id: str,
    ) -> Dict[str, Any]:
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
        instance_arn: str,
        target_id: str,
        target_type: str,
        permission_set_arn: str,
        principal_type: str,
        principal_id: str,
    ) -> Dict[str, Any]:
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
        instance_arn: str,
        target_id: str,
        target_type: str,
        permission_set_arn: str,
        principal_type: str,
        principal_id: str,
    ) -> AccountAssignment:
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

    def list_account_assignments(
        self, instance_arn: str, account_id: str, permission_set_arn: str
    ) -> List[Dict[str, Any]]:
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

    def create_permission_set(
        self,
        name: str,
        description: str,
        instance_arn: str,
        session_duration: str,
        relay_state: str,
        tags: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        permission_set = PermissionSet(
            name,
            description,
            instance_arn,
            session_duration,
            relay_state,
            tags,
        )
        self.permission_sets.append(permission_set)
        return permission_set.to_json(True)

    def update_permission_set(
        self,
        instance_arn: str,
        permission_set_arn: str,
        description: str,
        session_duration: str,
        relay_state: str,
    ) -> Dict[str, Any]:
        permission_set = self._find_permission_set(
            instance_arn,
            permission_set_arn,
        )
        self.permission_sets.remove(permission_set)
        permission_set.description = description
        permission_set.session_duration = session_duration
        permission_set.relay_state = relay_state
        self.permission_sets.append(permission_set)
        return permission_set.to_json(True)

    def describe_permission_set(
        self, instance_arn: str, permission_set_arn: str
    ) -> Dict[str, Any]:
        permission_set = self._find_permission_set(
            instance_arn,
            permission_set_arn,
        )
        return permission_set.to_json(True)

    def delete_permission_set(
        self, instance_arn: str, permission_set_arn: str
    ) -> Dict[str, Any]:
        permission_set = self._find_permission_set(
            instance_arn,
            permission_set_arn,
        )
        self.permission_sets.remove(permission_set)
        return permission_set.to_json(include_creation_date=True)

    def _find_permission_set(
        self, instance_arn: str, permission_set_arn: str
    ) -> PermissionSet:
        for permission_set in self.permission_sets:
            instance_arn_match = permission_set.instance_arn == instance_arn
            permission_set_match = (
                permission_set.permission_set_arn == permission_set_arn
            )
            if instance_arn_match and permission_set_match:
                return permission_set
        raise ResourceNotFound

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore[misc]
    def list_permission_sets(self, instance_arn: str) -> List[PermissionSet]:
        permission_sets = []
        for permission_set in self.permission_sets:
            if permission_set.instance_arn == instance_arn:
                permission_sets.append(permission_set)
        return permission_sets


ssoadmin_backends = BackendDict(SSOAdminBackend, "sso")
