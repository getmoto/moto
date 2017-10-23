import uuid


def make_arn_for_certificate(account_id, region_name):
    # Example
    # arn:aws:acm:eu-west-2:764371465172:certificate/c4b738b8-56fe-4b3a-b841-1c047654780b
    return "arn:aws:acm:{0}:{1}:certificate/{2}".format(region_name, account_id, uuid.uuid4())
