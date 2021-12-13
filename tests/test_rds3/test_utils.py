from __future__ import print_function
from moto.rds3 import utils


# def test_get_parameters():
#     class MockResponse(object):
#         def get_shaped_param(self, shape, key):
#             return '{}: {}'.format(key, shape)
#     params = utils.get_parameters('CreateDBInstance', MockResponse())
#     print params


def test_walk_parameters():
    params = ""  # utils.walk_parameters('CreateDBInstance')
    print(params)
