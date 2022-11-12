from .exceptions import ResourceNotFound

from moto.core import BaseBackend, BackendDict, BaseModel
from moto.core.utils import unix_time
from moto.moto_api._internal import mock_random as random
from moto.utilities.paginator import paginate
from .utils import PAGINATION_MODEL


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
        self.request_id = str(random.uuid4())
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


class PermissionSet(BaseModel):
    def __init__(
        self,
        name,
        description,
        instance_arn,
        session_duration,
        relay_state,
        tags,
    ):
        self.name = name
        self.description = description
        self.instance_arn = instance_arn
        self.permission_set_arn = PermissionSet.generate_id(instance_arn)
        self.session_duration = session_duration
        self.relay_state = relay_state
        self.tags = tags
        self.created_date = unix_time()

    def to_json(self, include_creation_date=False):
        summary = {
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
    def generate_id(instance_arn):
        chars = list(range(10)) + ["a", "b", "c", "d", "e", "f"]
        return (
            instance_arn
            + "/ps-"
            + "".join(str(random.choice(chars)) for _ in range(16))
        )


class SSOAdminBackend(BaseBackend):
    """Implementation of SSOAdmin APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.account_assignments = list()
        self.permission_sets = list()

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

    def create_permission_set(
        self,
        name,
        description,
        instance_arn,
        session_duration,
        relay_state,
        tags,
    ):
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
        instance_arn,
        permission_set_arn,
        description,
        session_duration,
        relay_state,
    ):
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
        self,
        instance_arn,
        permission_set_arn,
    ):
        permission_set = self._find_permission_set(
            instance_arn,
            permission_set_arn,
        )
        return permission_set.to_json(True)

    def delete_permission_set(
        self,
        instance_arn,
        permission_set_arn,
    ):
        permission_set = self._find_permission_set(
            instance_arn,
            permission_set_arn,
        )
        self.permission_sets.remove(permission_set)
        return permission_set.to_json(include_creation_date=True)

    def _find_permission_set(
        self,
        instance_arn,
        permission_set_arn,
    ):
        for permission_set in self.permission_sets:
            instance_arn_match = permission_set.instance_arn == instance_arn
            permission_set_match = (
                permission_set.permission_set_arn == permission_set_arn
            )
            if instance_arn_match and permission_set_match:
                return permission_set
        raise ResourceNotFound

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_permission_sets(self, instance_arn):
        permission_sets = []
        for permission_set in self.permission_sets:
            if permission_set.instance_arn == instance_arn:
                permission_sets.append(permission_set)
        return permission_sets


ssoadmin_backends = BackendDict(SSOAdminBackend, "sso")
