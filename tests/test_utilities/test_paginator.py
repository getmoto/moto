from collections import OrderedDict
import unittest

import pytest

from moto.utilities.paginator import Paginator, paginate
from moto.core.exceptions import InvalidToken


results = [
    {"id": f"id{i}", "name": f"name{i}", "arn": f"arn:aws:thing/name{i}"}
    for i in range(0, 10)
]


class Model:
    def __init__(self, i):
        self.id = f"id{i}"
        self.name = f"name{i}"
        self.arn = f"arn:aws:thing/{self.name}"


model_results = [Model(i) for i in range(0, 100)]


def test_paginator_without_max_results__throws_error():
    p = Paginator()
    with pytest.raises(TypeError):
        p.paginate(results)


def test_paginator__paginate_with_just_max_results():
    p = Paginator(max_results=50)
    resp = p.paginate(results)
    assert len(resp) == 2

    page, next_token = resp
    assert next_token is None
    assert page == results


def test_paginator__ordered_dict():
    p = Paginator(max_results=1, unique_attribute="id")
    page, _ = p.paginate([OrderedDict(x) for x in results])
    assert len(page) == 1


def test_paginator__paginate_without_range_key__throws_error():
    p = Paginator(max_results=2)
    with pytest.raises(KeyError):
        p.paginate(results)


def test_paginator__paginate_with_unknown_range_key__throws_error():
    p = Paginator(max_results=2, unique_attribute=["unknown"])
    with pytest.raises(KeyError):
        p.paginate(results)


def test_paginator__paginate_5():
    p = Paginator(max_results=5, unique_attribute=["name"])
    resp = p.paginate(results)
    assert len(resp) == 2

    page, next_token = resp
    assert next_token is not None
    assert page == results[0:5]


def test_paginator__paginate_5__use_different_range_keys():
    p = Paginator(max_results=5, unique_attribute="name")
    _, token_as_str = p.paginate(results)

    p = Paginator(max_results=5, unique_attribute=["name"])
    _, token_as_lst = p.paginate(results)

    assert token_as_lst is not None
    assert token_as_lst == token_as_str

    p = Paginator(max_results=5, unique_attribute=["name", "arn"])
    _, token_multiple = p.paginate(results)
    assert token_multiple is not None
    assert token_multiple != token_as_str


def test_paginator__paginate_twice():
    p = Paginator(max_results=5, unique_attribute=["name"])
    resp = p.paginate(results)
    assert len(resp) == 2

    page, next_token = resp

    p = Paginator(max_results=10, unique_attribute=["name"], starting_token=next_token)
    resp = p.paginate(results)

    page, next_token = resp
    assert next_token is None
    assert page == results[5:]


def test_paginator__invalid_token():
    with pytest.raises(InvalidToken):
        Paginator(max_results=5, unique_attribute=["name"], starting_token="unknown")


def test_paginator__invalid_token__but_we_just_dont_care():
    p = Paginator(
        max_results=5,
        unique_attribute=["name"],
        starting_token="unknown",
        fail_on_invalid_token=False,
    )
    res, token = p.paginate(results)

    assert res == []
    assert token is None


class CustomInvalidTokenException(BaseException):
    def __init__(self, token):
        self.message = f"Invalid token: {token}"


class GenericInvalidTokenException(BaseException):
    def __init__(self):
        self.message = "Invalid token!"


class TestDecorator(unittest.TestCase):
    PAGINATION_MODEL = {
        "method_returning_dict": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "name",
        },
        "method_returning_instances": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 10,
            "limit_max": 50,
            "unique_attribute": "name",
        },
        "method_returning_args": {
            "limit_key": "max_results",
            "unique_attribute": "name",
        },
        "method_specifying_invalidtoken_exception": {
            "limit_key": "max_results",
            "limit_default": 5,
            "unique_attribute": "name",
            "fail_on_invalid_token": CustomInvalidTokenException,
        },
        "method_specifying_generic_invalidtoken_exception": {
            "limit_key": "max_results",
            "limit_default": 5,
            "unique_attribute": "name",
            "fail_on_invalid_token": GenericInvalidTokenException,
        },
        "method_expecting_token_as_kwarg": {
            "input_token": "custom_token",
            "limit_default": 1,
            "unique_attribute": "name",
        },
        "method_expecting_limit_as_kwarg": {
            "limit_key": "custom_limit",
            "limit_default": 1,
            "unique_attribute": "name",
        },
        "method_with_list_as_kwarg": {"limit_default": 1, "unique_attribute": "name"},
    }

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore[misc]
    def method_returning_dict(self):
        return results

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore[misc]
    def method_returning_instances(self):
        return model_results

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore[misc]
    def method_without_configuration(self):
        return results

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore[misc]
    def method_returning_args(self, *args, **kwargs):
        return [*args] + list(kwargs.items())

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore[misc]
    def method_expecting_token_as_kwarg(self, custom_token=None):
        self.custom_token = custom_token
        return [{"name": "item1"}, {"name": "item2"}]

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore[misc]
    def method_expecting_limit_as_kwarg(self, custom_limit):
        self.custom_limit = custom_limit
        return [{"name": "item1"}, {"name": "item2"}]

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore[misc]
    def method_with_list_as_kwarg(self, resources=None):
        if not resources:
            resources = []
        return resources or results

    @paginate(PAGINATION_MODEL)  # type: ignore[misc]
    def method_specifying_invalidtoken_exception(self):
        return results

    @paginate(PAGINATION_MODEL)  # type: ignore[misc]
    def method_specifying_generic_invalidtoken_exception(self):
        return results

    def test__method_returning_dict(self):
        page, token = self.method_returning_dict()
        assert page == results
        assert token is None

    def test__method_returning_instances(self):
        page, token = self.method_returning_instances()
        assert page == model_results[0:10]
        assert token is not None

    def test__method_without_configuration(self):
        with pytest.raises(ValueError):
            self.method_without_configuration()

    def test__input_arguments_are_returned(self):
        resp, _ = self.method_returning_args(1, "2", next_token=None, max_results=5)
        assert len(resp) == 4
        assert 1 in resp
        assert "2" in resp
        assert ("next_token", None) in resp
        assert ("max_results", 5) in resp

    def test__pass_exception_on_invalid_token(self):
        # works fine if no token is specified
        self.method_specifying_invalidtoken_exception()

        # throws exception if next_token is invalid
        with pytest.raises(CustomInvalidTokenException) as exc:
            self.method_specifying_invalidtoken_exception(
                next_token="some invalid token"
            )
        assert isinstance(exc.value, CustomInvalidTokenException)
        assert exc.value.message == "Invalid token: some invalid token"

    def test__pass_generic_exception_on_invalid_token(self):
        # works fine if no token is specified
        self.method_specifying_generic_invalidtoken_exception()

        # throws exception if next_token is invalid
        # Exception does not take any arguments - our paginator needs to
        # verify whether the next_token arg is expected
        with pytest.raises(GenericInvalidTokenException) as exc:
            self.method_specifying_generic_invalidtoken_exception(
                next_token="some invalid token"
            )
        assert isinstance(exc.value, GenericInvalidTokenException)
        assert exc.value.message == "Invalid token!"

    def test__invoke_function_that_expects_token_as_keyword(self):
        resp, first_token = self.method_expecting_token_as_kwarg()
        assert resp == [{"name": "item1"}]
        assert first_token is not None
        assert self.custom_token is None

        # Verify the custom_token is received in the business method
        # Could be handy for additional validation
        resp, _ = self.method_expecting_token_as_kwarg(custom_token=first_token)
        assert self.custom_token == first_token

    def test__invoke_function_that_expects_limit_as_keyword(self):
        self.method_expecting_limit_as_kwarg(custom_limit=None)
        assert self.custom_limit is None

        # Verify the custom_limit is received in the business method
        # Could be handy for additional validation
        self.method_expecting_limit_as_kwarg(custom_limit=1)
        assert self.custom_limit == 1

    def test__verify_kwargs_can_be_a_list(self):
        # Use case - verify that the kwarg can be of type list
        # Paginator creates a hash for all kwargs
        # We need to be make sure that the hash-function can deal with lists
        resp, token = self.method_with_list_as_kwarg()
        assert resp == results[0:1]

        resp, token = self.method_with_list_as_kwarg(next_token=token)
        assert resp == results[1:2]

        custom_list = [{"name": "a"}, {"name": "b"}]
        resp, token = self.method_with_list_as_kwarg(resources=custom_list)
        assert resp == custom_list[0:1]

        resp, token = self.method_with_list_as_kwarg(
            resources=custom_list, next_token=token
        )
        assert resp == custom_list[1:]
        assert token is None

    def test__paginator_fails_with_inconsistent_arguments(self):
        custom_list = [{"name": "a"}, {"name": "b"}]
        resp, token = self.method_with_list_as_kwarg(resources=custom_list)
        assert resp == custom_list[0:1]

        with pytest.raises(InvalidToken):
            # This should fail, as our 'resources' argument is inconsistent
            # with the original resources that were provided
            self.method_with_list_as_kwarg(resources=results, next_token=token)
