from __future__ import unicode_literals


def make_arn_for_lexicon(account_id, name, region_name):
    return "arn:aws:polly:{0}:{1}:lexicon/{2}".format(region_name, account_id, name)
