def make_arn_for_dashboard(account_id: str, name: str) -> str:
    return "arn:aws:cloudwatch::{0}dashboard/{1}".format(account_id, name)


def make_arn_for_alarm(region: str, account_id: str, alarm_name: str) -> str:
    return "arn:aws:cloudwatch:{0}:{1}:alarm:{2}".format(region, account_id, alarm_name)
