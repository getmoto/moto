from moto.core.utils import pascal_to_camelcase, camelcase_to_underscores


def make_arn_for_wacl(name, account_id, region_name, wacl_id, scope):
    """https://docs.aws.amazon.com/waf/latest/developerguide/how-aws-waf-works.html - explains --scope (cloudfront vs regional)"""

    if scope == "REGIONAL":
        scope = "regional"
    elif scope == "CLOUDFRONT":
        scope = "global"
    return f"arn:aws:wafv2:{region_name}:{account_id}:{scope}/webacl/{name}/{wacl_id}"


def pascal_to_underscores_dict(original_dict):
    outdict = {}
    for k, v in original_dict.items():
        outdict[camelcase_to_underscores(pascal_to_camelcase(k))] = v
    return outdict
