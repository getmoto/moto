from __future__ import unicode_literals
import boto
import sure  # noqa

from moto.ec2 import mock_ec2


@mock_ec2
def test_placement_groups():
    pass
