from uuid import uuid4


def get_random_identity_id(region):
    return "{0}:{1}".format(region, uuid4())
