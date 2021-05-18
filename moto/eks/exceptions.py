from __future__ import unicode_literals
from moto.core.exceptions import AWSError


class ResourceInUseException(AWSError):
    TYPE = "ResourceInUseException"
    STATUS = 409


class ResourceNotFoundException(AWSError):
    TYPE = "ResourceNotFoundException"
    STATUS = 404


class ResourceLimitExceededException(AWSError):
    TYPE = "ResourceLimitExceededException"
    STATUS = 400


class InvalidParameterException(AWSError):
    TYPE = "InvalidParameterException"
    STATUS = 400


class InvalidRequestException(AWSError):
    TYPE = "InvalidRequestException"
    STATUS = 400


class ClientException(AWSError):
    TYPE = "ClientException"
    STATUS = 400


class ServerException(AWSError):
    TYPE = "ServerException"
    STATUS = 500


class ServiceUnavailableException(AWSError):
    TYPE = "ServiceUnavailableException"
    STATUS = 503


class UnsupportedAvailabilityZoneException(AWSError):
    TYPE = "UnsupportedAvailabilityZoneException"
    STATUS = 400
