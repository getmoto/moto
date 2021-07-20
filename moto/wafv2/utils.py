import uuid
from collections import namedtuple
from moto.core import ACCOUNT_ID
from typing import Tuple
from uuid import UUID


# https://docs.aws.amazon.com/waf/latest/developerguide/how-aws-waf-works.html - explains --scope (cloudfront vs regional)
def make_arn_for_wacl(name: str, region_name:str , id: UUID, scope: str) -> str:

    if scope == "REGIONAL": scope = "regional"
    elif scope == "CLOUDFRONT": scope = "global"
    return "arn:aws:wafv2:{}:{}:{}/webacl/{}/{}".format(region_name, ACCOUNT_ID, scope, name, id)

# ACCOUNTID: ACCOUNT_ID = os.environ.get("MOTO_ACCOUNT_ID", "123456789012")
