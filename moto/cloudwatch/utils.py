def make_arn_for_dashboard(account_id: str, name: str) -> str:
    return f"arn:aws:cloudwatch::{account_id}dashboard/{name}"


def make_arn_for_alarm(region: str, account_id: str, alarm_name: str) -> str:
    return f"arn:aws:cloudwatch:{region}:{account_id}:alarm:{alarm_name}"
