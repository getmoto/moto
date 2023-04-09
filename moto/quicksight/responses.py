"""Handles incoming quicksight requests, invokes methods, returns responses."""
import json
from typing import Any

from moto.core.common_types import TYPE_RESPONSE
from moto.core.responses import BaseResponse
from .models import quicksight_backends, QuickSightBackend


class QuickSightResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="quicksight")

    @property
    def quicksight_backend(self) -> QuickSightBackend:
        """Return backend instance specific for this region."""
        return quicksight_backends[self.current_account][self.region]

    def dataset(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.create_data_set()

    def groups(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.create_group()
        if request.method == "GET":
            return self.list_groups()

    def group(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.describe_group()
        if request.method == "DELETE":
            return self.delete_group()
        if request.method == "PUT":
            return self.update_group()

    def group_member(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "PUT":
            return self.create_group_membership()
        if request.method == "GET":
            return self.describe_group_membership()

    def group_members(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.list_group_memberships()

    def ingestion(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "PUT":
            return self.create_ingestion()

    def users(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.register_user()
        if request.method == "GET":
            return self.list_users()

    def user(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.describe_user()
        if request.method == "DELETE":
            return self.delete_user()

    def create_data_set(self) -> TYPE_RESPONSE:
        params = json.loads(self.body)
        data_set_id = params.get("DataSetId")
        name = params.get("Name")
        data_set = self.quicksight_backend.create_data_set(data_set_id, name)
        return 200, {}, json.dumps(data_set.to_json())

    def create_group(self) -> TYPE_RESPONSE:
        params = json.loads(self.body)
        group_name = params.get("GroupName")
        description = params.get("Description")
        aws_account_id = self.path.split("/")[-4]
        namespace = self.path.split("/")[-2]
        group = self.quicksight_backend.create_group(
            group_name=group_name,
            description=description,
            aws_account_id=aws_account_id,
            namespace=namespace,
        )
        return 200, {}, json.dumps(dict(Group=group.to_json()))

    def create_group_membership(self) -> TYPE_RESPONSE:
        aws_account_id = self.path.split("/")[-7]
        namespace = self.path.split("/")[-5]
        group_name = self.path.split("/")[-3]
        user_name = self.path.split("/")[-1]
        member = self.quicksight_backend.create_group_membership(
            aws_account_id, namespace, group_name, user_name
        )
        return 200, {}, json.dumps({"GroupMember": member.to_json()})

    def create_ingestion(self) -> TYPE_RESPONSE:
        data_set_id = self.path.split("/")[-3]
        ingestion_id = self.path.split("/")[-1]
        ingestion = self.quicksight_backend.create_ingestion(data_set_id, ingestion_id)
        return 200, {}, json.dumps(ingestion.to_json())

    def describe_group_membership(self) -> TYPE_RESPONSE:
        aws_account_id = self.path.split("/")[-7]
        namespace = self.path.split("/")[-5]
        group_name = self.path.split("/")[-3]
        user_name = self.path.split("/")[-1]
        member = self.quicksight_backend.describe_group_membership(
            aws_account_id, namespace, group_name, user_name
        )
        return 200, {}, json.dumps({"GroupMember": member.to_json()})

    def list_groups(self) -> TYPE_RESPONSE:
        aws_account_id = self.path.split("/")[-4]
        namespace = self.path.split("/")[-2]
        groups = self.quicksight_backend.list_groups(aws_account_id, namespace)
        return 200, {}, json.dumps(dict(GroupList=[g.to_json() for g in groups]))

    def list_group_memberships(self) -> TYPE_RESPONSE:
        aws_account_id = self.path.split("/")[-6]
        namespace = self.path.split("/")[-4]
        group_name = self.path.split("/")[-2]
        members = self.quicksight_backend.list_group_memberships(
            aws_account_id, namespace, group_name
        )
        return 200, {}, json.dumps({"GroupMemberList": [m.to_json() for m in members]})

    def list_users(self) -> TYPE_RESPONSE:
        aws_account_id = self.path.split("/")[-4]
        namespace = self.path.split("/")[-2]
        users = self.quicksight_backend.list_users(aws_account_id, namespace)
        return 200, {}, json.dumps(dict(UserList=[u.to_json() for u in users]))

    def register_user(self) -> TYPE_RESPONSE:
        params = json.loads(self.body)
        identity_type = params.get("IdentityType")
        email = params.get("Email")
        user_role = params.get("UserRole")
        aws_account_id = self.path.split("/")[-4]
        namespace = self.path.split("/")[-2]
        user_name = params.get("UserName")
        user = self.quicksight_backend.register_user(
            identity_type=identity_type,
            email=email,
            user_role=user_role,
            aws_account_id=aws_account_id,
            namespace=namespace,
            user_name=user_name,
        )
        return 200, {}, json.dumps(dict(User=user.to_json(), UserInvitationUrl="TBD"))

    def describe_group(self) -> TYPE_RESPONSE:
        aws_account_id = self.path.split("/")[-5]
        namespace = self.path.split("/")[-3]
        group_name = self.path.split("/")[-1]

        group = self.quicksight_backend.describe_group(
            aws_account_id, namespace, group_name
        )
        return 200, {}, json.dumps(dict(Group=group.to_json()))

    def describe_user(self) -> TYPE_RESPONSE:
        aws_account_id = self.path.split("/")[-5]
        namespace = self.path.split("/")[-3]
        user_name = self.path.split("/")[-1]

        user = self.quicksight_backend.describe_user(
            aws_account_id, namespace, user_name
        )
        return 200, {}, json.dumps(dict(User=user.to_json()))

    def delete_group(self) -> TYPE_RESPONSE:
        aws_account_id = self.path.split("/")[-5]
        namespace = self.path.split("/")[-3]
        group_name = self.path.split("/")[-1]

        self.quicksight_backend.delete_group(aws_account_id, namespace, group_name)
        return 204, {}, json.dumps({"Status": 204})

    def delete_user(self) -> TYPE_RESPONSE:
        aws_account_id = self.path.split("/")[-5]
        namespace = self.path.split("/")[-3]
        user_name = self.path.split("/")[-1]

        self.quicksight_backend.delete_user(aws_account_id, namespace, user_name)
        return 204, {}, json.dumps({"Status": 204})

    def update_group(self) -> TYPE_RESPONSE:
        aws_account_id = self.path.split("/")[-5]
        namespace = self.path.split("/")[-3]
        group_name = self.path.split("/")[-1]
        description = json.loads(self.body).get("Description")

        group = self.quicksight_backend.update_group(
            aws_account_id, namespace, group_name, description
        )
        return 200, {}, json.dumps(dict(Group=group.to_json()))
