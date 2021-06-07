import uuid
from collections import namedtuple
from moto.core import ACCOUNT_ID

ARN = namedtuple("ARN", ["region", "account", "function_name", "version"])


def create_test_name(name):
    return "{0}-{1}".format(name, uuid.uuid4())[0:128]


def make_arn(service, region, name):
    return "arn:aws:wafv2:{0}:{1}:regional/{2}/{3}/{4}".format(
        region, ACCOUNT_ID, service, name, uuid.uuid4()
    )


def make_webacl_arn(region, name):
    return make_arn("webacl", region, name)
