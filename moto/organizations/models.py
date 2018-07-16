from __future__ import unicode_literals

import datetime
import re

from moto.core import BaseBackend, BaseModel
from moto.core.utils import unix_time
from moto.organizations import utils

MASTER_ACCOUNT_ID = '123456789012'
MASTER_ACCOUNT_EMAIL = 'fakeorg@moto-example.com'
ORGANIZATION_ARN_FORMAT = 'arn:aws:organizations::{0}:organization/{1}'
MASTER_ACCOUNT_ARN_FORMAT = 'arn:aws:organizations::{0}:account/{1}/{0}'
ACCOUNT_ARN_FORMAT = 'arn:aws:organizations::{0}:account/{1}/{2}'
ROOT_ARN_FORMAT = 'arn:aws:organizations::{0}:root/{1}/{2}'
OU_ARN_FORMAT = 'arn:aws:organizations::{0}:ou/{1}/{2}'


class FakeOrganization(BaseModel):

    def __init__(self, feature_set):
        self.id = utils.make_random_org_id()
        self.root_id = utils.make_random_root_id()
        self.feature_set = feature_set
        self.master_account_id = MASTER_ACCOUNT_ID
        self.master_account_email = MASTER_ACCOUNT_EMAIL
        self.available_policy_types = [{
            'Type': 'SERVICE_CONTROL_POLICY',
            'Status': 'ENABLED'
        }]

    @property
    def arn(self):
        return ORGANIZATION_ARN_FORMAT.format(self.master_account_id, self.id)

    @property
    def master_account_arn(self):
        return MASTER_ACCOUNT_ARN_FORMAT.format(self.master_account_id, self.id)

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
        return ACCOUNT_ARN_FORMAT.format(
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
        self._arn_format = OU_ARN_FORMAT

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
        self._arn_format = ROOT_ARN_FORMAT

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
        return self.org.describe()

    def list_roots(self):
        return dict(
            Roots=[ou.describe() for ou in self.ou if isinstance(ou, FakeRoot)]
        )

    def create_organizational_unit(self, **kwargs):
        new_ou = FakeOrganizationalUnit(self.org, **kwargs)
        self.ou.append(new_ou)
        return new_ou.describe()

    def describe_organizational_unit(self, **kwargs):
        ou = [
            ou for ou in self.ou if ou.id == kwargs['OrganizationalUnitId']
        ].pop(0)
        return ou.describe()

    def list_organizational_units_for_parent(self, **kwargs):
        return dict(
            OrganizationalUnits=[
                {
                    'Id': ou.id,
                    'Arn': ou.arn,
                    'Name': ou.name,
                }
                for ou in self.ou
                if ou.parent_id == kwargs['ParentId']
            ]
        )

    def create_account(self, **kwargs):
        new_account = FakeAccount(self.org, **kwargs)
        self.accounts.append(new_account)
        return new_account.create_account_status

    def describe_account(self, **kwargs):
        account = [
            account for account in self.accounts
            if account.id == kwargs['AccountId']
        ].pop(0)
        return account.describe()

    def list_accounts(self):
        return dict(
            Accounts=[account.describe()['Account'] for account in self.accounts]
        )

    def list_accounts_for_parent(self, **kwargs):
        return dict(
            Accounts=[
                account.describe()['Account']
                for account in self.accounts
                if account.parent_id == kwargs['ParentId']
            ]
        )

    def move_account(self, **kwargs):
        new_parent_id = kwargs['DestinationParentId']
        all_parent_id = [parent.id for parent in self.ou]
        account = [
            account for account in self.accounts
            if account.id == kwargs['AccountId']
        ].pop(0)
        assert new_parent_id in all_parent_id
        assert account.parent_id == kwargs['SourceParentId']
        index = self.accounts.index(account)
        self.accounts[index].parent_id = new_parent_id

    def list_parents(self, **kwargs):
        if re.compile(r'[0-9]{12}').match(kwargs['ChildId']):
            obj_list = self.accounts
        else:
            obj_list = self.ou
        parent_id = [
            obj.parent_id for obj in obj_list
            if obj.id == kwargs['ChildId']
        ].pop(0)
        return dict(
            Parents=[
                {
                    'Id': ou.id,
                    'Type': ou.type,
                }
                for ou in self.ou
                if ou.id == parent_id
            ]
        )

    def list_children(self, **kwargs):
        if kwargs['ChildType'] == 'ACCOUNT':
            obj_list = self.accounts
        elif kwargs['ChildType'] == 'ORGANIZATIONAL_UNIT':
            obj_list = self.ou
        else:
            raise ValueError
        return dict(
            Children=[
                {
                    'Id': obj.id,
                    'Type': kwargs['ChildType'],
                }
                for obj in obj_list
                if obj.parent_id == kwargs['ParentId']
            ]
        )


organizations_backend = OrganizationsBackend()
