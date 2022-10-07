from moto.moto_api._internal import mock_random


def make_arn_for_certificate(account_id: str, region_name: str) -> str:
    # Example
    # arn:aws:acm:eu-west-2:764371465172:certificate/c4b738b8-56fe-4b3a-b841-1c047654780b
    return "arn:aws:acm:{0}:{1}:certificate/{2}".format(
        region_name, account_id, mock_random.uuid4()
    )
