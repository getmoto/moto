from moto.core.exceptions import ServiceException


class StepFunctionsException(ServiceException):
    pass


class ExecutionAlreadyExists(StepFunctionsException):
    code = "ExecutionAlreadyExists"


class ExecutionDoesNotExist(StepFunctionsException):
    code = "ExecutionDoesNotExist"


class InvalidArn(StepFunctionsException):
    code = "InvalidArn"


class InvalidName(StepFunctionsException):
    code = "InvalidName"


class InvalidExecutionInput(StepFunctionsException):
    code = "InvalidExecutionInput"


class StateMachineDoesNotExist(StepFunctionsException):
    code = "StateMachineDoesNotExist"


class InvalidToken(StepFunctionsException):
    code = "InvalidToken"

    def __init__(self, message: str = "Invalid token"):
        super().__init__(f"Invalid Token: {message}")


class ResourceNotFound(StepFunctionsException):
    code = "ResourceNotFound"

    def __init__(self, arn: str):
        super().__init__(f"Resource not found: '{arn}'")


class ValidationException(StepFunctionsException):
    code = "ValidationException"

    def __init__(self, msg: str):
        super().__init__(msg)


class NameTooLongException(ValidationException):
    def __init__(self, name: str):
        super().__init__(
            f"1 validation error detected: Value '{name}' at 'name' "
            "failed to satisfy constraint: Member must have length less than or equal to 80"
        )


class InvalidEncryptionConfiguration(StepFunctionsException):
    code = "InvalidEncryptionConfiguration"


class ActivityDoesNotExist(StepFunctionsException):
    code = "ActivityDoesNotExist"


class ActivityAlreadyExists(StepFunctionsException):
    code = "ActivityAlreadyExists"
