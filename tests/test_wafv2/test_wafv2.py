from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_wafv2


@mock_wafv2
def test_list():
    # do test
    pass