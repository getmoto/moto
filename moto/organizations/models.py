from __future__ import unicode_literals

import datetime
import re
import json

from moto.core import BaseBackend, BaseModel
from moto.core.exceptions import RESTError
from moto.core.utils import unix_time
from moto.organizations import utils
from moto.organizations.exceptions import (
    InvalidInputException,
    DuplicateOrganizationalUnitException,
)


class FakeOrganization(BaseModel):
    def __init__(self, feature_set):
        self.id = utils.make_random_org_id()
        self.root_id = utils.make_random_root_id()
        self.feature_set = feature_set
        self.master_account_id = utils.MASTER_ACCOUNT_ID
        self.master_account_email = utils.MASTER_ACCOUNT_EMAIL
        self.available_policy_types = [
            {"Type": "SERVICE_CONTROL_POLICY", "Status": "ENABLED"}
        ]

    @property
    def arn(self):
        return utils.ORGANIZATION_ARN_FORMAT.format(self.master_account_id, self.id)

    @property
    def master_account_arn(self):
        return utils.MASTER_ACCOUNT_ARN_FORMAT.format(self.master_account_id, self.id)

    def describe(self):
        return {
            "Organization": {
                "Id": self.id,
                "Arn": self.arn,
                "FeatureSet": self.feature_set,
                "MasterAccountArn": self.master_account_arn,
                "MasterAccountId": self.master_account_id,
                "MasterAccountEmail": self.master_account_email,
                "AvailablePolicyTypes": self.available_policy_types,
            }
        }


class FakeAccount(BaseModel):
    def __init__(self, organization, **kwargs):
        self.type = "ACCOUNT"
        self.organization_id = organization.id
        self.master_account_id = organization.master_account_id
        self.create_account_status_id = utils.make_random_create_account_status_id()
        self.id = utils.make_random_account_id()
        self.name = kwargs["AccountName"]
        self.email = kwargs["Email"]
        self.create_time = datetime.datetime.utcnow()
        self.status = "ACTIVE"
        self.joined_method = "CREATED"
        self.parent_id = organization.root_id
        self.attached_policies = []
        self.tags = {}

    @property
    def arn(self):
        return utils.ACCOUNT_ARN_FORMAT.format(
            self.master_account_id, self.organization_id, self.id
        )

    @property
    def create_account_status(self):
        return {
            "CreateAccountStatus": {
                "Id": self.create_account_status_id,
                "AccountName": self.name,
                "State": "SUCCEEDED",
                "RequestedTimestamp": unix_time(self.create_time),
                "CompletedTimestamp": unix_time(self.create_time),
                "AccountId": self.id,
            }
        }

    def describe(self):
        return {
            "Account": {
                "Id": self.id,
                "Arn": self.arn,
                "Email": self.email,
                "Name": self.name,
                "Status": self.status,
                "JoinedMethod": self.joined_method,
                "JoinedTimestamp": unix_time(self.create_time),
            }
        }


class FakeOrganizationalUnit(BaseModel):
    def __init__(self, organization, **kwargs):
        self.type = "ORGANIZATIONAL_UNIT"
        self.organization_id = organization.id
        self.master_account_id = organization.master_account_id
        self.id = utils.make_random_ou_id(organization.root_id)
        self.name = kwargs.get("Name")
        self.parent_id = kwargs.get("ParentId")
        self._arn_format = utils.OU_ARN_FORMAT
        self.attached_policies = []

    @property
    def arn(self):
        return self._arn_format.format(
            self.master_account_id, self.organization_id, self.id
        )

    def describe(self):
        return {
            "OrganizationalUnit": {"Id": self.id, "Arn": self.arn, "Name": self.name}
        }


class FakeRoot(FakeOrganizationalUnit):
    def __init__(self, organization, **kwargs):
        super(FakeRoot, self).__init__(organization, **kwargs)
        self.type = "ROOT"
        self.id = organization.root_id
        self.name = "Root"
        self.policy_types = [{"Type": "SERVICE_CONTROL_POLICY", "Status": "ENABLED"}]
        self._arn_format = utils.ROOT_ARN_FORMAT
        self.attached_policies = []

    def describe(self):
        return {
            "Id": self.id,
            "Arn": self.arn,
            "Name": self.name,
            "PolicyTypes": self.policy_types,
        }


class FakeServiceControlPolicy(BaseModel):
    def __init__(self, organization, **kwargs):
        self.content = kwargs.get("Content")
        self.description = kwargs.get("Description")
        self.name = kwargs.get("Name")
        self.type = kwargs.get("Type")
        self.id = utils.make_random_service_control_policy_id()
        self.aws_managed = False
        self.organization_id = organization.id
        self.master_account_id = organization.master_account_id
        self._arn_format = utils.SCP_ARN_FORMAT
        self.attachments = []

    @property
    def arn(self):
        return self._arn_format.format(
            self.master_account_id, self.organization_id, self.id
        )

    def describe(self):
        return {
            "Policy": {
                "PolicySummary": {
                    "Id": self.id,
                    "Arn": self.arn,
                    "Name": self.name,
                    "Description": self.description,
                    "Type": self.type,
                    "AwsManaged": self.aws_managed,
                },
                "Content": self.content,
            }
        }


class OrganizationsBackend(BaseBackend):
    def __init__(self):
        self.org = None
        self.accounts = []
        self.ou = []
        self.policies = []

    def create_organization(self, **kwargs):
        self.org = FakeOrganization(kwargs["FeatureSet"])
        root_ou = FakeRoot(self.org)
        self.ou.append(root_ou)
        master_account = FakeAccount(
            self.org, AccountName="master", Email=self.org.master_account_email
        )
        master_account.id = self.org.master_account_id
        self.accounts.append(master_account)
        default_policy = FakeServiceControlPolicy(
            self.org,
            Name="FullAWSAccess",
            Description="Allows access to every operation",
            Type="SERVICE_CONTROL_POLICY",
            Content=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
                }
            ),
        )
        default_policy.id = utils.DEFAULT_POLICY_ID
        default_policy.aws_managed = True
        self.policies.append(default_policy)
        self.attach_policy(PolicyId=default_policy.id, TargetId=root_ou.id)
        self.attach_policy(PolicyId=default_policy.id, TargetId=master_account.id)
        return self.org.describe()

    def describe_organization(self):
        if not self.org:
            raise RESTError(
                "AWSOrganizationsNotInUseException",
                "Your account is not a member of an organization.",
            )
        return self.org.describe()

    def list_roots(self):
        return dict(Roots=[ou.describe() for ou in self.ou if isinstance(ou, FakeRoot)])

    def create_organizational_unit(self, **kwargs):
        new_ou = FakeOrganizationalUnit(self.org, **kwargs)
        self.ou.append(new_ou)
        self.attach_policy(PolicyId=utils.DEFAULT_POLICY_ID, TargetId=new_ou.id)
        return new_ou.describe()

    def update_organizational_unit(self, **kwargs):
        for ou in self.ou:
            if ou.name == kwargs["Name"]:
                raise DuplicateOrganizationalUnitException
        ou = self.get_organizational_unit_by_id(kwargs["OrganizationalUnitId"])
        ou.name = kwargs["Name"]
        return ou.describe()

    def get_organizational_unit_by_id(self, ou_id):
        ou = next((ou for ou in self.ou if ou.id == ou_id), None)
        if ou is None:
            raise RESTError(
                "OrganizationalUnitNotFoundException",
                "You specified an organizational unit that doesn't exist.",
            )
        return ou

    def validate_parent_id(self, parent_id):
        try:
            self.get_organizational_unit_by_id(parent_id)
        except RESTError:
            raise RESTError(
                "ParentNotFoundException", "You specified parent that doesn't exist."
            )
        return parent_id

    def describe_organizational_unit(self, **kwargs):
        ou = self.get_organizational_unit_by_id(kwargs["OrganizationalUnitId"])
        return ou.describe()

    def list_organizational_units_for_parent(self, **kwargs):
        parent_id = self.validate_parent_id(kwargs["ParentId"])
        return dict(
            OrganizationalUnits=[
                {"Id": ou.id, "Arn": ou.arn, "Name": ou.name}
                for ou in self.ou
                if ou.parent_id == parent_id
            ]
        )

    def create_account(self, **kwargs):
        new_account = FakeAccount(self.org, **kwargs)
        self.accounts.append(new_account)
        self.attach_policy(PolicyId=utils.DEFAULT_POLICY_ID, TargetId=new_account.id)
        return new_account.create_account_status

    def get_account_by_id(self, account_id):
        account = next(
            (account for account in self.accounts if account.id == account_id), None
        )
        if account is None:
            raise RESTError(
                "AccountNotFoundException",
                "You specified an account that doesn't exist.",
            )
        return account

    def get_account_by_attr(self, attr, value):
        account = next(
            (
                account
                for account in self.accounts
                if hasattr(account, attr) and getattr(account, attr) == value
            ),
            None,
        )
        if account is None:
            raise RESTError(
                "AccountNotFoundException",
                "You specified an account that doesn't exist.",
            )
        return account

    def describe_account(self, **kwargs):
        account = self.get_account_by_id(kwargs["AccountId"])
        return account.describe()

    def describe_create_account_status(self, **kwargs):
        account = self.get_account_by_attr(
            "create_account_status_id", kwargs["CreateAccountRequestId"]
        )
        return account.create_account_status

    def list_accounts(self):
        return dict(
            Accounts=[account.describe()["Account"] for account in self.accounts]
        )

    def list_accounts_for_parent(self, **kwargs):
        parent_id = self.validate_parent_id(kwargs["ParentId"])
        return dict(
            Accounts=[
                account.describe()["Account"]
                for account in self.accounts
                if account.parent_id == parent_id
            ]
        )

    def move_account(self, **kwargs):
        new_parent_id = self.validate_parent_id(kwargs["DestinationParentId"])
        self.validate_parent_id(kwargs["SourceParentId"])
        account = self.get_account_by_id(kwargs["AccountId"])
        index = self.accounts.index(account)
        self.accounts[index].parent_id = new_parent_id

    def list_parents(self, **kwargs):
        if re.compile(r"[0-9]{12}").match(kwargs["ChildId"]):
            child_object = self.get_account_by_id(kwargs["ChildId"])
        else:
            child_object = self.get_organizational_unit_by_id(kwargs["ChildId"])
        return dict(
            Parents=[
                {"Id": ou.id, "Type": ou.type}
                for ou in self.ou
                if ou.id == child_object.parent_id
            ]
        )

    def list_children(self, **kwargs):
        parent_id = self.validate_parent_id(kwargs["ParentId"])
        if kwargs["ChildType"] == "ACCOUNT":
            obj_list = self.accounts
        elif kwargs["ChildType"] == "ORGANIZATIONAL_UNIT":
            obj_list = self.ou
        else:
            raise RESTError("InvalidInputException", "You specified an invalid value.")
        return dict(
            Children=[
                {"Id": obj.id, "Type": kwargs["ChildType"]}
                for obj in obj_list
                if obj.parent_id == parent_id
            ]
        )

    def create_policy(self, **kwargs):
        new_policy = FakeServiceControlPolicy(self.org, **kwargs)
        self.policies.append(new_policy)
        return new_policy.describe()

    def describe_policy(self, **kwargs):
        if re.compile(utils.SCP_ID_REGEX).match(kwargs["PolicyId"]):
            policy = next(
                (p for p in self.policies if p.id == kwargs["PolicyId"]), None
            )
            if policy is None:
                raise RESTError(
                    "PolicyNotFoundException",
                    "You specified a policy that doesn't exist.",
                )
        else:
            raise RESTError("InvalidInputException", "You specified an invalid value.")
        return policy.describe()

    def attach_policy(self, **kwargs):
        policy = next((p for p in self.policies if p.id == kwargs["PolicyId"]), None)
        if re.compile(utils.ROOT_ID_REGEX).match(kwargs["TargetId"]) or re.compile(
            utils.OU_ID_REGEX
        ).match(kwargs["TargetId"]):
            ou = next((ou for ou in self.ou if ou.id == kwargs["TargetId"]), None)
            if ou is not None:
                if ou not in ou.attached_policies:
                    ou.attached_policies.append(policy)
                    policy.attachments.append(ou)
            else:
                raise RESTError(
                    "OrganizationalUnitNotFoundException",
                    "You specified an organizational unit that doesn't exist.",
                )
        elif re.compile(utils.ACCOUNT_ID_REGEX).match(kwargs["TargetId"]):
            account = next(
                (a for a in self.accounts if a.id == kwargs["TargetId"]), None
            )
            if account is not None:
                if account not in account.attached_policies:
                    account.attached_policies.append(policy)
                    policy.attachments.append(account)
            else:
                raise RESTError(
                    "AccountNotFoundException",
                    "You specified an account that doesn't exist.",
                )
        else:
            raise RESTError("InvalidInputException", "You specified an invalid value.")

    def list_policies(self, **kwargs):
        return dict(
            Policies=[p.describe()["Policy"]["PolicySummary"] for p in self.policies]
        )

    def list_policies_for_target(self, **kwargs):
        if re.compile(utils.OU_ID_REGEX).match(kwargs["TargetId"]):
            obj = next((ou for ou in self.ou if ou.id == kwargs["TargetId"]), None)
            if obj is None:
                raise RESTError(
                    "OrganizationalUnitNotFoundException",
                    "You specified an organizational unit that doesn't exist.",
                )
        elif re.compile(utils.ACCOUNT_ID_REGEX).match(kwargs["TargetId"]):
            obj = next((a for a in self.accounts if a.id == kwargs["TargetId"]), None)
            if obj is None:
                raise RESTError(
                    "AccountNotFoundException",
                    "You specified an account that doesn't exist.",
                )
        else:
            raise RESTError("InvalidInputException", "You specified an invalid value.")
        return dict(
            Policies=[
                p.describe()["Policy"]["PolicySummary"] for p in obj.attached_policies
            ]
        )

    def list_targets_for_policy(self, **kwargs):
        if re.compile(utils.SCP_ID_REGEX).match(kwargs["PolicyId"]):
            policy = next(
                (p for p in self.policies if p.id == kwargs["PolicyId"]), None
            )
            if policy is None:
                raise RESTError(
                    "PolicyNotFoundException",
                    "You specified a policy that doesn't exist.",
                )
        else:
            raise RESTError("InvalidInputException", "You specified an invalid value.")
        objects = [
            {"TargetId": obj.id, "Arn": obj.arn, "Name": obj.name, "Type": obj.type}
            for obj in policy.attachments
        ]
        return dict(Targets=objects)

    def tag_resource(self, **kwargs):
        account = next((a for a in self.accounts if a.id == kwargs["ResourceId"]), None)

        if account is None:
            raise InvalidInputException

        new_tags = {tag["Key"]: tag["Value"] for tag in kwargs["Tags"]}
        account.tags.update(new_tags)

    def list_tags_for_resource(self, **kwargs):
        account = next((a for a in self.accounts if a.id == kwargs["ResourceId"]), None)

        if account is None:
            raise InvalidInputException

        tags = [{"Key": key, "Value": value} for key, value in account.tags.items()]
        return dict(Tags=tags)

    def untag_resource(self, **kwargs):
        account = next((a for a in self.accounts if a.id == kwargs["ResourceId"]), None)

        if account is None:
            raise InvalidInputException

        for key in kwargs["TagKeys"]:
            account.tags.pop(key, None)


organizations_backend = OrganizationsBackend()
