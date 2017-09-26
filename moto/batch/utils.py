from __future__ import unicode_literals


def make_arn_for_compute_env(account_id, name, region_name):
    return "arn:aws:batch:{0}:{1}:compute-environment/{2}".format(region_name, account_id, name)
