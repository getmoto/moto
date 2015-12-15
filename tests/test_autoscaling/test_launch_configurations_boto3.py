from __future__ import unicode_literals
import boto3

import sure  # noqa

from moto import mock_autoscaling


@mock_autoscaling
def test_create_launch_configuration():
    client = boto3.client('autoscaling')
    response = client.create_launch_configuration(
        LaunchConfigurationName='tester',
        ImageId='ami-abcd1234',
        InstanceType='t1.micro',
        KeyName='the_keys',
        SecurityGroups=["default", "default2"],
        UserData="This is some user_data",
        InstanceMonitoring={'Enabled': True},
        IamInstanceProfile='arn:aws:iam::123456789012:instance-profile/testing',
        SpotPrice='0.1'
    )
    response['ResponseMetadata']['HTTPStatusCode'].should.equal(200)
