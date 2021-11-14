"""Exceptions raised by the cloudtrail service."""
from moto.core import ACCOUNT_ID
from moto.core.exceptions import JsonRESTError


class InvalidParameterCombinationException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidParameterCombinationException, self).__init__(
            "InvalidParameterCombinationException", message
        )


class S3BucketDoesNotExistException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(S3BucketDoesNotExistException, self).__init__(
            "S3BucketDoesNotExistException", message
        )


class InsufficientSnsTopicPolicyException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InsufficientSnsTopicPolicyException, self).__init__(
            "InsufficientSnsTopicPolicyException", message
        )


class TrailNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, name):
        super(TrailNotFoundException, self).__init__(
            "TrailNotFoundException",
            f"Unknown trail: {name} for the user: {ACCOUNT_ID}",
        )


class InvalidTrailNameException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidTrailNameException, self).__init__(
            "InvalidTrailNameException", message
        )


class TrailNameTooShort(InvalidTrailNameException):
    def __init__(self, actual_length):
        super(TrailNameTooShort, self).__init__(
            f"Trail name too short. Minimum allowed length: 3 characters. Specified name length: {actual_length} characters."
        )


class TrailNameTooLong(InvalidTrailNameException):
    def __init__(self, actual_length):
        super(TrailNameTooLong, self).__init__(
            f"Trail name too long. Maximum allowed length: 128 characters. Specified name length: {actual_length} characters."
        )


class TrailNameNotStartingCorrectly(InvalidTrailNameException):
    def __init__(self):
        super(TrailNameNotStartingCorrectly, self).__init__(
            "Trail name must starts with a letter or number."
        )


class TrailNameNotEndingCorrectly(InvalidTrailNameException):
    def __init__(self):
        super(TrailNameNotEndingCorrectly, self).__init__(
            "Trail name must ends with a letter or number."
        )


class TrailNameInvalidChars(InvalidTrailNameException):
    def __init__(self):
        super(TrailNameInvalidChars, self).__init__(
            "Trail name or ARN can only contain uppercase letters, lowercase letters, numbers, periods (.), hyphens (-), and underscores (_)."
        )
