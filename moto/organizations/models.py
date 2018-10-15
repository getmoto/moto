from __future__ import unicode_literals

import datetime
import re

from moto.core import BaseBackend, BaseModel
from moto.core.exceptions import RESTError
from moto.core.utils import unix_time
from moto.organizations import utils


class FakeOrganization(BaseModel):

    def __init__(self, feature_set):
        self.id = utils.make_random_org_id()
        self.root_id = utils.make_random_root_id()
        self.feature_set = feature_set
        self.master_account_id = utils.MASTER_ACCOUNT_ID
        self.master_account_email = utils.MASTER_ACCOUNT_EMAIL
        self.available_policy_types = [{
            'Type': 'SERVICE_CONTROL_POLICY',
            'Status': 'ENABLED'
        }]

    @property
    def arn(self):
        return utils.ORGANIZATION_ARN_FORMAT.format(self.master_account_id, self.id)

    @property
    def master_account_arn(self):
        return utils.MASTER_ACCOUNT_ARN_FORMAT.format(self.master_account_id, self.id)

    def describe(self):
        return {
            'Organization': {
                'Id': self.id,
                'Arn': self.arn,
                'FeatureSet': self.feature_set,
                'MasterAccountArn': self.master_account_arn,
                'MasterAccountId': self.master_account_id,
                'MasterAccountEmail': self.master_account_email,
                'AvailablePolicyTypes': self.available_policy_types,
            }
        }


class FakeAccount(BaseModel):

    def __init__(self, organization, **kwargs):
        self.organization_id = organization.id
        self.master_account_id = organization.master_account_id
        self.create_account_status_id = utils.make_random_create_account_status_id()
        self.id = utils.make_random_account_id()
        self.name = kwargs['AccountName']
        self.email = kwargs['Email']
        self.create_time = datetime.datetime.utcnow()
        self.status = 'ACTIVE'
        self.joined_method = 'CREATED'
        self.parent_id = organization.root_id

    @property
    def arn(self):
        return utils.ACCOUNT_ARN_FORMAT.format(
            self.master_account_id,
            self.organization_id,
            self.id
        )

    @property
    def create_account_status(self):
        return {
            'CreateAccountStatus': {
                'Id': self.create_account_status_id,
                'AccountName': self.name,
                'State': 'SUCCEEDED',
                'RequestedTimestamp': unix_time(self.create_time),
                'CompletedTimestamp': unix_time(self.create_time),
                'AccountId': self.id,
            }
        }

    def describe(self):
        return {
            'Account': {
                'Id': self.id,
                'Arn': self.arn,
                'Email': self.email,
                'Name': self.name,
                'Status': self.status,
                'JoinedMethod': self.joined_method,
                'JoinedTimestamp': unix_time(self.create_time),
            }
        }


class FakeOrganizationalUnit(BaseModel):

    def __init__(self, organization, **kwargs):
        self.type = 'ORGANIZATIONAL_UNIT'
        self.organization_id = organization.id
        self.master_account_id = organization.master_account_id
        self.id = utils.make_random_ou_id(organization.root_id)
        self.name = kwargs.get('Name')
        self.parent_id = kwargs.get('ParentId')
        self._arn_format = utils.OU_ARN_FORMAT

    @property
    def arn(self):
        return self._arn_format.format(
            self.master_account_id,
            self.organization_id,
            self.id
        )

    def describe(self):
        return {
            'OrganizationalUnit': {
                'Id': self.id,
                'Arn': self.arn,
                'Name': self.name,
            }
        }


class FakeRoot(FakeOrganizationalUnit):

    def __init__(self, organization, **kwargs):
        super(FakeRoot, self).__init__(organization, **kwargs)
        self.type = 'ROOT'
        self.id = organization.root_id
        self.name = 'Root'
        self.policy_types = [{
            'Type': 'SERVICE_CONTROL_POLICY',
            'Status': 'ENABLED'
        }]
        self._arn_format = utils.ROOT_ARN_FORMAT

    def describe(self):
        return {
            'Id': self.id,
            'Arn': self.arn,
            'Name': self.name,
            'PolicyTypes': self.policy_types
        }


class OrganizationsBackend(BaseBackend):

    def __init__(self):
        self.org = None
        self.accounts = []
        self.ou = []

    def create_organization(self, **kwargs):
        self.org = FakeOrganization(kwargs['FeatureSet'])
        self.ou.append(FakeRoot(self.org))
        return self.org.describe()

    def describe_organization(self):
        if not self.org:
            raise RESTError(
                'AWSOrganizationsNotInUseException',
                "Your account is not a member of an organization."
            )
        return self.org.describe()

    def list_roots(self):
        return dict(
            Roots=[ou.describe() for ou in self.ou if isinstance(ou, FakeRoot)]
        )

    def create_organizational_unit(self, **kwargs):
        new_ou = FakeOrganizationalUnit(self.org, **kwargs)
        self.ou.append(new_ou)
        return new_ou.describe()

    def get_organizational_unit_by_id(self, ou_id):
        ou = next((ou for ou in self.ou if ou.id == ou_id), None)
        if ou is None:
            raise RESTError(
                'OrganizationalUnitNotFoundException',
                "You specified an organizational unit that doesn't exist."
            )
        return ou

    def validate_parent_id(self, parent_id):
        try:
            self.get_organizational_unit_by_id(parent_id)
        except RESTError:
            raise RESTError(
                'ParentNotFoundException',
                "You specified parent that doesn't exist."
            )
        return parent_id

    def describe_organizational_unit(self, **kwargs):
        ou = self.get_organizational_unit_by_id(kwargs['OrganizationalUnitId'])
        return ou.describe()

    def list_organizational_units_for_parent(self, **kwargs):
        parent_id = self.validate_parent_id(kwargs['ParentId'])
        return dict(
            OrganizationalUnits=[
                {
                    'Id': ou.id,
                    'Arn': ou.arn,
                    'Name': ou.name,
                }
                for ou in self.ou
                if ou.parent_id == parent_id
            ]
        )

    def create_account(self, **kwargs):
        new_account = FakeAccount(self.org, **kwargs)
        self.accounts.append(new_account)
        return new_account.create_account_status

    def get_account_by_id(self, account_id):
        account = next((
            account for account in self.accounts
            if account.id == account_id
        ), None)
        if account is None:
            raise RESTError(
                'AccountNotFoundException',
                "You specified an account that doesn't exist."
            )
        return account

    def describe_account(self, **kwargs):
        account = self.get_account_by_id(kwargs['AccountId'])
        return account.describe()

    def list_accounts(self):
        return dict(
            Accounts=[account.describe()['Account'] for account in self.accounts]
        )

    def list_accounts_for_parent(self, **kwargs):
        parent_id = self.validate_parent_id(kwargs['ParentId'])
        return dict(
            Accounts=[
                account.describe()['Account']
                for account in self.accounts
                if account.parent_id == parent_id
            ]
        )

    def move_account(self, **kwargs):
        new_parent_id = self.validate_parent_id(kwargs['DestinationParentId'])
        self.validate_parent_id(kwargs['SourceParentId'])
        account = self.get_account_by_id(kwargs['AccountId'])
        index = self.accounts.index(account)
        self.accounts[index].parent_id = new_parent_id

    def list_parents(self, **kwargs):
        if re.compile(r'[0-9]{12}').match(kwargs['ChildId']):
            child_object = self.get_account_by_id(kwargs['ChildId'])
        else:
            child_object = self.get_organizational_unit_by_id(kwargs['ChildId'])
        return dict(
            Parents=[
                {
                    'Id': ou.id,
                    'Type': ou.type,
                }
                for ou in self.ou
                if ou.id == child_object.parent_id
            ]
        )

    def list_children(self, **kwargs):
        parent_id = self.validate_parent_id(kwargs['ParentId'])
        if kwargs['ChildType'] == 'ACCOUNT':
            obj_list = self.accounts
        elif kwargs['ChildType'] == 'ORGANIZATIONAL_UNIT':
            obj_list = self.ou
        else:
            raise RESTError(
                'InvalidInputException',
                'You specified an invalid value.'
            )
        return dict(
            Children=[
                {
                    'Id': obj.id,
                    'Type': kwargs['ChildType'],
                }
                for obj in obj_list
                if obj.parent_id == parent_id
            ]
        )


organizations_backend = OrganizationsBackend()
