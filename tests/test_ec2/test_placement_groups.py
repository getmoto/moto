import boto
import sure  # flake8: noqa

from moto import mock_ec2


@mock_ec2
def test_placement_groups():
    pass
