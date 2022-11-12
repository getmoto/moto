from moto.core.exceptions import JsonRESTError


class LambdaClientError(JsonRESTError):
    def __init__(self, error: str, message: str):
        super().__init__(error, message)


class CrossAccountNotAllowed(LambdaClientError):
    def __init__(self) -> None:
        super().__init__(
            "AccessDeniedException", "Cross-account pass role is not allowed."
        )


class InvalidParameterValueException(LambdaClientError):
    def __init__(self, message: str):
        super().__init__("InvalidParameterValueException", message)


class InvalidRoleFormat(LambdaClientError):
    pattern = r"arn:(aws[a-zA-Z-]*)?:iam::(\d{12}):role/?[a-zA-Z_0-9+=,.@\-_/]+"

    def __init__(self, role: str):
        message = f"1 validation error detected: Value '{role}' at 'role' failed to satisfy constraint: Member must satisfy regular expression pattern: {InvalidRoleFormat.pattern}"
        super().__init__("ValidationException", message)


class PreconditionFailedException(JsonRESTError):
    code = 412

    def __init__(self, message: str):
        super().__init__("PreconditionFailedException", message)


class UnknownAliasException(LambdaClientError):
    code = 404

    def __init__(self, arn: str):
        super().__init__("ResourceNotFoundException", f"Cannot find alias arn: {arn}")


class UnknownFunctionException(LambdaClientError):
    code = 404

    def __init__(self, arn: str):
        super().__init__("ResourceNotFoundException", f"Function not found: {arn}")


class FunctionUrlConfigNotFound(LambdaClientError):
    code = 404

    def __init__(self) -> None:
        super().__init__(
            "ResourceNotFoundException", "The resource you requested does not exist."
        )


class UnknownLayerException(LambdaClientError):
    code = 404

    def __init__(self) -> None:
        super().__init__("ResourceNotFoundException", "Cannot find layer")


class UnknownPolicyException(LambdaClientError):
    code = 404

    def __init__(self) -> None:
        super().__init__(
            "ResourceNotFoundException",
            "No policy is associated with the given resource.",
        )
