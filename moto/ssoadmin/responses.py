import json

from moto.core.responses import BaseResponse
from uuid import uuid4

from .models import ssoadmin_backends


class SSOAdminResponse(BaseResponse):
    """Handler for SSOAdmin requests and responses."""

    @property
    def ssoadmin_backend(self):
        """Return backend instance specific for this region."""
        return ssoadmin_backends[self.region]

    def create_account_assignment(self):
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
        summary["RequestId"] = str(uuid4())
        return json.dumps({"AccountAssignmentCreationStatus": summary})

    def delete_account_assignment(self):
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
        summary["RequestId"] = str(uuid4())
        return json.dumps({"AccountAssignmentDeletionStatus": summary})

    def list_account_assignments(self):
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
