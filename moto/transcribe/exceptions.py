"""Exceptions raised by the transcribe service."""

from moto.core.exceptions import ServiceException


class TranscribeException(ServiceException):
    pass


class ConflictException(TranscribeException):
    code = "ConflictException"


class BadRequestException(TranscribeException):
    code = "BadRequestException"
