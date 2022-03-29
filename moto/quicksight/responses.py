"""Handles incoming quicksight requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import quicksight_backends


class QuickSightResponse(BaseResponse):
    """Handler for QuickSight requests and responses."""

    @property
    def quicksight_backend(self):
        """Return backend instance specific for this region."""
        return quicksight_backends[self.region]

    def groups(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.create_group()

    def group(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.describe_group()
        if request.method == "DELETE":
            return self.delete_group()
        if request.method == "PUT":
            return self.update_group()

    def users(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.register_user()

    def user(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.describe_user()
        if request.method == "DELETE":
            return self.delete_user()

    def create_group(self):
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

    def register_user(self):
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

    def describe_group(self):
        aws_account_id = self.path.split("/")[-5]
        namespace = self.path.split("/")[-3]
        group_name = self.path.split("/")[-1]

        group = self.quicksight_backend.describe_group(
            aws_account_id, namespace, group_name
        )
        return 200, {}, json.dumps(dict(Group=group.to_json()))

    def describe_user(self):
        aws_account_id = self.path.split("/")[-5]
        namespace = self.path.split("/")[-3]
        user_name = self.path.split("/")[-1]

        user = self.quicksight_backend.describe_user(
            aws_account_id, namespace, user_name
        )
        return 200, {}, json.dumps(dict(User=user.to_json()))

    def delete_group(self):
        aws_account_id = self.path.split("/")[-5]
        namespace = self.path.split("/")[-3]
        group_name = self.path.split("/")[-1]

        self.quicksight_backend.delete_group(aws_account_id, namespace, group_name)
        return 204, {}, json.dumps({"Status": 204})

    def delete_user(self):
        aws_account_id = self.path.split("/")[-5]
        namespace = self.path.split("/")[-3]
        user_name = self.path.split("/")[-1]

        self.quicksight_backend.delete_user(aws_account_id, namespace, user_name)
        return 204, {}, json.dumps({"Status": 204})

    def update_group(self):
        aws_account_id = self.path.split("/")[-5]
        namespace = self.path.split("/")[-3]
        group_name = self.path.split("/")[-1]
        description = json.loads(self.body).get("Description")

        group = self.quicksight_backend.update_group(
            aws_account_id, namespace, group_name, description
        )
        return 200, {}, json.dumps(dict(Group=group.to_json()))
