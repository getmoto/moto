"""
Temporary functions for checking object structures while specing out
models.  This module will go away.
"""

import yaml
from moto import organizations as orgs


# utils
print(orgs.utils.make_random_org_id())
root_id = orgs.utils.make_random_root_id()
print(root_id)
print(orgs.utils.make_random_ou_id(root_id))
print(orgs.utils.make_random_account_id())
print(orgs.utils.make_random_create_account_status_id())

# models
my_org = orgs.models.FakeOrganization(feature_set='ALL')
print(yaml.dump(my_org._describe()))
#assert False

my_account = orgs.models.FakeAccount(my_org, AccountName='blee01', Email='blee01@moto-example.org')
print(yaml.dump(my_account))
#assert False
