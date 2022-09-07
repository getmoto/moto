import uuid

from moto.wafv2.utils import make_arn_for_wacl
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


def test_make_arn_for_wacl():
    uniqueID = str(uuid.uuid4())
    region = "us-east-1"
    name = "testName"
    scope = "REGIONAL"
    arn = make_arn_for_wacl(name, ACCOUNT_ID, region, uniqueID, scope)
    assert arn == "arn:aws:wafv2:{}:{}:regional/webacl/{}/{}".format(
        region, ACCOUNT_ID, name, uniqueID
    )

    scope = "CLOUDFRONT"
    arn = make_arn_for_wacl(name, ACCOUNT_ID, region, uniqueID, scope)
    assert arn == "arn:aws:wafv2:{}:{}:global/webacl/{}/{}".format(
        region, ACCOUNT_ID, name, uniqueID
    )
