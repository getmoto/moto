from moto.core.exceptions import JsonRESTError


class NameTooLongException(JsonRESTError):
    code = 400

    def __init__(self, name, location, max_limit=256):
        message = (
            f"1 validation error detected: Value '{name}' at '{location}' "
            f"failed to satisfy constraint: Member must have length less "
            f"than or equal to {max_limit}"
        )
        super().__init__("ValidationException", message)


class InvalidConfigurationRecorderNameException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = "The configuration recorder name '{name}' is not valid, blank string.".format(
            name=name
        )
        super().__init__("InvalidConfigurationRecorderNameException", message)


class MaxNumberOfConfigurationRecordersExceededException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = (
            "Failed to put configuration recorder '{name}' because the maximum number of "
            "configuration recorders: 1 is reached.".format(name=name)
        )
        super().__init__("MaxNumberOfConfigurationRecordersExceededException", message)


class InvalidRecordingGroupException(JsonRESTError):
    code = 400

    def __init__(self):
        message = "The recording group provided is not valid"
        super().__init__("InvalidRecordingGroupException", message)


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

        super().__init__("ValidationException", message)


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
        super().__init__("NoSuchConfigurationAggregatorException", message)


class NoSuchConfigurationRecorderException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = "Cannot find configuration recorder with the specified name '{name}'.".format(
            name=name
        )
        super().__init__("NoSuchConfigurationRecorderException", message)


class InvalidDeliveryChannelNameException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = "The delivery channel name '{name}' is not valid, blank string.".format(
            name=name
        )
        super().__init__("InvalidDeliveryChannelNameException", message)


class NoSuchBucketException(JsonRESTError):
    """We are *only* validating that there is value that is not '' here."""

    code = 400

    def __init__(self):
        message = "Cannot find a S3 bucket with an empty bucket name."
        super().__init__("NoSuchBucketException", message)


class InvalidNextTokenException(JsonRESTError):
    code = 400

    def __init__(self):
        message = "The nextToken provided is invalid"
        super().__init__("InvalidNextTokenException", message)


class InvalidS3KeyPrefixException(JsonRESTError):
    code = 400

    def __init__(self):
        message = "The s3 key prefix '' is not valid, empty s3 key prefix."
        super().__init__("InvalidS3KeyPrefixException", message)


class InvalidSNSTopicARNException(JsonRESTError):
    """We are *only* validating that there is value that is not '' here."""

    code = 400

    def __init__(self):
        message = "The sns topic arn '' is not valid."
        super().__init__("InvalidSNSTopicARNException", message)


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
        super().__init__("InvalidDeliveryFrequency", message)


class MaxNumberOfDeliveryChannelsExceededException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = (
            "Failed to put delivery channel '{name}' because the maximum number of "
            "delivery channels: 1 is reached.".format(name=name)
        )
        super().__init__("MaxNumberOfDeliveryChannelsExceededException", message)


class NoSuchDeliveryChannelException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = "Cannot find delivery channel with specified name '{name}'.".format(
            name=name
        )
        super().__init__("NoSuchDeliveryChannelException", message)


class NoAvailableConfigurationRecorderException(JsonRESTError):
    code = 400

    def __init__(self):
        message = "Configuration recorder is not available to put delivery channel."
        super().__init__("NoAvailableConfigurationRecorderException", message)


class NoAvailableDeliveryChannelException(JsonRESTError):
    code = 400

    def __init__(self):
        message = "Delivery channel is not available to start configuration recorder."
        super().__init__("NoAvailableDeliveryChannelException", message)


class LastDeliveryChannelDeleteFailedException(JsonRESTError):
    code = 400

    def __init__(self, name):
        message = (
            "Failed to delete last specified delivery channel with name '{name}', because there, "
            "because there is a running configuration recorder.".format(name=name)
        )
        super().__init__("LastDeliveryChannelDeleteFailedException", message)


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
        super().__init__("ValidationException", message)


class DuplicateTags(JsonRESTError):
    code = 400

    def __init__(self):
        super().__init__(
            "InvalidInput",
            "Duplicate tag keys found. Please note that Tag keys are case insensitive.",
        )


class TagKeyTooBig(JsonRESTError):
    code = 400

    def __init__(self, tag, param="tags.X.member.key"):
        super().__init__(
            "ValidationException",
            "1 validation error detected: Value '{}' at '{}' failed to satisfy "
            "constraint: Member must have length less than or equal to 128".format(
                tag, param
            ),
        )


class TagValueTooBig(JsonRESTError):
    code = 400

    def __init__(self, tag, param="tags.X.member.value"):
        super().__init__(
            "ValidationException",
            "1 validation error detected: Value '{}' at '{}' failed to satisfy "
            "constraint: Member must have length less than or equal to 256".format(
                tag, param
            ),
        )


class InvalidParameterValueException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("InvalidParameterValueException", message)


class InvalidTagCharacters(JsonRESTError):
    code = 400

    def __init__(self, tag, param="tags.X.member.key"):
        message = "1 validation error detected: Value '{}' at '{}' failed to satisfy ".format(
            tag, param
        )
        message += "constraint: Member must satisfy regular expression pattern: [\\\\p{L}\\\\p{Z}\\\\p{N}_.:/=+\\\\-@]+"

        super().__init__("ValidationException", message)


class TooManyTags(JsonRESTError):
    code = 400

    def __init__(self, tags, param="tags"):
        super().__init__(
            "ValidationException",
            "1 validation error detected: Value '{}' at '{}' failed to satisfy "
            "constraint: Member must have length less than or equal to 50.".format(
                tags, param
            ),
        )


class InvalidResourceParameters(JsonRESTError):
    code = 400

    def __init__(self):
        super().__init__(
            "ValidationException",
            "Both Resource ID and Resource Name " "cannot be specified in the request",
        )


class InvalidLimitException(JsonRESTError):
    code = 400

    def __init__(self, value):
        super().__init__(
            "InvalidLimitException",
            "Value '{value}' at 'limit' failed to satisfy constraint: Member"
            " must have value less than or equal to 100".format(value=value),
        )


class TooManyResourceIds(JsonRESTError):
    code = 400

    def __init__(self):
        super().__init__(
            "ValidationException",
            "The specified list had more than 20 resource ID's. "
            "It must have '20' or less items",
        )


class ResourceNotDiscoveredException(JsonRESTError):
    code = 400

    def __init__(self, resource_type, resource):
        super().__init__(
            "ResourceNotDiscoveredException",
            "Resource {resource} of resourceType:{type} is unknown or has not been "
            "discovered".format(resource=resource, type=resource_type),
        )


class ResourceNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, resource_arn):
        super().__init__(
            "ResourceNotFoundException",
            "ResourceArn '{resource_arn}' does not exist".format(
                resource_arn=resource_arn
            ),
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
        super().__init__("ValidationException", message)


class InvalidResultTokenException(JsonRESTError):
    code = 400

    def __init__(self):
        message = "The resultToken provided is invalid"
        super().__init__("InvalidResultTokenException", message)


class ValidationException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("ValidationException", message)


class NoSuchOrganizationConformancePackException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("NoSuchOrganizationConformancePackException", message)


class MaxNumberOfConfigRulesExceededException(JsonRESTError):
    code = 400

    def __init__(self, name, max_limit):
        message = (
            f"Failed to put config rule '{name}' because the maximum number "
            f"of config rules: {max_limit} is reached."
        )
        super().__init__("MaxNumberOfConfigRulesExceededException", message)


class ResourceInUseException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("ResourceInUseException", message)


class InsufficientPermissionsException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("InsufficientPermissionsException", message)


class NoSuchConfigRuleException(JsonRESTError):
    code = 400

    def __init__(self, rule_name):
        message = (
            f"The ConfigRule '{rule_name}' provided in the request is "
            f"invalid. Please check the configRule name"
        )
        super().__init__("NoSuchConfigRuleException", message)


class MissingRequiredConfigRuleParameterException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("ParamValidationError", message)
