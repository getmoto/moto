from __future__ import unicode_literals


def make_arn_for_dashboard(account_id, name):
    return "arn:aws:cloudwatch::{0}dashboard/{1}".format(account_id, name)


def make_arn_for_alarm(region, account_id, alarm_name):
    return "arn:aws:cloudwatch:{0}:{1}:alarm:{2}".format(region, account_id, alarm_name)
