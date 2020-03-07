from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class NameTooLongException(JsonRESTError):
    code = 400

    def __init__(self, name, location):
        message = (
            "1 validation error detected: Value '{name}' at '{location}' failed to satisfy"
            " constraint: Member must have length less than or equal to 256".format(
                name=name, location=location
            )
        )
        super(NameTooLongException, self).__init__("ValidationException", message)


class InvalidConfigurationRecorderNameException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = "The configuration recorder name '{name}' is not valid, blank string.".format(
            name=name
        )
        super(InvalidConfigurationRecorderNameException, self).__init__(
            "InvalidConfigurationRecorderNameException", message
        )


class MaxNumberOfConfigurationRecordersExceededException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = (
            "Failed to put configuration recorder '{name}' because the maximum number of "
            "configuration recorders: 1 is reached.".format(name=name)
        )
        super(MaxNumberOfConfigurationRecordersExceededException, self).__init__(
            "MaxNumberOfConfigurationRecordersExceededException", message
        )


class InvalidRecordingGroupException(JsonRESTError):
    code = 400

    def __init__(self):
        message = "The recording group provided is not valid"
        super(InvalidRecordingGroupException, self).__init__(
            "InvalidRecordingGroupException", message
        )


class InvalidResourceTypeException(JsonRESTError):
    code = 400

    def __init__(self, bad_list, good_list):
        message = (
            "{num} validation error detected: Value '{bad_list}' at "
            "'configurationRecorder.recordingGroup.resourceTypes' failed to satisfy constraint: "
            "Member must satisfy constraint: [Member must satisfy enum value set: {good_list}]".format(
                num=len(bad_list), bad_list=bad_list, good_list=good_list
            )
        )
        # For PY2:
        message = str(message)

        super(InvalidResourceTypeException, self).__init__(
            "ValidationException", message
        )


class NoSuchConfigurationAggregatorException(JsonRESTError):
    code = 400

    def __init__(self, number=1):
        if number == 1:
            message = "The configuration aggregator does not exist. Check the configuration aggregator name and try again."
        else:
            message = (
                "At least one of the configuration aggregators does not exist. Check the configuration aggregator"
                " names and try again."
            )
        super(NoSuchConfigurationAggregatorException, self).__init__(
            "NoSuchConfigurationAggregatorException", message
        )


class NoSuchConfigurationRecorderException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = "Cannot find configuration recorder with the specified name '{name}'.".format(
            name=name
        )
        super(NoSuchConfigurationRecorderException, self).__init__(
            "NoSuchConfigurationRecorderException", message
        )


class InvalidDeliveryChannelNameException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = "The delivery channel name '{name}' is not valid, blank string.".format(
            name=name
        )
        super(InvalidDeliveryChannelNameException, self).__init__(
            "InvalidDeliveryChannelNameException", message
        )


class NoSuchBucketException(JsonRESTError):
    """We are *only* validating that there is value that is not '' here."""

    code = 400

    def __init__(self):
        message = "Cannot find a S3 bucket with an empty bucket name."
        super(NoSuchBucketException, self).__init__("NoSuchBucketException", message)


class InvalidNextTokenException(JsonRESTError):
    code = 400

    def __init__(self):
        message = "The nextToken provided is invalid"
        super(InvalidNextTokenException, self).__init__(
            "InvalidNextTokenException", message
        )


class InvalidS3KeyPrefixException(JsonRESTError):
    code = 400

    def __init__(self):
        message = "The s3 key prefix '' is not valid, empty s3 key prefix."
        super(InvalidS3KeyPrefixException, self).__init__(
            "InvalidS3KeyPrefixException", message
        )


class InvalidSNSTopicARNException(JsonRESTError):
    """We are *only* validating that there is value that is not '' here."""

    code = 400

    def __init__(self):
        message = "The sns topic arn '' is not valid."
        super(InvalidSNSTopicARNException, self).__init__(
            "InvalidSNSTopicARNException", message
        )


class InvalidDeliveryFrequency(JsonRESTError):
    code = 400

    def __init__(self, value, good_list):
        message = (
            "1 validation error detected: Value '{value}' at "
            "'deliveryChannel.configSnapshotDeliveryProperties.deliveryFrequency' failed to satisfy "
            "constraint: Member must satisfy enum value set: {good_list}".format(
                value=value, good_list=good_list
            )
        )
        super(InvalidDeliveryFrequency, self).__init__(
            "InvalidDeliveryFrequency", message
        )


class MaxNumberOfDeliveryChannelsExceededException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = (
            "Failed to put delivery channel '{name}' because the maximum number of "
            "delivery channels: 1 is reached.".format(name=name)
        )
        super(MaxNumberOfDeliveryChannelsExceededException, self).__init__(
            "MaxNumberOfDeliveryChannelsExceededException", message
        )


class NoSuchDeliveryChannelException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = "Cannot find delivery channel with specified name '{name}'.".format(
            name=name
        )
        super(NoSuchDeliveryChannelException, self).__init__(
            "NoSuchDeliveryChannelException", message
        )


class NoAvailableConfigurationRecorderException(JsonRESTError):
    code = 400

    def __init__(self):
        message = "Configuration recorder is not available to put delivery channel."
        super(NoAvailableConfigurationRecorderException, self).__init__(
            "NoAvailableConfigurationRecorderException", message
        )


class NoAvailableDeliveryChannelException(JsonRESTError):
    code = 400

    def __init__(self):
        message = "Delivery channel is not available to start configuration recorder."
        super(NoAvailableDeliveryChannelException, self).__init__(
            "NoAvailableDeliveryChannelException", message
        )


class LastDeliveryChannelDeleteFailedException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = (
            "Failed to delete last specified delivery channel with name '{name}', because there, "
            "because there is a running configuration recorder.".format(name=name)
        )
        super(LastDeliveryChannelDeleteFailedException, self).__init__(
            "LastDeliveryChannelDeleteFailedException", message
        )


class TooManyAccountSources(JsonRESTError):
    code = 400

    def __init__(self, length):
        locations = ["com.amazonaws.xyz"] * length

        message = (
            "Value '[{locations}]' at 'accountAggregationSources' failed to satisfy constraint: "
            "Member must have length less than or equal to 1".format(
                locations=", ".join(locations)
            )
        )
        super(TooManyAccountSources, self).__init__("ValidationException", message)


class DuplicateTags(JsonRESTError):
    code = 400

    def __init__(self):
        super(DuplicateTags, self).__init__(
            "InvalidInput",
            "Duplicate tag keys found. Please note that Tag keys are case insensitive.",
        )


class TagKeyTooBig(JsonRESTError):
    code = 400

    def __init__(self, tag, param="tags.X.member.key"):
        super(TagKeyTooBig, self).__init__(
            "ValidationException",
            "1 validation error detected: Value '{}' at '{}' failed to satisfy "
            "constraint: Member must have length less than or equal to 128".format(
                tag, param
            ),
        )


class TagValueTooBig(JsonRESTError):
    code = 400

    def __init__(self, tag):
        super(TagValueTooBig, self).__init__(
            "ValidationException",
            "1 validation error detected: Value '{}' at 'tags.X.member.value' failed to satisfy "
            "constraint: Member must have length less than or equal to 256".format(tag),
        )


class InvalidParameterValueException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidParameterValueException, self).__init__(
            "InvalidParameterValueException", message
        )


class InvalidTagCharacters(JsonRESTError):
    code = 400

    def __init__(self, tag, param="tags.X.member.key"):
        message = "1 validation error detected: Value '{}' at '{}' failed to satisfy ".format(
            tag, param
        )
        message += "constraint: Member must satisfy regular expression pattern: [\\\\p{L}\\\\p{Z}\\\\p{N}_.:/=+\\\\-@]+"

        super(InvalidTagCharacters, self).__init__("ValidationException", message)


class TooManyTags(JsonRESTError):
    code = 400

    def __init__(self, tags, param="tags"):
        super(TooManyTags, self).__init__(
            "ValidationException",
            "1 validation error detected: Value '{}' at '{}' failed to satisfy "
            "constraint: Member must have length less than or equal to 50.".format(
                tags, param
            ),
        )


class InvalidResourceParameters(JsonRESTError):
    code = 400

    def __init__(self):
        super(InvalidResourceParameters, self).__init__(
            "ValidationException",
            "Both Resource ID and Resource Name " "cannot be specified in the request",
        )


class InvalidLimit(JsonRESTError):
    code = 400

    def __init__(self, value):
        super(InvalidLimit, self).__init__(
            "ValidationException",
            "Value '{value}' at 'limit' failed to satisify constraint: Member"
            " must have value less than or equal to 100".format(value=value),
        )


class TooManyResourceIds(JsonRESTError):
    code = 400

    def __init__(self):
        super(TooManyResourceIds, self).__init__(
            "ValidationException",
            "The specified list had more than 20 resource ID's. "
            "It must have '20' or less items",
        )


class ResourceNotDiscoveredException(JsonRESTError):
    code = 400

    def __init__(self, type, resource):
        super(ResourceNotDiscoveredException, self).__init__(
            "ResourceNotDiscoveredException",
            "Resource {resource} of resourceType:{type} is unknown or has not been "
            "discovered".format(resource=resource, type=type),
        )


class TooManyResourceKeys(JsonRESTError):
    code = 400

    def __init__(self, bad_list):
        message = (
            "1 validation error detected: Value '{bad_list}' at "
            "'resourceKeys' failed to satisfy constraint: "
            "Member must have length less than or equal to 100".format(
                bad_list=bad_list
            )
        )
        # For PY2:
        message = str(message)

        super(TooManyResourceKeys, self).__init__("ValidationException", message)


class InvalidResultTokenException(JsonRESTError):
    code = 400

    def __init__(self):
        message = "The resultToken provided is invalid"
        super(InvalidResultTokenException, self).__init__(
            "InvalidResultTokenException", message
        )
