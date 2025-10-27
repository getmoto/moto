from moto.core.exceptions import ServiceException


class VectorBucketNotFound(ServiceException):
    code = "NotFoundException"

    def __init__(self) -> None:
        super().__init__("The specified vector bucket could not be found")


class VectorBucketInvalidLength(ServiceException):
    code = "ValidationException"

    def __init__(self, length: int):
        super().__init__(
            f"1 validation error detected. Value with length {length} at '/vectorBucketName' failed to satisfy constraint: Member must have length between 3 and 63, inclusive"
        )


class VectorBucketInvalidChars(ServiceException):
    code = "ValidationException"

    def __init__(self) -> None:
        super().__init__("Invalid vector bucket name")


class VectorBucketAlreadyExists(ServiceException):
    code = "ConflictException"

    def __init__(self) -> None:
        super().__init__("A vector bucket with the specified name already exists")
