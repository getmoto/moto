import unittest

import pytest
import sure  # noqa # pylint: disable=unused-import
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
    resp.should.have.length_of(2)

    page, next_token = resp
    next_token.should.equal(None)
    page.should.equal(results)


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
    resp.should.have.length_of(2)

    page, next_token = resp
    next_token.shouldnt.equal(None)
    page.should.equal(results[0:5])


def test_paginator__paginate_5__use_different_range_keys():
    p = Paginator(max_results=5, unique_attribute="name")
    _, token_as_str = p.paginate(results)

    p = Paginator(max_results=5, unique_attribute=["name"])
    _, token_as_lst = p.paginate(results)

    token_as_lst.shouldnt.be(None)
    token_as_lst.should.equal(token_as_str)

    p = Paginator(max_results=5, unique_attribute=["name", "arn"])
    _, token_multiple = p.paginate(results)
    token_multiple.shouldnt.be(None)
    token_multiple.shouldnt.equal(token_as_str)


def test_paginator__paginate_twice():
    p = Paginator(max_results=5, unique_attribute=["name"])
    resp = p.paginate(results)
    resp.should.have.length_of(2)

    page, next_token = resp

    p = Paginator(max_results=10, unique_attribute=["name"], starting_token=next_token)
    resp = p.paginate(results)

    page, next_token = resp
    next_token.should.equal(None)
    page.should.equal(results[5:])


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

    res.should.equal([])
    token.should.equal(None)


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
        "method_with_list_as_kwarg": {"limit_default": 1, "unique_attribute": "name",},
    }

    @paginate(pagination_model=PAGINATION_MODEL)
    def method_returning_dict(self):
        return results

    @paginate(pagination_model=PAGINATION_MODEL)
    def method_returning_instances(self):
        return model_results

    @paginate(pagination_model=PAGINATION_MODEL)
    def method_without_configuration(self):
        return results

    @paginate(pagination_model=PAGINATION_MODEL)
    def method_returning_args(self, *args, **kwargs):
        return [*args] + [(k, v) for k, v in kwargs.items()]

    @paginate(pagination_model=PAGINATION_MODEL)
    def method_expecting_token_as_kwarg(self, custom_token=None):
        self.custom_token = custom_token
        return [{"name": "item1"}, {"name": "item2"}]

    @paginate(pagination_model=PAGINATION_MODEL)
    def method_expecting_limit_as_kwarg(self, custom_limit):
        self.custom_limit = custom_limit
        return [{"name": "item1"}, {"name": "item2"}]

    @paginate(pagination_model=PAGINATION_MODEL)
    def method_with_list_as_kwarg(self, resources=[]):
        return resources or results

    @paginate(PAGINATION_MODEL)
    def method_specifying_invalidtoken_exception(self):
        return results

    @paginate(PAGINATION_MODEL)
    def method_specifying_generic_invalidtoken_exception(self):
        return results

    def test__method_returning_dict(self):
        page, token = self.method_returning_dict()
        page.should.equal(results)
        token.should.equal(None)

    def test__method_returning_instances(self):
        page, token = self.method_returning_instances()
        page.should.equal(model_results[0:10])
        token.shouldnt.equal(None)

    def test__method_without_configuration(self):
        with pytest.raises(ValueError):
            self.method_without_configuration()

    def test__input_arguments_are_returned(self):
        resp, token = self.method_returning_args(1, "2", next_token=None, max_results=5)
        resp.should.have.length_of(4)
        resp.should.contain(1)
        resp.should.contain("2")
        resp.should.contain(("next_token", None))
        resp.should.contain(("max_results", 5))
        token.should.equal(None)

    def test__pass_exception_on_invalid_token(self):
        # works fine if no token is specified
        self.method_specifying_invalidtoken_exception()

        # throws exception if next_token is invalid
        with pytest.raises(CustomInvalidTokenException) as exc:
            self.method_specifying_invalidtoken_exception(
                next_token="some invalid token"
            )
        exc.value.should.be.a(CustomInvalidTokenException)
        exc.value.message.should.equal("Invalid token: some invalid token")

    def test__pass_generic_exception_on_invalid_token(self):
        # works fine if no token is specified
        self.method_specifying_generic_invalidtoken_exception()

        # throws exception if next_token is invalid
        # Exception does not take any arguments - our paginator needs to verify whether the next_token arg is expected
        with pytest.raises(GenericInvalidTokenException) as exc:
            self.method_specifying_generic_invalidtoken_exception(
                next_token="some invalid token"
            )
        exc.value.should.be.a(GenericInvalidTokenException)
        exc.value.message.should.equal("Invalid token!")

    def test__invoke_function_that_expects_token_as_keyword(self):
        resp, first_token = self.method_expecting_token_as_kwarg()
        resp.should.equal([{"name": "item1"}])
        first_token.shouldnt.equal(None)
        self.custom_token.should.equal(None)

        # Verify the custom_token is received in the business method
        # Could be handy for additional validation
        resp, token = self.method_expecting_token_as_kwarg(custom_token=first_token)
        self.custom_token.should.equal(first_token)

    def test__invoke_function_that_expects_limit_as_keyword(self):
        self.method_expecting_limit_as_kwarg(custom_limit=None)
        self.custom_limit.should.equal(None)

        # Verify the custom_limit is received in the business method
        # Could be handy for additional validation
        self.method_expecting_limit_as_kwarg(custom_limit=1)
        self.custom_limit.should.equal(1)

    def test__verify_kwargs_can_be_a_list(self):
        # Use case - verify that the kwarg can be of type list
        # Paginator creates a hash for all kwargs
        # We need to be make sure that the hash-function can deal with lists
        resp, token = self.method_with_list_as_kwarg()
        resp.should.equal(results[0:1])

        resp, token = self.method_with_list_as_kwarg(next_token=token)
        resp.should.equal(results[1:2])

        custom_list = [{"name": "a"}, {"name": "b"}]
        resp, token = self.method_with_list_as_kwarg(resources=custom_list)
        resp.should.equal(custom_list[0:1])

        resp, token = self.method_with_list_as_kwarg(
            resources=custom_list, next_token=token
        )
        resp.should.equal(custom_list[1:])
        token.should.equal(None)

    def test__paginator_fails_with_inconsistent_arguments(self):
        custom_list = [{"name": "a"}, {"name": "b"}]
        resp, token = self.method_with_list_as_kwarg(resources=custom_list)
        resp.should.equal(custom_list[0:1])

        with pytest.raises(InvalidToken):
            # This should fail, as our 'resources' argument is inconsistent with the original resources that were provided
            self.method_with_list_as_kwarg(resources=results, next_token=token)
