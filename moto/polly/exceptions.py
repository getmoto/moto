from moto.core.exceptions import ServiceException


class PollyException(ServiceException):
    pass


class InvalidParameterValue(PollyException):
    code = "InvalidParameterValue"


class InvalidSampleRateException(PollyException):
    code = "InvalidSampleRateException"
    message = "The specified sample rate is not valid."


class LexiconNotFoundException(PollyException):
    code = "LexiconNotFoundException"
    message = "Lexicon not found"


class MarksNotSupportedForFormatException(PollyException):
    code = "MarksNotSupportedForFormatException"
    message = "OutputFormat must be json"


class MissingParameter(PollyException):
    code = "MissingParameter"


class SsmlMarksNotSupportedForTextTypeException(PollyException):
    code = "SsmlMarksNotSupportedForTextTypeException"
    message = "TextType must be ssml"


class TextLengthExceededException(PollyException):
    code = "TextLengthExceededException"
    message = "Text too long"


class ValidationException(PollyException):
    code = "ValidationException"
