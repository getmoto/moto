from __future__ import unicode_literals

import random
import string

CHARSET=string.ascii_lowercase + string.digits
ORG_ID_SIZE = 10
ROOT_ID_SIZE = 4
ACCOUNT_ID_SIZE = 12
CREATE_ACCOUNT_STATUS_ID_SIZE = 8


def make_random_org_id():
    # The regex pattern for an organization ID string requires "o-" 
    # followed by from 10 to 32 lower-case letters or digits.
    # e.g. 'o-vipjnq5z86'
    return 'o-' + ''.join(random.choice(CHARSET) for x in range(ORG_ID_SIZE))

def make_random_root_id():
    # The regex pattern for a root ID string requires "r-" followed by 
    # from 4 to 32 lower-case letters or digits.
    # e.g. 'r-3zwx'
    return 'r-' + ''.join(random.choice(CHARSET) for x in range(ROOT_ID_SIZE))

def make_random_account_id():
    # The regex pattern for an account ID string requires exactly 12 digits.
    # e.g. '488633172133'
    return ''.join([random.choice(string.digits) for n in range(ACCOUNT_ID_SIZE)])

def make_random_create_account_status_id():
    # The regex pattern for an create account request ID string requires 
    # "car-" followed by from 8 to 32 lower-case letters or digits.
    # e.g. 'car-35gxzwrp'
    return 'car-' + ''.join(random.choice(CHARSET) for x in range(CREATE_ACCOUNT_STATUS_ID_SIZE))
