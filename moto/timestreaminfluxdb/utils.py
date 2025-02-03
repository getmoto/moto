import random
import re
import string

from .exceptions import ValidationException


def random_id(size: int = 10) -> str:
    chars = list(range(10)) + list(string.ascii_lowercase)
    return "".join(str(random.choice(chars)) for x in range(size))


def validate_storage(storage: int) -> None:
    if storage < 20 or storage > 16384:
        raise ValidationException(
            f"Expected allocated storage to be between 20 and 16384, got {storage}"
        )


def validate_port(port: int) -> None:
    if port < 1024 or port > 65535:
        raise ValidationException(
            f"Expected port to be between 1024 and 65535, got {port}"
        )


def validate_name(name: str) -> None:
    """
    The name that uniquely identifies the DB instance when interacting with the Amazon Timestream for InfluxDB API and CLI commands.
    This name will also be a prefix included in the endpoint.
    DB instance names must be unique per customer and per region.
    Length Constraints: Minimum length of 3. Maximum length of 40.
    Pattern: ^[a-zA-Z][a-zA-Z0-9]*(-[a-zA-Z0-9]+)*$

    """

    if len(name) < 3:
        raise ValidationException(
            f"Expected name to have a minimum length of 3, got {len(name)}"
        )
    elif len(name) > 40:
        raise ValidationException(
            f"Expected name to have a maximum length of 40, got {len(name)}"
        )
    elif not re.match(r"^[a-zA-Z][a-zA-Z0-9]*(-[a-zA-Z0-9]+)*$", name):
        raise ValidationException(
            f"Expected name to match the pattern ^[a-zA-Z][a-zA-Z0-9]*(-[a-zA-Z0-9]+)*$, got {name}"
        )
