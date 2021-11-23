"""Exceptions raised by the route53resolver service."""
from moto.core.exceptions import JsonRESTError


class RRValidationException(JsonRESTError):
    """Report one of more parameter validation errors."""

    code = 400

    def __init__(self, error_tuples):
        """Validation errors are concatenated into one exception message.

        error_tuples is a list of tuples.  Each tuple contains:

          - name of invalid parameter,
          - value of invalid parameter,
          - string describing the constraints for that parameter.
        """
        msg_leader = (
            f"{len(error_tuples)} "
            f"validation error{'s' if len(error_tuples) > 1 else ''} detected: "
        )
        msgs = []
        for arg_name, arg_value, constraint in error_tuples:
            msgs.append(
                f"Value '{arg_value}' at '{arg_name}' failed to satisfy "
                f"constraint: Member must {constraint}"
            )
        super().__init__("ValidationException", msg_leader + "; ".join(msgs))


class InvalidNextTokenException(JsonRESTError):
    """Invalid next token parameter used to return a list of entities."""

    code = 400

    def __init__(self):
        super().__init__(
            "InvalidNextTokenException",
            "Invalid value passed for the NextToken parameter",
        )


class InvalidParameterException(JsonRESTError):
    """One or more parameters in request are not valid."""

    code = 400

    def __init__(self, message):
        super().__init__("InvalidParameterException", message)


class InvalidRequestException(JsonRESTError):
    """The request is invalid."""

    code = 400

    def __init__(self, message):
        super().__init__("InvalidRequestException", message)


class LimitExceededException(JsonRESTError):
    """The request caused one or more limits to be exceeded."""

    code = 400

    def __init__(self, message):
        super().__init__("LimitExceededException", message)


class ResourceExistsException(JsonRESTError):
    """The resource already exists."""

    code = 400

    def __init__(self, message):
        super().__init__("ResourceExistsException", message)


class ResourceInUseException(JsonRESTError):
    """The resource has other resources associated with it."""

    code = 400

    def __init__(self, message):
        super().__init__("ResourceInUseException", message)


class ResourceNotFoundException(JsonRESTError):
    """The specified resource doesn't exist."""

    code = 400

    def __init__(self, message):
        super().__init__("ResourceNotFoundException", message)


class TagValidationException(JsonRESTError):
    """Tag validation failed."""

    code = 400

    def __init__(self, message):
        super().__init__("ValidationException", message)
