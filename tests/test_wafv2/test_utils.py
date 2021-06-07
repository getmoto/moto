import random
import string

from moto.wafv2 import utils
from moto.wafv2.utils import make_arn, make_webacl_arn


def test_create_test_name_length_limit_128():
    longname = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(150)
    )
    assert len(longname) > 128
    created_name = utils.create_test_name(longname)
    assert len(created_name) == 128


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
