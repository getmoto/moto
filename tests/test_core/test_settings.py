import os
from unittest import mock
import pytest
import sure  # noqa # pylint: disable=unused-import

from moto import settings


"""
Sanity checks for interpretation of the MOTO_ECS_NEW_ARN-variable
"""


def test_default_is_true():
    settings.ecs_new_arn_format().should.equal(True)


@pytest.mark.parametrize("value", ["TrUe", "true", "invalid", "0", "1"])
def test_anything_but_false_is_true(value):
    with mock.patch.dict(os.environ, {"MOTO_ECS_NEW_ARN": value}):
        settings.ecs_new_arn_format().should.equal(True)


@pytest.mark.parametrize("value", ["False", "false", "faLse"])
def test_only_false_is_false(value):
    with mock.patch.dict(os.environ, {"MOTO_ECS_NEW_ARN": value}):
        settings.ecs_new_arn_format().should.equal(False)
