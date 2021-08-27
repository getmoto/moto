from __future__ import unicode_literals

import random
import re
import string
from moto.core import ACCOUNT_ID


MASTER_ACCOUNT_ID = ACCOUNT_ID
MASTER_ACCOUNT_EMAIL = "master@example.com"
DEFAULT_POLICY_ID = "p-FullAWSAccess"
ORGANIZATION_ARN_FORMAT = "arn:aws:organizations::{0}:organization/{1}"
MASTER_ACCOUNT_ARN_FORMAT = "arn:aws:organizations::{0}:account/{1}/{0}"
ACCOUNT_ARN_FORMAT = "arn:aws:organizations::{0}:account/{1}/{2}"
ROOT_ARN_FORMAT = "arn:aws:organizations::{0}:root/{1}/{2}"
OU_ARN_FORMAT = "arn:aws:organizations::{0}:ou/{1}/{2}"
SCP_ARN_FORMAT = "arn:aws:organizations::{0}:policy/{1}/service_control_policy/{2}"
AI_POLICY_ARN_FORMAT = (
    "arn:aws:organizations::{0}:policy/{1}/aiservices_opt_out_policy/{2}"
)

CHARSET = string.ascii_lowercase + string.digits
ORG_ID_SIZE = 10
ROOT_ID_SIZE = 4
ACCOUNT_ID_SIZE = 12
OU_ID_SUFFIX_SIZE = 8
CREATE_ACCOUNT_STATUS_ID_SIZE = 8
POLICY_ID_SIZE = 8

EMAIL_REGEX = "^.+@[a-zA-Z0-9-.]+.[a-zA-Z]{2,3}|[0-9]{1,3}$"
ORG_ID_REGEX = r"o-[a-z0-9]{%s}" % ORG_ID_SIZE
ROOT_ID_REGEX = r"r-[a-z0-9]{%s}" % ROOT_ID_SIZE
OU_ID_REGEX = r"ou-[a-z0-9]{%s}-[a-z0-9]{%s}" % (ROOT_ID_SIZE, OU_ID_SUFFIX_SIZE)
ACCOUNT_ID_REGEX = r"[0-9]{%s}" % ACCOUNT_ID_SIZE
CREATE_ACCOUNT_STATUS_ID_REGEX = r"car-[a-z0-9]{%s}" % CREATE_ACCOUNT_STATUS_ID_SIZE
POLICY_ID_REGEX = r"%s|p-[a-z0-9]{%s}" % (DEFAULT_POLICY_ID, POLICY_ID_SIZE)


def make_random_org_id():
    # The regex pattern for an organization ID string requires "o-"
    # followed by from 10 to 32 lower-case letters or digits.
    # e.g. 'o-vipjnq5z86'
    return "o-" + "".join(random.choice(CHARSET) for x in range(ORG_ID_SIZE))


def make_random_root_id():
    # The regex pattern for a root ID string requires "r-" followed by
    # from 4 to 32 lower-case letters or digits.
    # e.g. 'r-3zwx'
    return "r-" + "".join(random.choice(CHARSET) for x in range(ROOT_ID_SIZE))


def make_random_ou_id(root_id):
    # The regex pattern for an organizational unit ID string requires "ou-"
    # followed by from 4 to 32 lower-case letters or digits (the ID of the root
    # that contains the OU) followed by a second "-" dash and from 8 to 32
    # additional lower-case letters or digits.
    # e.g. ou-g8sd-5oe3bjaw
    return "-".join(
        [
            "ou",
            root_id.partition("-")[2],
            "".join(random.choice(CHARSET) for x in range(OU_ID_SUFFIX_SIZE)),
        ]
    )


def make_random_account_id():
    # The regex pattern for an account ID string requires exactly 12 digits.
    # e.g. '488633172133'
    return "".join([random.choice(string.digits) for n in range(ACCOUNT_ID_SIZE)])


def make_random_create_account_status_id():
    # The regex pattern for an create account request ID string requires
    # "car-" followed by from 8 to 32 lower-case letters or digits.
    # e.g. 'car-35gxzwrp'
    return "car-" + "".join(
        random.choice(CHARSET) for x in range(CREATE_ACCOUNT_STATUS_ID_SIZE)
    )


def make_random_policy_id():
    # The regex pattern for a policy ID string requires "p-" followed by
    # from 8 to 128 lower-case letters or digits.
    # e.g. 'p-k2av4a8a'
    return "p-" + "".join(random.choice(CHARSET) for x in range(POLICY_ID_SIZE))


def fullmatch(regex, s, flags=0):
    """Emulate python-3.4 re.fullmatch()."""
    m = re.match(regex, s, flags=flags)
    if m and m.span()[1] == len(s):
        return m
