def make_arn_for_wacl(name, account_id, region_name, wacl_id, scope):
    """https://docs.aws.amazon.com/waf/latest/developerguide/how-aws-waf-works.html - explains --scope (cloudfront vs regional)"""

    if scope == "REGIONAL":
        scope = "regional"
    elif scope == "CLOUDFRONT":
        scope = "global"
    return f"arn:aws:wafv2:{region_name}:{account_id}:{scope}/webacl/{name}/{wacl_id}"
