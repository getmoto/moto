def make_arn_for_wacl(
    name: str, account_id: str, region_name: str, wacl_id: str, scope: str
) -> str:
    """https://docs.aws.amazon.com/waf/latest/developerguide/how-aws-waf-works.html - explains --scope (cloudfront vs regional)"""

    if scope == "REGIONAL":
        scope = "regional"
    elif scope == "CLOUDFRONT":
        scope = "global"
    return f"arn:aws:wafv2:{region_name}:{account_id}:{scope}/webacl/{name}/{wacl_id}"
