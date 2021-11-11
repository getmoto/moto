"""Route53ResolverBackend validations that result in ValidationException.

Note that ValidationExceptions are accumulative.
"""
import re

from moto.route53resolver.exceptions import RRValidationException


def validate_args(validators):
    """Raise exception if any of the validations fails.

    validators is a list of tuples each containing the following:
        (validator_function, printable field name, field value)

    The error messages are accumulated before the exception is raised.
    """
    err_msgs = []
    for (func, fieldname, value) in validators:
        msg = func(value)
        if msg:
            err_msgs.append((fieldname, value, msg))
    if err_msgs:
        raise RRValidationException(err_msgs)


def validate_creator_request_id(value):
    """Raise exception if the creator_request id has invalid length."""
    if value and len(value) > 255:
        return "have length less than or equal to 255"
    return ""


def validate_direction(value):
    """Raise exception if direction not one of the allowed values."""
    if value and value not in ["INBOUND", "OUTBOUND"]:
        return "satisfy enum value set: [INBOUND, OUTBOUND]"
    return ""


def validate_ip_addresses(value):
    """Raise exception if IPs fail to match length constraint."""
    if len(value) > 10:
        return "have length less than or equal to 10"
    return ""


def validate_name(value):
    """Raise exception if name fails to match constraints."""
    if value:
        if len(value) > 64:
            return "have length less than or equal to 64"
        name_pattern = r"^(?!^[0-9]+$)([a-zA-Z0-9-_' ']+)$"
        if not re.match(name_pattern, value):
            return fr"satisfy regular expression pattern: {name_pattern}"
    return ""


def validate_security_group_ids(value):
    """Raise exception if IPs fail to match length constraint."""
    # Too many security group IDs is an InvalidParameterException.
    for group_id in value:
        if len(group_id) > 64:
            return (
                "have length less than or equal to 64 and Member must have "
                "length greater than or equal to 1"
            )
    return ""


def validate_subnets(value):
    """Raise exception if subnets fail to match length constraint."""
    for subnet_id in [x["SubnetId"] for x in value]:
        if len(subnet_id) > 32:
            return "have length less than or equal to 32"
    return ""
