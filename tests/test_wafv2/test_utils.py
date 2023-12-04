import uuid

from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.wafv2.utils import make_arn_for_wacl


def test_make_arn_for_wacl():
    uniqueID = str(uuid.uuid4())
    region = "us-east-1"
    name = "testName"
    scope = "REGIONAL"
    arn = make_arn_for_wacl(name, ACCOUNT_ID, region, uniqueID, scope)
    assert (
        arn == f"arn:aws:wafv2:{region}:{ACCOUNT_ID}:regional/webacl/{name}/{uniqueID}"
    )

    scope = "CLOUDFRONT"
    arn = make_arn_for_wacl(name, ACCOUNT_ID, region, uniqueID, scope)
    assert arn == f"arn:aws:wafv2:{region}:{ACCOUNT_ID}:global/webacl/{name}/{uniqueID}"
