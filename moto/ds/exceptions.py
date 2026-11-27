"""Exceptions raised by the Directory Service service."""

from moto.core.exceptions import ServiceException


class DirectoryServiceException(ServiceException):
    pass


class DsValidationException(DirectoryServiceException):
    """Report one of more parameter validation errors."""

    code = "ValidationException"

    def __init__(self, error_tuples: list[tuple[str, str, str]]):
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
            value = "at" if "assword" in arg_name else f"'{arg_value}' at"
            msgs.append(
                f"Value {value} '{arg_name}' failed to satisfy constraint: "
                f"Member must {constraint}"
            )
        super().__init__(msg_leader + "; ".join(msgs))


class ClientException(DirectoryServiceException):
    """Client exception has occurred. VPC parameters are invalid."""

    code = "ClientException"


class DirectoryLimitExceededException(DirectoryServiceException):
    """Maximum number of directories in region has been reached."""

    code = "DirectoryLimitExceededException"


class EntityDoesNotExistException(DirectoryServiceException):
    """The specified entity could not be found."""

    code = "EntityDoesNotExistException"


class EntityAlreadyExistsException(DirectoryServiceException):
    """The specified entity already exists."""

    code = "EntityAlreadyExistsException"


class InvalidNextTokenException(DirectoryServiceException):
    """Invalid next token parameter used to return a list of entities."""

    code = "InvalidNextTokenException"

    def __init__(self) -> None:
        super().__init__("Invalid value passed for the NextToken parameter")


class InvalidParameterException(DirectoryServiceException):
    """Invalid parameter."""

    code = "InvalidParameterException"


class TagLimitExceededException(DirectoryServiceException):
    """The maximum allowed number of tags was exceeded."""

    code = "TagLimitExceededException"


class ValidationException(DirectoryServiceException):
    """Tag validation failed."""

    code = "ValidationException"


class UnsupportedOperationException(DirectoryServiceException):
    """Unsupported Operation"""

    code = "UnsupportedOperationException"
