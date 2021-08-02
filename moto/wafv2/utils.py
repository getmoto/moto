from moto.core import ACCOUNT_ID
from moto.core.utils import pascal_to_camelcase, camelcase_to_underscores


def make_arn_for_wacl(name, region_name, id, scope):
    """https://docs.aws.amazon.com/waf/latest/developerguide/how-aws-waf-works.html - explains --scope (cloudfront vs regional)"""

    if scope == "REGIONAL":
        scope = "regional"
    elif scope == "CLOUDFRONT":
        scope = "global"
    return "arn:aws:wafv2:{}:{}:{}/webacl/{}/{}".format(
        region_name, ACCOUNT_ID, scope, name, id
    )


def pascal_to_underscores_dict(original_dict):
    outdict = {}
    for k, v in original_dict.items():
        outdict[camelcase_to_underscores(pascal_to_camelcase(k))] = v
    return outdict
