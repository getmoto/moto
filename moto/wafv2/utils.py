from moto.core import ACCOUNT_ID

# https://docs.aws.amazon.com/waf/latest/developerguide/how-aws-waf-works.html - explains --scope (cloudfront vs regional)


def make_arn_for_wacl(name, region_name , id, scope):

    if scope == "REGIONAL":
        scope = "regional"
    elif scope == "CLOUDFRONT":
        scope = "global"
    return "arn:aws:wafv2:{}:{}:{}/webacl/{}/{}".format(region_name, ACCOUNT_ID, scope, name, id)

# ACCOUNTID: ACCOUNT_ID = os.environ.get("MOTO_ACCOUNT_ID", "123456789012")
