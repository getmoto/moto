from __future__ import unicode_literals

import boto3
import sure  # noqa

from moto import mock_ec2

SPOT_REQUEST_CONFIG = {
    'ClientToken': 'string',
    'SpotPrice': '0.12',
    'TargetCapacity': 6,
    'IamFleetRole': 'arn:aws:iam::123456789012:role/fleet',
    'LaunchSpecifications': [{
            'ImageId': 'ami-123',
            'KeyName': 'my-key',
            'SecurityGroups': [
                {
                    'GroupId': 'sg-123'
                },
            ],
            'UserData': 'some user data',
            'InstanceType': 't2.small',
            'BlockDeviceMappings': [
                {
                    'VirtualName': 'string',
                    'DeviceName': 'string',
                    'Ebs': {
                        'SnapshotId': 'string',
                        'VolumeSize': 123,
                        'DeleteOnTermination': True|False,
                        'VolumeType': 'standard',
                        'Iops': 123,
                        'Encrypted': True|False
                    },
                    'NoDevice': 'string'
                },
            ],
            'Monitoring': {
                'Enabled': True
            },
            'SubnetId': 'subnet-1234',
            'IamInstanceProfile': {
                'Arn': 'arn:aws:iam::123456789012:role/fleet'
            },
            'EbsOptimized': False,
            'WeightedCapacity': 2.0,
            'SpotPrice': '0.13'
    }, {
            'ImageId': 'ami-123',
            'KeyName': 'my-key',
            'SecurityGroups': [
                {
                    'GroupId': 'sg-123'
                },
            ],
            'UserData': 'some user data',
            'InstanceType': 't2.large',
            'Monitoring': {
                'Enabled': True
            },
            'SubnetId': 'subnet-1234',
            'IamInstanceProfile': {
                'Arn': 'arn:aws:iam::123456789012:role/fleet'
            },
            'EbsOptimized': False,
            'WeightedCapacity': 4.0,
            'SpotPrice': '10.00',
    }],
    'AllocationStrategy': 'lowestPrice',
    'FulfilledCapacity': 6,
}


@mock_ec2
def test_create_spot_fleet_with_lowest_price():
    conn = boto3.client("ec2", region_name='us-west-2')

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=SPOT_REQUEST_CONFIG
    )
    spot_fleet_id = spot_fleet_res['SpotFleetRequestId']

    spot_fleet_requests = conn.describe_spot_fleet_requests(SpotFleetRequestIds=[spot_fleet_id])['SpotFleetRequestConfigs']
    len(spot_fleet_requests).should.equal(1)
    spot_fleet_request = spot_fleet_requests[0]
    spot_fleet_request['SpotFleetRequestState'].should.equal("active")
    spot_fleet_config = spot_fleet_request['SpotFleetRequestConfig']

    spot_fleet_config['SpotPrice'].should.equal('0.12')
    spot_fleet_config['TargetCapacity'].should.equal(6)
    spot_fleet_config['IamFleetRole'].should.equal('arn:aws:iam::123456789012:role/fleet')
    spot_fleet_config['AllocationStrategy'].should.equal('lowestPrice')
    spot_fleet_config['FulfilledCapacity'].should.equal(6.0)

    len(spot_fleet_config['LaunchSpecifications']).should.equal(2)
    launch_spec = spot_fleet_config['LaunchSpecifications'][0]

    launch_spec['EbsOptimized'].should.equal(False)
    launch_spec['SecurityGroups'].should.equal([{"GroupId": "sg-123"}])
    launch_spec['IamInstanceProfile'].should.equal({"Arn": "arn:aws:iam::123456789012:role/fleet"})
    launch_spec['ImageId'].should.equal("ami-123")
    launch_spec['InstanceType'].should.equal("t2.small")
    launch_spec['KeyName'].should.equal("my-key")
    launch_spec['Monitoring'].should.equal({"Enabled": True})
    launch_spec['SpotPrice'].should.equal("0.13")
    launch_spec['SubnetId'].should.equal("subnet-1234")
    launch_spec['UserData'].should.equal("some user data")
    launch_spec['WeightedCapacity'].should.equal(2.0)

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = instance_res['ActiveInstances']
    len(instances).should.equal(3)


@mock_ec2
def test_create_diversified_spot_fleet():
    conn = boto3.client("ec2", region_name='us-west-2')
    diversified_config = SPOT_REQUEST_CONFIG.copy()
    diversified_config['AllocationStrategy'] = 'diversified'

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=diversified_config
    )
    spot_fleet_id = spot_fleet_res['SpotFleetRequestId']

    instance_res = conn.describe_spot_fleet_instances(SpotFleetRequestId=spot_fleet_id)
    instances = instance_res['ActiveInstances']
    len(instances).should.equal(2)


@mock_ec2
def test_cancel_spot_fleet_request():
    conn = boto3.client("ec2", region_name='us-west-2')

    spot_fleet_res = conn.request_spot_fleet(
        SpotFleetRequestConfig=SPOT_REQUEST_CONFIG,
    )
    spot_fleet_id = spot_fleet_res['SpotFleetRequestId']

    conn.cancel_spot_fleet_requests(SpotFleetRequestIds=[spot_fleet_id], TerminateInstances=True)

    spot_fleet_requests = conn.describe_spot_fleet_requests(SpotFleetRequestIds=[spot_fleet_id])['SpotFleetRequestConfigs']
    len(spot_fleet_requests).should.equal(0)
