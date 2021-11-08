"""DirectoryServiceBackend checks that result in ValidationException.

Note that ValidationExceptions are accumulative.
"""
import re

from moto.ds.exceptions import DsValidationException


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
        raise DsValidationException(err_msgs)


def validate_alias(value):
    """Raise exception if alias fails to conform to length and constraints."""
    if len(value) > 62:
        return "have length less than or equal to 62"

    alias_pattern = r"^(?!D-|d-)([\da-zA-Z]+)([-]*[\da-zA-Z])*$"
    if not re.match(alias_pattern, value):
        json_pattern = alias_pattern.replace("\\", r"\\")
        return fr"satisfy regular expression pattern: {json_pattern}"
    return ""


def validate_description(value):
    """Raise exception if description exceeds length."""
    if value and len(value) > 128:
        return "have length less than or equal to 128"
    return ""


def validate_directory_id(value):
    """Raise exception if the directory id is invalid."""
    id_pattern = r"^d-[0-9a-f]{10}$"
    if not re.match(id_pattern, value):
        return fr"satisfy regular expression pattern: {id_pattern}"
    return ""


def validate_dns_ips(value):
    """Raise exception if DNS IPs fail to match constraints."""
    dnsip_pattern = (
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )
    for dnsip in value:
        if not re.match(dnsip_pattern, dnsip):
            json_pattern = dnsip_pattern.replace("\\", r"\\")
            return fr"satisfy regular expression pattern: {json_pattern}"
    return ""


def validate_edition(value):
    """Raise exception if edition not one of the allowed values."""
    if value and value not in ["Enterprise", "Standard"]:
        return "satisfy enum value set: [Enterprise, Standard]"
    return ""


def validate_name(value):
    """Raise exception if name fails to match constraints."""
    name_pattern = r"^([a-zA-Z0-9]+[\\.-])+([a-zA-Z0-9])+$"
    if not re.match(name_pattern, value):
        return fr"satisfy regular expression pattern: {name_pattern}"
    return ""


def validate_password(value):
    """Raise exception if password fails to match constraints."""
    passwd_pattern = (
        r"^(?=^.{8,64}$)((?=.*\d)(?=.*[A-Z])(?=.*[a-z])|"
        r"(?=.*\d)(?=.*[^A-Za-z0-9\s])(?=.*[a-z])|"
        r"(?=.*[^A-Za-z0-9\s])(?=.*[A-Z])(?=.*[a-z])|"
        r"(?=.*\d)(?=.*[A-Z])(?=.*[^A-Za-z0-9\s]))^.*$"
    )
    if not re.match(passwd_pattern, value):
        # Can't have an odd number of backslashes in a literal.
        json_pattern = passwd_pattern.replace("\\", r"\\")
        return fr"satisfy regular expression pattern: {json_pattern}"
    return ""


def validate_short_name(value):
    """Raise exception if short name fails to match constraints."""
    short_name_pattern = r'^[^\/:*?"<>|.]+[^\/:*?"<>|]*$'
    if value and not re.match(short_name_pattern, value):
        json_pattern = short_name_pattern.replace("\\", r"\\").replace('"', r"\"")
        return fr"satisfy regular expression pattern: {json_pattern}"
    return ""


def validate_size(value):
    """Raise exception if size fails to match constraints."""
    if value.lower() not in ["small", "large"]:
        return "satisfy enum value set: [Small, Large]"
    return ""


def validate_sso_password(value):
    """Raise exception is SSO password exceeds length."""
    if value and len(value) > 128:
        return "have length less than or equal to 128"
    return ""


def validate_subnet_ids(value):
    """Raise exception is subnet IDs fail to match constraints."""
    subnet_id_pattern = r"^(subnet-[0-9a-f]{8}|subnet-[0-9a-f]{17})$"
    for subnet in value:
        if not re.match(subnet_id_pattern, subnet):
            return fr"satisfy regular expression pattern: {subnet_id_pattern}"
    return ""


def validate_user_name(value):
    """Raise exception is username fails to match constraints."""
    username_pattern = r"^[a-zA-Z0-9._-]+$"
    if value and not re.match(username_pattern, value):
        return fr"satisfy regular expression pattern: {username_pattern}"
    return ""
