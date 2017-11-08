from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_resourcegroupstaggingapi


@mock_resourcegroupstaggingapi
def test_list():
    # do test
    pass