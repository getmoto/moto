import json

from moto.core.responses import BaseResponse
from moto.moto_api._internal import mock_random

from .models import ssoadmin_backends, SSOAdminBackend


class SSOAdminResponse(BaseResponse):
    """Handler for SSOAdmin requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="sso-admin")

    @property
    def ssoadmin_backend(self) -> SSOAdminBackend:
        """Return backend instance specific for this region."""
        return ssoadmin_backends[self.current_account][self.region]

    def create_account_assignment(self) -> str:
        params = json.loads(self.body)
        instance_arn = params.get("InstanceArn")
        target_id = params.get("TargetId")
        target_type = params.get("TargetType")
        permission_set_arn = params.get("PermissionSetArn")
        principal_type = params.get("PrincipalType")
        principal_id = params.get("PrincipalId")
        summary = self.ssoadmin_backend.create_account_assignment(
            instance_arn=instance_arn,
            target_id=target_id,
            target_type=target_type,
            permission_set_arn=permission_set_arn,
            principal_type=principal_type,
            principal_id=principal_id,
        )
        summary["Status"] = "SUCCEEDED"
        summary["RequestId"] = str(mock_random.uuid4())
        return json.dumps({"AccountAssignmentCreationStatus": summary})

    def delete_account_assignment(self) -> str:
        params = json.loads(self.body)
        instance_arn = params.get("InstanceArn")
        target_id = params.get("TargetId")
        target_type = params.get("TargetType")
        permission_set_arn = params.get("PermissionSetArn")
        principal_type = params.get("PrincipalType")
        principal_id = params.get("PrincipalId")
        summary = self.ssoadmin_backend.delete_account_assignment(
            instance_arn=instance_arn,
            target_id=target_id,
            target_type=target_type,
            permission_set_arn=permission_set_arn,
            principal_type=principal_type,
            principal_id=principal_id,
        )
        summary["Status"] = "SUCCEEDED"
        summary["RequestId"] = str(mock_random.uuid4())
        return json.dumps({"AccountAssignmentDeletionStatus": summary})

    def list_account_assignments(self) -> str:
        params = json.loads(self.body)
        instance_arn = params.get("InstanceArn")
        account_id = params.get("AccountId")
        permission_set_arn = params.get("PermissionSetArn")
        assignments = self.ssoadmin_backend.list_account_assignments(
            instance_arn=instance_arn,
            account_id=account_id,
            permission_set_arn=permission_set_arn,
        )
        return json.dumps({"AccountAssignments": assignments})

    def create_permission_set(self) -> str:
        name = self._get_param("Name")
        description = self._get_param("Description")
        instance_arn = self._get_param("InstanceArn")
        session_duration = self._get_param("SessionDuration", 3600)
        relay_state = self._get_param("RelayState")
        tags = self._get_param("Tags")

        permission_set = self.ssoadmin_backend.create_permission_set(
            name=name,
            description=description,
            instance_arn=instance_arn,
            session_duration=session_duration,
            relay_state=relay_state,
            tags=tags,
        )

        return json.dumps({"PermissionSet": permission_set})

    def delete_permission_set(self) -> str:
        params = json.loads(self.body)
        instance_arn = params.get("InstanceArn")
        permission_set_arn = params.get("PermissionSetArn")
        self.ssoadmin_backend.delete_permission_set(
            instance_arn=instance_arn,
            permission_set_arn=permission_set_arn,
        )
        return "{}"

    def update_permission_set(self) -> str:
        instance_arn = self._get_param("InstanceArn")
        permission_set_arn = self._get_param("PermissionSetArn")
        description = self._get_param("Description")
        session_duration = self._get_param("SessionDuration", 3600)
        relay_state = self._get_param("RelayState")

        self.ssoadmin_backend.update_permission_set(
            instance_arn=instance_arn,
            permission_set_arn=permission_set_arn,
            description=description,
            session_duration=session_duration,
            relay_state=relay_state,
        )
        return "{}"

    def describe_permission_set(self) -> str:
        instance_arn = self._get_param("InstanceArn")
        permission_set_arn = self._get_param("PermissionSetArn")

        permission_set = self.ssoadmin_backend.describe_permission_set(
            instance_arn=instance_arn,
            permission_set_arn=permission_set_arn,
        )
        return json.dumps({"PermissionSet": permission_set})

    def list_permission_sets(self) -> str:
        instance_arn = self._get_param("InstanceArn")
        max_results = self._get_int_param("MaxResults")
        next_token = self._get_param("NextToken")
        permission_sets, next_token = self.ssoadmin_backend.list_permission_sets(
            instance_arn=instance_arn, max_results=max_results, next_token=next_token
        )
        permission_set_ids = []
        for permission_set in permission_sets:
            permission_set_ids.append(permission_set.permission_set_arn)
        response = {"PermissionSets": permission_set_ids}
        if next_token:
            response["NextToken"] = next_token
        return json.dumps(response)
