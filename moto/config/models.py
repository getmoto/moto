import json
import time
import pkg_resources

from datetime import datetime

from boto3 import Session

from moto.config.exceptions import InvalidResourceTypeException, InvalidDeliveryFrequency, \
    InvalidConfigurationRecorderNameException, NameTooLongException, \
    MaxNumberOfConfigurationRecordersExceededException, InvalidRecordingGroupException, \
    NoSuchConfigurationRecorderException, NoAvailableConfigurationRecorderException, \
    InvalidDeliveryChannelNameException, NoSuchBucketException, InvalidS3KeyPrefixException, \
    InvalidSNSTopicARNException, MaxNumberOfDeliveryChannelsExceededException, NoAvailableDeliveryChannelException, \
    NoSuchDeliveryChannelException, LastDeliveryChannelDeleteFailedException

from moto.core import BaseBackend, BaseModel

DEFAULT_ACCOUNT_ID = 123456789012


def datetime2int(date):
    return int(time.mktime(date.timetuple()))


def snake_to_camels(original):
    parts = original.split('_')

    camel_cased = parts[0].lower() + ''.join(p.title() for p in parts[1:])
    camel_cased = camel_cased.replace('Arn', 'ARN')  # Config uses 'ARN' instead of 'Arn'

    return camel_cased


class ConfigEmptyDictable(BaseModel):
    """Base class to make serialization easy. This assumes that the sub-class will NOT return 'None's in the JSON."""

    def to_dict(self):
        data = {}
        for item, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, ConfigEmptyDictable):
                    data[snake_to_camels(item)] = value.to_dict()
                else:
                    data[snake_to_camels(item)] = value

        return data


class ConfigRecorderStatus(ConfigEmptyDictable):

    def __init__(self, name):
        self.name = name

        self.recording = False
        self.last_start_time = None
        self.last_stop_time = None
        self.last_status = None
        self.last_error_code = None
        self.last_error_message = None
        self.last_status_change_time = None

    def start(self):
        self.recording = True
        self.last_status = 'PENDING'
        self.last_start_time = datetime2int(datetime.utcnow())
        self.last_status_change_time = datetime2int(datetime.utcnow())

    def stop(self):
        self.recording = False
        self.last_stop_time = datetime2int(datetime.utcnow())
        self.last_status_change_time = datetime2int(datetime.utcnow())


class ConfigDeliverySnapshotProperties(ConfigEmptyDictable):

    def __init__(self, delivery_frequency):
        self.delivery_frequency = delivery_frequency


class ConfigDeliveryChannel(ConfigEmptyDictable):

    def __init__(self, name, s3_bucket_name, prefix=None, sns_arn=None, snapshot_properties=None):
        self.name = name
        self.s3_bucket_name = s3_bucket_name
        self.s3_key_prefix = prefix
        self.sns_topic_arn = sns_arn
        self.config_snapshot_delivery_properties = snapshot_properties


class RecordingGroup(ConfigEmptyDictable):

    def __init__(self, all_supported=True, include_global_resource_types=False, resource_types=None):
        self.all_supported = all_supported
        self.include_global_resource_types = include_global_resource_types
        self.resource_types = resource_types


class ConfigRecorder(ConfigEmptyDictable):

    def __init__(self, role_arn, recording_group, name='default', status=None):
        self.name = name
        self.role_arn = role_arn
        self.recording_group = recording_group

        if not status:
            self.status = ConfigRecorderStatus(name)
        else:
            self.status = status


class ConfigBackend(BaseBackend):

    def __init__(self):
        self.recorders = {}
        self.delivery_channels = {}

    @staticmethod
    def _validate_resource_types(resource_list):
        # Load the service file:
        resource_package = 'botocore'
        resource_path = '/'.join(('data', 'config', '2014-11-12', 'service-2.json'))
        conifg_schema = json.loads(pkg_resources.resource_string(resource_package, resource_path))

        # Verify that each entry exists in the supported list:
        bad_list = []
        for resource in resource_list:
            # For PY2:
            r_str = str(resource)

            if r_str not in conifg_schema['shapes']['ResourceType']['enum']:
                bad_list.append(r_str)

        if bad_list:
            raise InvalidResourceTypeException(bad_list, conifg_schema['shapes']['ResourceType']['enum'])

    @staticmethod
    def _validate_delivery_snapshot_properties(properties):
        # Load the service file:
        resource_package = 'botocore'
        resource_path = '/'.join(('data', 'config', '2014-11-12', 'service-2.json'))
        conifg_schema = json.loads(pkg_resources.resource_string(resource_package, resource_path))

        # Verify that the deliveryFrequency is set to an acceptable value:
        if properties.get('deliveryFrequency', None) not in \
                conifg_schema['shapes']['MaximumExecutionFrequency']['enum']:
            raise InvalidDeliveryFrequency(properties.get('deliveryFrequency', None),
                                           conifg_schema['shapes']['MaximumExecutionFrequency']['enum'])

    def put_configuration_recorder(self, config_recorder):
        # Validate the name:
        if not config_recorder.get('name'):
            raise InvalidConfigurationRecorderNameException(config_recorder.get('name'))
        if len(config_recorder.get('name')) > 256:
            raise NameTooLongException(config_recorder.get('name'), 'configurationRecorder.name')

        # We're going to assume that the passed in Role ARN is correct.

        # Config currently only allows 1 configuration recorder for an account:
        if len(self.recorders) == 1 and not self.recorders.get(config_recorder['name']):
            raise MaxNumberOfConfigurationRecordersExceededException(config_recorder['name'])

        # Is this updating an existing one?
        recorder_status = None
        if self.recorders.get(config_recorder['name']):
            recorder_status = self.recorders[config_recorder['name']].status

        # Validate the Recording Group:
        if config_recorder.get('recordingGroup') is None:
            recording_group = RecordingGroup()
        else:
            rg = config_recorder['recordingGroup']

            # If an empty dict is passed in, then bad:
            if not rg:
                raise InvalidRecordingGroupException()

            # Can't have both the resource types specified and the other flags as True.
            if rg.get('resourceTypes') and (
                    rg.get('allSupported', False) or
                    rg.get('includeGlobalResourceTypes', False)):
                raise InvalidRecordingGroupException()

            # Must supply resourceTypes if 'allSupported' is not supplied:
            if not rg.get('allSupported') and not rg.get('resourceTypes'):
                raise InvalidRecordingGroupException()

            # Validate that the list provided is correct:
            self._validate_resource_types(rg.get('resourceTypes', []))

            recording_group = RecordingGroup(
                all_supported=rg.get('allSupported', True),
                include_global_resource_types=rg.get('includeGlobalResourceTypes', False),
                resource_types=rg.get('resourceTypes', [])
            )

        self.recorders[config_recorder['name']] = \
            ConfigRecorder(config_recorder['roleARN'], recording_group, name=config_recorder['name'],
                           status=recorder_status)

    def describe_configuration_recorders(self, recorder_names):
        recorders = []

        if recorder_names:
            for rn in recorder_names:
                if not self.recorders.get(rn):
                    raise NoSuchConfigurationRecorderException(rn)

                # Format the recorder:
                recorders.append(self.recorders[rn].to_dict())

        else:
            for recorder in self.recorders.values():
                recorders.append(recorder.to_dict())

        return recorders

    def describe_configuration_recorder_status(self, recorder_names):
        recorders = []

        if recorder_names:
            for rn in recorder_names:
                if not self.recorders.get(rn):
                    raise NoSuchConfigurationRecorderException(rn)

                # Format the recorder:
                recorders.append(self.recorders[rn].status.to_dict())

        else:
            for recorder in self.recorders.values():
                recorders.append(recorder.status.to_dict())

        return recorders

    def put_delivery_channel(self, delivery_channel):
        # Must have a configuration recorder:
        if not self.recorders:
            raise NoAvailableConfigurationRecorderException()

        # Validate the name:
        if not delivery_channel.get('name'):
            raise InvalidDeliveryChannelNameException(delivery_channel.get('name'))
        if len(delivery_channel.get('name')) > 256:
            raise NameTooLongException(delivery_channel.get('name'), 'deliveryChannel.name')

        # We are going to assume that the bucket exists -- but will verify if the bucket provided is blank:
        if not delivery_channel.get('s3BucketName'):
            raise NoSuchBucketException()

        # We are going to assume that the bucket has the correct policy attached to it. We are only going to verify
        # if the prefix provided is not an empty string:
        if delivery_channel.get('s3KeyPrefix', None) == '':
            raise InvalidS3KeyPrefixException()

        # Ditto for SNS -- Only going to assume that the ARN provided is not an empty string:
        if delivery_channel.get('snsTopicARN', None) == '':
            raise InvalidSNSTopicARNException()

        # Config currently only allows 1 delivery channel for an account:
        if len(self.delivery_channels) == 1 and not self.delivery_channels.get(delivery_channel['name']):
            raise MaxNumberOfDeliveryChannelsExceededException(delivery_channel['name'])

        if not delivery_channel.get('configSnapshotDeliveryProperties'):
            dp = None

        else:
            # Validate the config snapshot delivery properties:
            self._validate_delivery_snapshot_properties(delivery_channel['configSnapshotDeliveryProperties'])

            dp = ConfigDeliverySnapshotProperties(
                delivery_channel['configSnapshotDeliveryProperties']['deliveryFrequency'])

        self.delivery_channels[delivery_channel['name']] = \
            ConfigDeliveryChannel(delivery_channel['name'], delivery_channel['s3BucketName'],
                                  prefix=delivery_channel.get('s3KeyPrefix', None),
                                  sns_arn=delivery_channel.get('snsTopicARN', None),
                                  snapshot_properties=dp)

    def describe_delivery_channels(self, channel_names):
        channels = []

        if channel_names:
            for cn in channel_names:
                if not self.delivery_channels.get(cn):
                    raise NoSuchDeliveryChannelException(cn)

                # Format the delivery channel:
                channels.append(self.delivery_channels[cn].to_dict())

        else:
            for channel in self.delivery_channels.values():
                channels.append(channel.to_dict())

        return channels

    def start_configuration_recorder(self, recorder_name):
        if not self.recorders.get(recorder_name):
            raise NoSuchConfigurationRecorderException(recorder_name)

        # Must have a delivery channel available as well:
        if not self.delivery_channels:
            raise NoAvailableDeliveryChannelException()

        # Start recording:
        self.recorders[recorder_name].status.start()

    def stop_configuration_recorder(self, recorder_name):
        if not self.recorders.get(recorder_name):
            raise NoSuchConfigurationRecorderException(recorder_name)

        # Stop recording:
        self.recorders[recorder_name].status.stop()

    def delete_configuration_recorder(self, recorder_name):
        if not self.recorders.get(recorder_name):
            raise NoSuchConfigurationRecorderException(recorder_name)

        del self.recorders[recorder_name]

    def delete_delivery_channel(self, channel_name):
        if not self.delivery_channels.get(channel_name):
            raise NoSuchDeliveryChannelException(channel_name)

        # Check if a channel is recording -- if so, bad -- (there can only be 1 recorder):
        for recorder in self.recorders.values():
            if recorder.status.recording:
                raise LastDeliveryChannelDeleteFailedException(channel_name)

        del self.delivery_channels[channel_name]


config_backends = {}
boto3_session = Session()
for region in boto3_session.get_available_regions('config'):
    config_backends[region] = ConfigBackend()
