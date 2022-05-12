"""QuickSightBackend class with methods for supported APIs."""

from moto.core import get_account_id, BaseBackend, BaseModel
from moto.core.utils import BackendDict
from .exceptions import ResourceNotFoundException


def _create_id(aws_account_id, namespace, _id):
    return f"{aws_account_id}:{namespace}:{_id}"


class QuicksightDataSet(BaseModel):
    def __init__(self, region, _id, name):
        self.arn = f"arn:aws:quicksight:{region}:{get_account_id()}:data-set/{_id}"
        self._id = _id
        self.name = name
        self.region = region

    def to_json(self):
        return {
            "Arn": self.arn,
            "DataSetId": self._id,
            "IngestionArn": f"arn:aws:quicksight:{self.region}:{get_account_id()}:ingestion/tbd",
        }


class QuicksightIngestion(BaseModel):
    def __init__(self, region, data_set_id, ingestion_id):
        self.arn = f"arn:aws:quicksight:{region}:{get_account_id()}:data-set/{data_set_id}/ingestions/{ingestion_id}"
        self.ingestion_id = ingestion_id

    def to_json(self):
        return {
            "Arn": self.arn,
            "IngestionId": self.ingestion_id,
            "IngestionStatus": "INITIALIZED",
        }


class QuicksightMembership(BaseModel):
    def __init__(self, region, group, user):
        self.group = group
        self.user = user
        self.arn = f"arn:aws:quicksight:{region}:{get_account_id()}:group/default/{group}/{user}"

    def to_json(self):
        return {"Arn": self.arn, "MemberName": self.user}


class QuicksightGroup(BaseModel):
    def __init__(self, region, group_name, description, aws_account_id, namespace):
        self.arn = (
            f"arn:aws:quicksight:{region}:{get_account_id()}:group/default/{group_name}"
        )
        self.group_name = group_name
        self.description = description
        self.aws_account_id = aws_account_id
        self.namespace = namespace
        self.region = region

        self.members = dict()

    def add_member(self, user_name):
        membership = QuicksightMembership(self.region, self.group_name, user_name)
        self.members[user_name] = membership
        return membership

    def delete_member(self, user_name):
        self.members.pop(user_name, None)

    def get_member(self, user_name):
        return self.members[user_name]

    def list_members(self):
        return self.members.values()

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
        self.arn = (
            f"arn:aws:quicksight:{region}:{get_account_id()}:user/default/{username}"
        )
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

    def create_data_set(self, data_set_id, name):
        return QuicksightDataSet(self.region_name, data_set_id, name=name)

    def create_group(self, group_name, description, aws_account_id, namespace):
        group = QuicksightGroup(
            region=self.region_name,
            group_name=group_name,
            description=description,
            aws_account_id=aws_account_id,
            namespace=namespace,
        )
        _id = _create_id(aws_account_id, namespace, group_name)
        self.groups[_id] = group
        return group

    def create_group_membership(self, aws_account_id, namespace, group_name, user_name):
        group = self.describe_group(aws_account_id, namespace, group_name)
        return group.add_member(user_name)

    def create_ingestion(self, data_set_id, ingestion_id):
        return QuicksightIngestion(self.region_name, data_set_id, ingestion_id)

    def delete_group(self, aws_account_id, namespace, group_name):
        _id = _create_id(aws_account_id, namespace, group_name)
        self.groups.pop(_id, None)

    def delete_user(self, aws_account_id, namespace, user_name):
        # Delete users from all groups
        for group in self.groups.values():
            group.delete_member(user_name)
        # Delete user itself
        _id = _create_id(aws_account_id, namespace, user_name)
        self.users.pop(_id, None)

    def describe_group(self, aws_account_id, namespace, group_name):
        _id = _create_id(aws_account_id, namespace, group_name)
        if _id not in self.groups:
            raise ResourceNotFoundException(f"Group {group_name} not found")
        return self.groups[_id]

    def describe_group_membership(
        self, aws_account_id, namespace, group_name, user_name
    ):
        group = self.describe_group(aws_account_id, namespace, group_name)
        return group.get_member(user_name)

    def describe_user(self, aws_account_id, namespace, user_name):
        _id = _create_id(aws_account_id, namespace, user_name)
        if _id not in self.users:
            raise ResourceNotFoundException(f"User {user_name} not found")
        return self.users[_id]

    def list_groups(self, aws_account_id, namespace):
        """
        The NextToken and MaxResults parameters are not yet implemented
        """
        id_for_ns = _create_id(aws_account_id, namespace, _id="")
        return [
            group for _id, group in self.groups.items() if _id.startswith(id_for_ns)
        ]

    def list_group_memberships(self, aws_account_id, namespace, group_name):
        """
        The NextToken and MaxResults parameters are not yet implemented
        """
        group = self.describe_group(aws_account_id, namespace, group_name)
        return group.list_members()

    def list_users(self, aws_account_id, namespace):
        """
        The NextToken and MaxResults parameters are not yet implemented
        """
        id_for_ns = _create_id(aws_account_id, namespace, _id="")
        return [user for _id, user in self.users.items() if _id.startswith(id_for_ns)]

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
        _id = _create_id(aws_account_id, namespace, user_name)
        self.users[_id] = user
        return user

    def update_group(self, aws_account_id, namespace, group_name, description):
        group = self.describe_group(aws_account_id, namespace, group_name)
        group.description = description
        return group


quicksight_backends = BackendDict(QuickSightBackend, "quicksight")
