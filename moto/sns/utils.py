from __future__ import unicode_literals
import uuid


def make_arn_for_topic(account_id, name, region_name):
    return "arn:aws:sns:{0}:{1}:{2}".format(region_name, account_id, name)


def make_arn_for_subscription(topic_arn):
    subscription_id = uuid.uuid4()
    return "{0}:{1}".format(topic_arn, subscription_id)
