import re

from boto3 import Session

from moto.eks.exceptions import InvalidParameterException


def set_partition(region):
    valid_matches = [
        # (region prefix, aws partition)
        ("cn-", "aws-cn"),
        ("us-gov-", "aws-us-gov"),
        ("us-gov-iso-", "aws-iso"),
        ("us-gov-iso-b-", "aws-iso-b"),
    ]

    for prefix, partition in valid_matches:
        if region.startswith(prefix):
            return partition
    return "aws"


def validate_role_arn(arn):
    valid_role_arn_format = re.compile(
        "arn:(?P<partition>.+):iam::(?P<account_id>[0-9]{12}):role/.+"
    )
    match = valid_role_arn_format.match(arn)
    valid_partition = match.group("partition") in Session().get_available_partitions()

    if not all({arn, match, valid_partition}):
        raise InvalidParameterException("Invalid Role Arn: '" + arn + "'")
