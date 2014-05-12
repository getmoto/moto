import uuid


def make_arn_for_topic(account_id, name):
    return "arn:aws:sns:us-east-1:{}:{}".format(account_id, name)


def make_arn_for_subscription(topic_arn):
    subscription_id = uuid.uuid4()
    return "{}:{}".format(topic_arn, subscription_id)
