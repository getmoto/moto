from moto.wafv2.utils import make_arn, make_webacl_arn


def test_make_arn_ipset():
    arn = make_arn("ipset", "us-west-2", "mytest-ipset")
    assert arn.startswith(
        "arn:aws:wafv2:us-west-2:123456789012:regional/ipset/mytest-ipset/"
    )


def test_make_webacl_arn():
    arn = make_webacl_arn("us-west-1", "mytest-webacl")
    assert arn.startswith(
        "arn:aws:wafv2:us-west-1:123456789012:regional/webacl/mytest-webacl/"
    )
