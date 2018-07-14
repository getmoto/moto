from __future__ import unicode_literals

import sure   # noqa
import moto
from moto.organizations import utils

ORG_ID_REGEX = r'o-[a-z0-9]{%s}' % utils.ORG_ID_SIZE
ROOT_ID_REGEX = r'r-[a-z0-9]{%s}' % utils.ROOT_ID_SIZE
ACCOUNT_ID_REGEX = r'[0-9]{%s}' % utils.ACCOUNT_ID_SIZE
CREATE_ACCOUNT_STATUS_ID_REGEX = r'car-[a-z0-9]{%s}' % utils.CREATE_ACCOUNT_STATUS_ID_SIZE

def test_make_random_org_id():
    org_id = utils.make_random_org_id()
    org_id.should.match(ORG_ID_REGEX)

def test_make_random_root_id():
    org_id = utils.make_random_root_id()
    org_id.should.match(ROOT_ID_REGEX)

def test_make_random_account_id():
    account_id = utils.make_random_account_id()
    account_id.should.match(ACCOUNT_ID_REGEX)

def test_make_random_create_account_status_id():
    create_account_status_id = utils.make_random_create_account_status_id()
    create_account_status_id.should.match(CREATE_ACCOUNT_STATUS_ID_REGEX)
