from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class NameTooLongException(JsonRESTError):
    code = 400

    def __init__(self, name, location):
        message = '1 validation error detected: Value \'{name}\' at \'{location}\' failed to satisfy' \
                  ' constraint: Member must have length less than or equal to 256'.format(name=name, location=location)
        super(NameTooLongException, self).__init__("ValidationException", message)


class InvalidConfigurationRecorderNameException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = 'The configuration recorder name \'{name}\' is not valid, blank string.'.format(name=name)
        super(InvalidConfigurationRecorderNameException, self).__init__("InvalidConfigurationRecorderNameException",
                                                                        message)


class MaxNumberOfConfigurationRecordersExceededException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = 'Failed to put configuration recorder \'{name}\' because the maximum number of ' \
                  'configuration recorders: 1 is reached.'.format(name=name)
        super(MaxNumberOfConfigurationRecordersExceededException, self).__init__(
            "MaxNumberOfConfigurationRecordersExceededException", message)


class InvalidRecordingGroupException(JsonRESTError):
    code = 400

    def __init__(self):
        message = 'The recording group provided is not valid'
        super(InvalidRecordingGroupException, self).__init__("InvalidRecordingGroupException", message)


class InvalidResourceTypeException(JsonRESTError):
    code = 400

    def __init__(self, bad_list, good_list):
        message = '{num} validation error detected: Value \'{bad_list}\' at ' \
                  '\'configurationRecorder.recordingGroup.resourceTypes\' failed to satisfy constraint: ' \
                  'Member must satisfy constraint: [Member must satisfy enum value set: {good_list}]'.format(
                      num=len(bad_list), bad_list=bad_list, good_list=good_list)
        # For PY2:
        message = str(message)

        super(InvalidResourceTypeException, self).__init__("ValidationException", message)


class NoSuchConfigurationRecorderException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = 'Cannot find configuration recorder with the specified name \'{name}\'.'.format(name=name)
        super(NoSuchConfigurationRecorderException, self).__init__("NoSuchConfigurationRecorderException", message)


class InvalidDeliveryChannelNameException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = 'The delivery channel name \'{name}\' is not valid, blank string.'.format(name=name)
        super(InvalidDeliveryChannelNameException, self).__init__("InvalidDeliveryChannelNameException",
                                                                  message)


class NoSuchBucketException(JsonRESTError):
    """We are *only* validating that there is value that is not '' here."""
    code = 400

    def __init__(self):
        message = 'Cannot find a S3 bucket with an empty bucket name.'
        super(NoSuchBucketException, self).__init__("NoSuchBucketException", message)


class InvalidS3KeyPrefixException(JsonRESTError):
    code = 400

    def __init__(self):
        message = 'The s3 key prefix \'\' is not valid, empty s3 key prefix.'
        super(InvalidS3KeyPrefixException, self).__init__("InvalidS3KeyPrefixException", message)


class InvalidSNSTopicARNException(JsonRESTError):
    """We are *only* validating that there is value that is not '' here."""
    code = 400

    def __init__(self):
        message = 'The sns topic arn \'\' is not valid.'
        super(InvalidSNSTopicARNException, self).__init__("InvalidSNSTopicARNException", message)


class InvalidDeliveryFrequency(JsonRESTError):
    code = 400

    def __init__(self, value, good_list):
        message = '1 validation error detected: Value \'{value}\' at ' \
                  '\'deliveryChannel.configSnapshotDeliveryProperties.deliveryFrequency\' failed to satisfy ' \
                  'constraint: Member must satisfy enum value set: {good_list}'.format(value=value, good_list=good_list)
        super(InvalidDeliveryFrequency, self).__init__("InvalidDeliveryFrequency", message)


class MaxNumberOfDeliveryChannelsExceededException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = 'Failed to put delivery channel \'{name}\' because the maximum number of ' \
                  'delivery channels: 1 is reached.'.format(name=name)
        super(MaxNumberOfDeliveryChannelsExceededException, self).__init__(
            "MaxNumberOfDeliveryChannelsExceededException", message)


class NoSuchDeliveryChannelException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = 'Cannot find delivery channel with specified name \'{name}\'.'.format(name=name)
        super(NoSuchDeliveryChannelException, self).__init__("NoSuchDeliveryChannelException", message)


class NoAvailableConfigurationRecorderException(JsonRESTError):
    code = 400

    def __init__(self):
        message = 'Configuration recorder is not available to put delivery channel.'
        super(NoAvailableConfigurationRecorderException, self).__init__("NoAvailableConfigurationRecorderException",
                                                                        message)


class NoAvailableDeliveryChannelException(JsonRESTError):
    code = 400

    def __init__(self):
        message = 'Delivery channel is not available to start configuration recorder.'
        super(NoAvailableDeliveryChannelException, self).__init__("NoAvailableDeliveryChannelException", message)


class LastDeliveryChannelDeleteFailedException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = 'Failed to delete last specified delivery channel with name \'{name}\', because there, ' \
                  'because there is a running configuration recorder.'.format(name=name)
        super(LastDeliveryChannelDeleteFailedException, self).__init__("LastDeliveryChannelDeleteFailedException", message)
