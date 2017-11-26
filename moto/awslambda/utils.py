from collections import namedtuple

ARN = namedtuple('ARN', ['region', 'account', 'function_name', 'version'])


def make_function_arn(region, account, name, version='1'):
    return 'arn:aws:lambda:{0}:{1}:function:{2}:{3}'.format(region, account, name, version)


def split_function_arn(arn):
    arn = arn.replace('arn:aws:lambda:')

    region, account, _, name, version = arn.split(':')

    return ARN(region, account, name, version)
