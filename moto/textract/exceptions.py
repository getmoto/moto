"""Exceptions raised by the textract service."""
from moto.core.exceptions import JsonRESTError


class InvalidJobIdException(JsonRESTError):
    code = 400

    def __init__(self):
        super().__init__(__class__.__name__, "An invalid job identifier was passed.")


class InvalidS3ObjectException(JsonRESTError):
    code = 400

    def __init__(self):
        super().__init__(
            __class__.__name__,
            "Amazon Textract is unable to access the S3 object that's specified in the request.",
        )


class InvalidParameterException(JsonRESTError):
    code = 400

    def __init__(self):
        super().__init__(
            __class__.__name__,
            "An input parameter violated a constraint. For example, in synchronous operations, an InvalidParameterException exception occurs when neither of the S3Object or Bytes values are supplied in the Document request parameter. Validate your parameter before calling the API operation again.",
        )
