import re
import uuid

E164_REGEX = re.compile(r"^\+?[1-9]\d{1,14}$")


def make_arn_for_topic(account_id, name, region_name):
    return "arn:aws:sns:{0}:{1}:{2}".format(region_name, account_id, name)


def make_arn_for_subscription(topic_arn):
    subscription_id = uuid.uuid4()
    return "{0}:{1}".format(topic_arn, subscription_id)


def is_e164(number):
    return E164_REGEX.match(number) is not None
