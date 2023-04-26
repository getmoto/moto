import re
from moto.moto_api._internal import mock_random

E164_REGEX = re.compile(r"^\+?[1-9]\d{1,14}$")


def make_arn_for_topic(account_id: str, name: str, region_name: str) -> str:
    return f"arn:aws:sns:{region_name}:{account_id}:{name}"


def make_arn_for_subscription(topic_arn: str) -> str:
    subscription_id = mock_random.uuid4()
    return f"{topic_arn}:{subscription_id}"


def is_e164(number: str) -> bool:
    return E164_REGEX.match(number) is not None
