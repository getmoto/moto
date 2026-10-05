import pytest

import moto.stepfunctions.parser.stepfunctions_utils as utils


def test_get_next_page_token_from_arn():
    assert utils.get_next_page_token_from_arn("") == ""


def test_normalise_max_results():
    assert utils.normalise_max_results(None) == 100
    assert utils.normalise_max_results(0) == 100
    assert utils.normalise_max_results(1) == 1
    assert utils.normalise_max_results(123) == 123


def test_assert_pagination_parameters_valid():
    utils.assert_pagination_parameters_valid(None, None)
    with pytest.raises(Exception) as exc:
        utils.assert_pagination_parameters_valid(9999, "A")
    assert "Member must have value less than or equal" in str(exc.value)
    with pytest.raises(Exception) as exc:
        utils.assert_pagination_parameters_valid(1, "A" * 10000)
    assert "Member must have length less than or equal" in str(exc.value)
