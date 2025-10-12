import uuid

from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.wafv2.utils import make_arn_for_wacl


def test_make_arn_for_wacl_in_regional_scope():
    uniqueID = str(uuid.uuid4())
    region = "us-east-1"
    name = "testName"
    scope = "REGIONAL"

    arn = make_arn_for_wacl(name, ACCOUNT_ID, region, uniqueID, scope)

    assert (
        arn == f"arn:aws:wafv2:{region}:{ACCOUNT_ID}:regional/webacl/{name}/{uniqueID}"
    )


def test_make_arn_for_wacl_in_cloudfront_scope():
    uniqueID = str(uuid.uuid4())
    backend_region = "aws"  # see https://github.com/getmoto/moto/blob/d00aa025b6c3d37977508b5d5e81ecad4ca15159/moto/core/base_backend.py#L272
    arn_region = "us-east-1"
    name = "testName"
    scope = "CLOUDFRONT"

    arn = make_arn_for_wacl(name, ACCOUNT_ID, backend_region, uniqueID, scope)

    assert (
        arn
        == f"arn:aws:wafv2:{arn_region}:{ACCOUNT_ID}:global/webacl/{name}/{uniqueID}"
    )
