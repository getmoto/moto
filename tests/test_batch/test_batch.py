from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_batch


@mock_batch
def test_list():
    # do test
    pass