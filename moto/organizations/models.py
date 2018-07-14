from __future__ import unicode_literals

import datetime
import time

from moto.core import BaseBackend, BaseModel
from moto.core.utils import unix_time
from moto.organizations import utils

MASTER_ACCOUNT_ID = '123456789012'
MASTER_ACCOUNT_EMAIL = 'fakeorg@moto-example.com'
ORGANIZATION_ARN_FORMAT = 'arn:aws:organizations::{0}:organization/{1}'
MASTER_ACCOUNT_ARN_FORMAT = 'arn:aws:organizations::{0}:account/{1}/{0}'
ACCOUNT_ARN_FORMAT = 'arn:aws:organizations::{0}:account/{1}/{2}'


class FakeOrganization(BaseModel):

    def __init__(self, feature_set):
        self.id = utils.make_random_org_id()
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

    def _describe(self):
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
        self.account_id = utils.make_random_account_id()
        self.account_name = kwargs['AccountName']
        self.email = kwargs['Email']
        self.create_time = datetime.datetime.utcnow()
        self.status = 'ACTIVE'
        self.joined_method = 'CREATED'

    @property
    def arn(self):
        return ACCOUNT_ARN_FORMAT.format(
            self.master_account_id,
            self.organization_id,
            self.account_id
        )

    @property
    def create_account_status(self):
        return {
            'CreateAccountStatus': {
                'Id': self.create_account_status_id,
                'AccountName': self.account_name,
                'State': 'SUCCEEDED',
                'RequestedTimestamp': unix_time(self.create_time),
                'CompletedTimestamp': unix_time(self.create_time),
                'AccountId': self.account_id,
            }
        }

    def describe(self):
        return {
            'Account': {
                'Id': self.account_id,
                'Arn': self.arn,
                'Email': self.email,
                'Name': self.account_name,
                'Status': self.status,
                'JoinedMethod': self.joined_method,
                'JoinedTimestamp': unix_time(self.create_time),
            }
        }


class OrganizationsBackend(BaseBackend):

    def __init__(self):
        self.org = None
        self.accounts = []

    def create_organization(self, **kwargs):
        self.org = FakeOrganization(kwargs['FeatureSet'])
        return self.org._describe()

    def describe_organization(self):
        return self.org._describe()

    def create_account(self, **kwargs):
        new_account = FakeAccount(self.org, **kwargs)
        self.accounts.append(new_account)
        return new_account.create_account_status

    def describe_account(self, **kwargs):
        account = [account for account in self.accounts 
                   if account.account_id == kwargs['AccountId']][0]
        return account.describe()

    def list_accounts(self):
        return dict(
            Accounts=[account.describe()['Account'] for account in self.accounts]
        )


organizations_backend = OrganizationsBackend()



