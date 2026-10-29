"""Exceptions raised by the textract service."""

from moto.core.exceptions import ServiceException


class TextractException(ServiceException):
    pass


class InvalidJobIdException(TextractException):
    code = "InvalidJobIdException"
    message = "An invalid job identifier was passed."


class InvalidS3ObjectException(TextractException):
    code = "InvalidS3ObjectException"
    message = "Amazon Textract is unable to access the S3 object that's specified in the request."


class InvalidParameterException(TextractException):
    code = "InvalidParameterException"
    message = "An input parameter violated a constraint. For example, in synchronous operations, an InvalidParameterException exception occurs when neither of the S3Object or Bytes values are supplied in the Document request parameter. Validate your parameter before calling the API operation again."
