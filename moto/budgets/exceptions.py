"""Exceptions raised by the budgets service."""
from moto.core.exceptions import JsonRESTError


class DuplicateRecordException(JsonRESTError):
    code = 400

    def __init__(self, record_type, record_name):
        super().__init__(
            __class__.__name__,
            f"Error creating {record_type}: {record_name} - the {record_type} already exists.",
        )


class NotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__(__class__.__name__, message)


class BudgetMissingLimit(JsonRESTError):
    code = 400

    def __init__(self):
        super().__init__(
            "InvalidParameterException",
            "Unable to create/update budget - please provide one of the followings: Budget Limit/ Planned Budget Limit/ Auto Adjust Data",
        )
