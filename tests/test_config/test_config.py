from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError
from nose.tools import assert_raises

from moto.config import mock_config


@mock_config
def test_put_configuration_recorder():
    client = boto3.client('config', region_name='us-west-2')

    # Try without a name supplied:
    with assert_raises(ClientError) as ce:
        client.put_configuration_recorder(ConfigurationRecorder={'roleARN': 'somearn'})
    assert ce.exception.response['Error']['Code'] == 'InvalidConfigurationRecorderNameException'
    assert 'is not valid, blank string.' in ce.exception.response['Error']['Message']

    # Try with a really long name:
    with assert_raises(ClientError) as ce:
        client.put_configuration_recorder(ConfigurationRecorder={'name': 'a' * 257, 'roleARN': 'somearn'})
    assert ce.exception.response['Error']['Code'] == 'ValidationException'
    assert 'Member must have length less than or equal to 256' in ce.exception.response['Error']['Message']

    # With resource types and flags set to True:
    bad_groups = [
        {'allSupported': True, 'includeGlobalResourceTypes': True, 'resourceTypes': ['item']},
        {'allSupported': False, 'includeGlobalResourceTypes': True, 'resourceTypes': ['item']},
        {'allSupported': True, 'includeGlobalResourceTypes': False, 'resourceTypes': ['item']},
        {'allSupported': False, 'includeGlobalResourceTypes': False, 'resourceTypes': []},
        {'includeGlobalResourceTypes': False, 'resourceTypes': []},
        {'includeGlobalResourceTypes': True},
        {'resourceTypes': []},
        {}
    ]

    for bg in bad_groups:
        with assert_raises(ClientError) as ce:
            client.put_configuration_recorder(ConfigurationRecorder={
                'name': 'default',
                'roleARN': 'somearn',
                'recordingGroup': bg
            })
        assert ce.exception.response['Error']['Code'] == 'InvalidRecordingGroupException'
        assert ce.exception.response['Error']['Message'] == 'The recording group provided is not valid'

    # With an invalid Resource Type:
    with assert_raises(ClientError) as ce:
        client.put_configuration_recorder(ConfigurationRecorder={
            'name': 'default',
            'roleARN': 'somearn',
            'recordingGroup': {
                'allSupported': False,
                'includeGlobalResourceTypes': False,
                # 2 good, and 2 bad:
                'resourceTypes': ['AWS::EC2::Volume', 'LOLNO', 'AWS::EC2::VPC', 'LOLSTILLNO']
            }
        })
    assert ce.exception.response['Error']['Code'] == 'ValidationException'
    assert "2 validation error detected: Value '['LOLNO', 'LOLSTILLNO']" in str(ce.exception.response['Error']['Message'])
    assert 'AWS::EC2::Instance' in ce.exception.response['Error']['Message']

    # Create a proper one:
    client.put_configuration_recorder(ConfigurationRecorder={
        'name': 'testrecorder',
        'roleARN': 'somearn',
        'recordingGroup': {
            'allSupported': False,
            'includeGlobalResourceTypes': False,
            'resourceTypes': ['AWS::EC2::Volume', 'AWS::EC2::VPC']
        }
    })

    result = client.describe_configuration_recorders()['ConfigurationRecorders']
    assert len(result) == 1
    assert result[0]['name'] == 'testrecorder'
    assert result[0]['roleARN'] == 'somearn'
    assert not result[0]['recordingGroup']['allSupported']
    assert not result[0]['recordingGroup']['includeGlobalResourceTypes']
    assert len(result[0]['recordingGroup']['resourceTypes']) == 2
    assert 'AWS::EC2::Volume' in result[0]['recordingGroup']['resourceTypes'] \
           and 'AWS::EC2::VPC' in result[0]['recordingGroup']['resourceTypes']

    # Now update the configuration recorder:
    client.put_configuration_recorder(ConfigurationRecorder={
        'name': 'testrecorder',
        'roleARN': 'somearn',
        'recordingGroup': {
            'allSupported': True,
            'includeGlobalResourceTypes': True
        }
    })
    result = client.describe_configuration_recorders()['ConfigurationRecorders']
    assert len(result) == 1
    assert result[0]['name'] == 'testrecorder'
    assert result[0]['roleARN'] == 'somearn'
    assert result[0]['recordingGroup']['allSupported']
    assert result[0]['recordingGroup']['includeGlobalResourceTypes']
    assert len(result[0]['recordingGroup']['resourceTypes']) == 0

    # With a default recording group (i.e. lacking one)
    client.put_configuration_recorder(ConfigurationRecorder={'name': 'testrecorder', 'roleARN': 'somearn'})
    result = client.describe_configuration_recorders()['ConfigurationRecorders']
    assert len(result) == 1
    assert result[0]['name'] == 'testrecorder'
    assert result[0]['roleARN'] == 'somearn'
    assert result[0]['recordingGroup']['allSupported']
    assert not result[0]['recordingGroup']['includeGlobalResourceTypes']
    assert not result[0]['recordingGroup'].get('resourceTypes')

    # Can currently only have exactly 1 Config Recorder in an account/region:
    with assert_raises(ClientError) as ce:
        client.put_configuration_recorder(ConfigurationRecorder={
            'name': 'someotherrecorder',
            'roleARN': 'somearn',
            'recordingGroup': {
                'allSupported': False,
                'includeGlobalResourceTypes': False,
            }
        })
    assert ce.exception.response['Error']['Code'] == 'MaxNumberOfConfigurationRecordersExceededException'
    assert "maximum number of configuration recorders: 1 is reached." in ce.exception.response['Error']['Message']


@mock_config
def test_describe_configurations():
    client = boto3.client('config', region_name='us-west-2')

    # Without any configurations:
    result = client.describe_configuration_recorders()
    assert not result['ConfigurationRecorders']

    client.put_configuration_recorder(ConfigurationRecorder={
        'name': 'testrecorder',
        'roleARN': 'somearn',
        'recordingGroup': {
            'allSupported': False,
            'includeGlobalResourceTypes': False,
            'resourceTypes': ['AWS::EC2::Volume', 'AWS::EC2::VPC']
        }
    })

    result = client.describe_configuration_recorders()['ConfigurationRecorders']
    assert len(result) == 1
    assert result[0]['name'] == 'testrecorder'
    assert result[0]['roleARN'] == 'somearn'
    assert not result[0]['recordingGroup']['allSupported']
    assert not result[0]['recordingGroup']['includeGlobalResourceTypes']
    assert len(result[0]['recordingGroup']['resourceTypes']) == 2
    assert 'AWS::EC2::Volume' in result[0]['recordingGroup']['resourceTypes'] \
           and 'AWS::EC2::VPC' in result[0]['recordingGroup']['resourceTypes']

    # Specify an incorrect name:
    with assert_raises(ClientError) as ce:
        client.describe_configuration_recorders(ConfigurationRecorderNames=['wrong'])
    assert ce.exception.response['Error']['Code'] == 'NoSuchConfigurationRecorderException'
    assert 'wrong' in ce.exception.response['Error']['Message']

    # And with both a good and wrong name:
    with assert_raises(ClientError) as ce:
        client.describe_configuration_recorders(ConfigurationRecorderNames=['testrecorder', 'wrong'])
    assert ce.exception.response['Error']['Code'] == 'NoSuchConfigurationRecorderException'
    assert 'wrong' in ce.exception.response['Error']['Message']


@mock_config
def test_delivery_channels():
    client = boto3.client('config', region_name='us-west-2')

    # Try without a config recorder:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={})
    assert ce.exception.response['Error']['Code'] == 'NoAvailableConfigurationRecorderException'
    assert ce.exception.response['Error']['Message'] == 'Configuration recorder is not available to ' \
                                                        'put delivery channel.'

    # Create a config recorder to continue testing:
    client.put_configuration_recorder(ConfigurationRecorder={
        'name': 'testrecorder',
        'roleARN': 'somearn',
        'recordingGroup': {
            'allSupported': False,
            'includeGlobalResourceTypes': False,
            'resourceTypes': ['AWS::EC2::Volume', 'AWS::EC2::VPC']
        }
    })

    # Try without a name supplied:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={})
    assert ce.exception.response['Error']['Code'] == 'InvalidDeliveryChannelNameException'
    assert 'is not valid, blank string.' in ce.exception.response['Error']['Message']

    # Try with a really long name:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={'name': 'a' * 257})
    assert ce.exception.response['Error']['Code'] == 'ValidationException'
    assert 'Member must have length less than or equal to 256' in ce.exception.response['Error']['Message']

    # Without specifying a bucket name:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={'name': 'testchannel'})
    assert ce.exception.response['Error']['Code'] == 'NoSuchBucketException'
    assert ce.exception.response['Error']['Message'] == 'Cannot find a S3 bucket with an empty bucket name.'

    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={'name': 'testchannel', 's3BucketName': ''})
    assert ce.exception.response['Error']['Code'] == 'NoSuchBucketException'
    assert ce.exception.response['Error']['Message'] == 'Cannot find a S3 bucket with an empty bucket name.'

    # With an empty string for the S3 key prefix:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={
            'name': 'testchannel', 's3BucketName': 'somebucket', 's3KeyPrefix': ''})
    assert ce.exception.response['Error']['Code'] == 'InvalidS3KeyPrefixException'
    assert 'empty s3 key prefix.' in ce.exception.response['Error']['Message']

    # With an empty string for the SNS ARN:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={
            'name': 'testchannel', 's3BucketName': 'somebucket', 'snsTopicARN': ''})
    assert ce.exception.response['Error']['Code'] == 'InvalidSNSTopicARNException'
    assert 'The sns topic arn' in ce.exception.response['Error']['Message']

    # With an invalid delivery frequency:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={
            'name': 'testchannel',
            's3BucketName': 'somebucket',
            'configSnapshotDeliveryProperties': {'deliveryFrequency': 'WRONG'}
        })
    assert ce.exception.response['Error']['Code'] == 'InvalidDeliveryFrequency'
    assert 'WRONG' in ce.exception.response['Error']['Message']
    assert 'TwentyFour_Hours' in ce.exception.response['Error']['Message']

    # Create a proper one:
    client.put_delivery_channel(DeliveryChannel={'name': 'testchannel', 's3BucketName': 'somebucket'})
    result = client.describe_delivery_channels()['DeliveryChannels']
    assert len(result) == 1
    assert len(result[0].keys()) == 2
    assert result[0]['name'] == 'testchannel'
    assert result[0]['s3BucketName'] == 'somebucket'

    # Overwrite it with another proper configuration:
    client.put_delivery_channel(DeliveryChannel={
        'name': 'testchannel',
        's3BucketName': 'somebucket',
        'snsTopicARN': 'sometopicarn',
        'configSnapshotDeliveryProperties': {'deliveryFrequency': 'TwentyFour_Hours'}
    })
    result = client.describe_delivery_channels()['DeliveryChannels']
    assert len(result) == 1
    assert len(result[0].keys()) == 4
    assert result[0]['name'] == 'testchannel'
    assert result[0]['s3BucketName'] == 'somebucket'
    assert result[0]['snsTopicARN'] == 'sometopicarn'
    assert result[0]['configSnapshotDeliveryProperties']['deliveryFrequency'] == 'TwentyFour_Hours'

    # Can only have 1:
    with assert_raises(ClientError) as ce:
        client.put_delivery_channel(DeliveryChannel={'name': 'testchannel2', 's3BucketName': 'somebucket'})
    assert ce.exception.response['Error']['Code'] == 'MaxNumberOfDeliveryChannelsExceededException'
    assert 'because the maximum number of delivery channels: 1 is reached.' in ce.exception.response['Error']['Message']


@mock_config
def test_describe_delivery_channels():
    client = boto3.client('config', region_name='us-west-2')
    client.put_configuration_recorder(ConfigurationRecorder={
        'name': 'testrecorder',
        'roleARN': 'somearn',
        'recordingGroup': {
            'allSupported': False,
            'includeGlobalResourceTypes': False,
            'resourceTypes': ['AWS::EC2::Volume', 'AWS::EC2::VPC']
        }
    })

    # Without any channels:
    result = client.describe_delivery_channels()
    assert not result['DeliveryChannels']

    client.put_delivery_channel(DeliveryChannel={'name': 'testchannel', 's3BucketName': 'somebucket'})
    result = client.describe_delivery_channels()['DeliveryChannels']
    assert len(result) == 1
    assert len(result[0].keys()) == 2
    assert result[0]['name'] == 'testchannel'
    assert result[0]['s3BucketName'] == 'somebucket'

    # Overwrite it with another proper configuration:
    client.put_delivery_channel(DeliveryChannel={
        'name': 'testchannel',
        's3BucketName': 'somebucket',
        'snsTopicARN': 'sometopicarn',
        'configSnapshotDeliveryProperties': {'deliveryFrequency': 'TwentyFour_Hours'}
    })
    result = client.describe_delivery_channels()['DeliveryChannels']
    assert len(result) == 1
    assert len(result[0].keys()) == 4
    assert result[0]['name'] == 'testchannel'
    assert result[0]['s3BucketName'] == 'somebucket'
    assert result[0]['snsTopicARN'] == 'sometopicarn'
    assert result[0]['configSnapshotDeliveryProperties']['deliveryFrequency'] == 'TwentyFour_Hours'

    # Specify an incorrect name:
    with assert_raises(ClientError) as ce:
        client.describe_delivery_channels(DeliveryChannelNames=['wrong'])
    assert ce.exception.response['Error']['Code'] == 'NoSuchDeliveryChannelException'
    assert 'wrong' in ce.exception.response['Error']['Message']

    # And with both a good and wrong name:
    with assert_raises(ClientError) as ce:
        client.describe_delivery_channels(DeliveryChannelNames=['testchannel', 'wrong'])
    assert ce.exception.response['Error']['Code'] == 'NoSuchDeliveryChannelException'
    assert 'wrong' in ce.exception.response['Error']['Message']


@mock_config
def test_start_configuration_recorder():
    client = boto3.client('config', region_name='us-west-2')

    # Without a config recorder:
    with assert_raises(ClientError) as ce:
        client.start_configuration_recorder(ConfigurationRecorderName='testrecorder')
    assert ce.exception.response['Error']['Code'] == 'NoSuchConfigurationRecorderException'

    # Make the config recorder;
    client.put_configuration_recorder(ConfigurationRecorder={
        'name': 'testrecorder',
        'roleARN': 'somearn',
        'recordingGroup': {
            'allSupported': False,
            'includeGlobalResourceTypes': False,
            'resourceTypes': ['AWS::EC2::Volume', 'AWS::EC2::VPC']
        }
    })

    # Without a delivery channel:
    with assert_raises(ClientError) as ce:
        client.start_configuration_recorder(ConfigurationRecorderName='testrecorder')
    assert ce.exception.response['Error']['Code'] == 'NoAvailableDeliveryChannelException'

    # Make the delivery channel:
    client.put_delivery_channel(DeliveryChannel={'name': 'testchannel', 's3BucketName': 'somebucket'})

    # Start it:
    client.start_configuration_recorder(ConfigurationRecorderName='testrecorder')

    # Verify it's enabled:
    result = client.describe_configuration_recorder_status()['ConfigurationRecordersStatus']
    lower_bound = (datetime.utcnow() - timedelta(minutes=5))
    assert result[0]['recording']
    assert result[0]['lastStatus'] == 'PENDING'
    assert lower_bound < result[0]['lastStartTime'].replace(tzinfo=None) <= datetime.utcnow()
    assert lower_bound < result[0]['lastStatusChangeTime'].replace(tzinfo=None) <= datetime.utcnow()


@mock_config
def test_stop_configuration_recorder():
    client = boto3.client('config', region_name='us-west-2')

    # Without a config recorder:
    with assert_raises(ClientError) as ce:
        client.stop_configuration_recorder(ConfigurationRecorderName='testrecorder')
    assert ce.exception.response['Error']['Code'] == 'NoSuchConfigurationRecorderException'

    # Make the config recorder;
    client.put_configuration_recorder(ConfigurationRecorder={
        'name': 'testrecorder',
        'roleARN': 'somearn',
        'recordingGroup': {
            'allSupported': False,
            'includeGlobalResourceTypes': False,
            'resourceTypes': ['AWS::EC2::Volume', 'AWS::EC2::VPC']
        }
    })

    # Make the delivery channel for creation:
    client.put_delivery_channel(DeliveryChannel={'name': 'testchannel', 's3BucketName': 'somebucket'})

    # Start it:
    client.start_configuration_recorder(ConfigurationRecorderName='testrecorder')
    client.stop_configuration_recorder(ConfigurationRecorderName='testrecorder')

    # Verify it's disabled:
    result = client.describe_configuration_recorder_status()['ConfigurationRecordersStatus']
    lower_bound = (datetime.utcnow() - timedelta(minutes=5))
    assert not result[0]['recording']
    assert result[0]['lastStatus'] == 'PENDING'
    assert lower_bound < result[0]['lastStartTime'].replace(tzinfo=None) <= datetime.utcnow()
    assert lower_bound < result[0]['lastStopTime'].replace(tzinfo=None) <= datetime.utcnow()
    assert lower_bound < result[0]['lastStatusChangeTime'].replace(tzinfo=None) <= datetime.utcnow()


@mock_config
def test_describe_configuration_recorder_status():
    client = boto3.client('config', region_name='us-west-2')

    # Without any:
    result = client.describe_configuration_recorder_status()
    assert not result['ConfigurationRecordersStatus']

    # Make the config recorder;
    client.put_configuration_recorder(ConfigurationRecorder={
        'name': 'testrecorder',
        'roleARN': 'somearn',
        'recordingGroup': {
            'allSupported': False,
            'includeGlobalResourceTypes': False,
            'resourceTypes': ['AWS::EC2::Volume', 'AWS::EC2::VPC']
        }
    })

    # Without specifying a config recorder:
    result = client.describe_configuration_recorder_status()['ConfigurationRecordersStatus']
    assert len(result) == 1
    assert result[0]['name'] == 'testrecorder'
    assert not result[0]['recording']

    # With a proper name:
    result = client.describe_configuration_recorder_status(
        ConfigurationRecorderNames=['testrecorder'])['ConfigurationRecordersStatus']
    assert len(result) == 1
    assert result[0]['name'] == 'testrecorder'
    assert not result[0]['recording']

    # Invalid name:
    with assert_raises(ClientError) as ce:
        client.describe_configuration_recorder_status(ConfigurationRecorderNames=['testrecorder', 'wrong'])
    assert ce.exception.response['Error']['Code'] == 'NoSuchConfigurationRecorderException'
    assert 'wrong' in ce.exception.response['Error']['Message']


@mock_config
def test_delete_configuration_recorder():
    client = boto3.client('config', region_name='us-west-2')

    # Make the config recorder;
    client.put_configuration_recorder(ConfigurationRecorder={
        'name': 'testrecorder',
        'roleARN': 'somearn',
        'recordingGroup': {
            'allSupported': False,
            'includeGlobalResourceTypes': False,
            'resourceTypes': ['AWS::EC2::Volume', 'AWS::EC2::VPC']
        }
    })

    # Delete it:
    client.delete_configuration_recorder(ConfigurationRecorderName='testrecorder')

    # Try again -- it should be deleted:
    with assert_raises(ClientError) as ce:
        client.delete_configuration_recorder(ConfigurationRecorderName='testrecorder')
    assert ce.exception.response['Error']['Code'] == 'NoSuchConfigurationRecorderException'


@mock_config
def test_delete_delivery_channel():
    client = boto3.client('config', region_name='us-west-2')

    # Need a recorder to test the constraint on recording being enabled:
    client.put_configuration_recorder(ConfigurationRecorder={
        'name': 'testrecorder',
        'roleARN': 'somearn',
        'recordingGroup': {
            'allSupported': False,
            'includeGlobalResourceTypes': False,
            'resourceTypes': ['AWS::EC2::Volume', 'AWS::EC2::VPC']
        }
    })
    client.put_delivery_channel(DeliveryChannel={'name': 'testchannel', 's3BucketName': 'somebucket'})
    client.start_configuration_recorder(ConfigurationRecorderName='testrecorder')

    # With the recorder enabled:
    with assert_raises(ClientError) as ce:
        client.delete_delivery_channel(DeliveryChannelName='testchannel')
    assert ce.exception.response['Error']['Code'] == 'LastDeliveryChannelDeleteFailedException'
    assert 'because there is a running configuration recorder.' in ce.exception.response['Error']['Message']

    # Stop recording:
    client.stop_configuration_recorder(ConfigurationRecorderName='testrecorder')

    # Try again:
    client.delete_delivery_channel(DeliveryChannelName='testchannel')

    # Verify:
    with assert_raises(ClientError) as ce:
        client.delete_delivery_channel(DeliveryChannelName='testchannel')
    assert ce.exception.response['Error']['Code'] == 'NoSuchDeliveryChannelException'
