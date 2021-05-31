import uuid
from collections import namedtuple

ARN = namedtuple("ARN", ["region", "account", "function_name", "version"])


def make_arn(service, region, name):
    return "arn:aws:wafv2:{0}:123456789012:regional/{1}/{2}/{3}".format(
        region, service, name, uuid.uuid4()
    )


def make_webacl_arn(region, name):
    return make_arn("webacl", region, name)
