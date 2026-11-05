"""Exceptions raised by the comprehend service."""

from moto.core.exceptions import ServiceException


class ComprehendException(ServiceException):
    pass


class ResourceNotFound(ComprehendException):
    code = "ResourceNotFoundException"
    message = "RESOURCE_NOT_FOUND: Could not find specified resource."


class DetectPIIValidationException(ComprehendException):
    code = "ValidationException"

    def __init__(self, language: str, all_languages: list[str]) -> None:
        all_languages_str = str(all_languages).replace("'", "")
        super().__init__(
            f"Value '{language}' at 'languageCode'failed to satisfy constraint: "
            f"Member must satisfy enum value set: {all_languages_str}"
        )


class TextSizeLimitExceededException(ComprehendException):
    code = "TextSizeLimitExceededException"

    def __init__(self, size: int) -> None:
        super().__init__(
            "Input text size exceeds limit. Max length of request text allowed is 100000 bytes while in "
            f"this request the text size is {size} bytes"
        )


class InvalidRequestException(ComprehendException):
    code = "InvalidRequestException"
