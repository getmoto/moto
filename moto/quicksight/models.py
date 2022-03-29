"""QuickSightBackend class with methods for supported APIs."""

from moto.core import ACCOUNT_ID, BaseBackend, BaseModel
from moto.core.utils import BackendDict
from .exceptions import ResourceNotFoundException


class QuicksightGroup(BaseModel):
    def __init__(self, region, group_name, description, aws_account_id, namespace):
        self.arn = (
            f"arn:aws:quicksight:{region}:{ACCOUNT_ID}:group/default/{group_name}"
        )
        self.group_name = group_name
        self.description = description
        self.aws_account_id = aws_account_id
        self.namespace = namespace

    def to_json(self):
        return {
            "Arn": self.arn,
            "GroupName": self.group_name,
            "Description": self.description,
            "PrincipalId": self.aws_account_id,
            "Namespace": self.namespace,
        }


class QuicksightUser(BaseModel):
    def __init__(self, region, email, identity_type, username, user_role):
        self.arn = f"arn:aws:quicksight:{region}:{ACCOUNT_ID}:user/default/{username}"
        self.email = email
        self.identity_type = identity_type
        self.username = username
        self.user_role = user_role
        self.active = False

    def to_json(self):
        return {
            "Arn": self.arn,
            "Email": self.email,
            "IdentityType": self.identity_type,
            "Role": self.user_role,
            "UserName": self.username,
            "Active": self.active,
        }


class QuickSightBackend(BaseBackend):
    """Implementation of QuickSight APIs."""

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.groups = dict()
        self.users = dict()

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_group(self, group_name, description, aws_account_id, namespace):
        group = QuicksightGroup(
            region=self.region_name,
            group_name=group_name,
            description=description,
            aws_account_id=aws_account_id,
            namespace=namespace,
        )
        self.groups[f"{aws_account_id}:{namespace}:{group_name}"] = group
        return group

    def delete_group(self, aws_account_id, namespace, group_name):
        self.groups.pop(f"{aws_account_id}:{namespace}:{group_name}", None)

    def delete_user(self, aws_account_id, namespace, user_name):
        self.users.pop(f"{aws_account_id}:{namespace}:{user_name}", None)

    def describe_group(self, aws_account_id, namespace, group_name):
        if f"{aws_account_id}:{namespace}:{group_name}" not in self.groups:
            raise ResourceNotFoundException(f"Group {group_name} not found")
        return self.groups[f"{aws_account_id}:{namespace}:{group_name}"]

    def describe_user(self, aws_account_id, namespace, user_name):
        if f"{aws_account_id}:{namespace}:{user_name}" not in self.users:
            raise ResourceNotFoundException(f"User {user_name} not found")
        return self.users[f"{aws_account_id}:{namespace}:{user_name}"]

    def register_user(
        self, identity_type, email, user_role, aws_account_id, namespace, user_name
    ):
        """
        The following parameters are not yet implemented:
        IamArn, SessionName, CustomsPermissionsName, ExternalLoginFederationProviderType, CustomFederationProviderUrl, ExternalLoginId
        """
        user = QuicksightUser(
            region=self.region_name,
            email=email,
            identity_type=identity_type,
            user_role=user_role,
            username=user_name,
        )
        self.users[f"{aws_account_id}:{namespace}:{user_name}"] = user
        return user

    def update_group(self, aws_account_id, namespace, group_name, description):
        group = self.describe_group(aws_account_id, namespace, group_name)
        group.description = description
        return group


quicksight_backends = BackendDict(QuickSightBackend, "quicksight")
