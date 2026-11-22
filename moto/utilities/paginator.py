import inspect
from collections.abc import Callable
from copy import deepcopy
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

from botocore.paginate import TokenDecoder, TokenEncoder

from moto.core.exceptions import InvalidToken

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, Protocol

    P1 = ParamSpec("P1")
    P2 = ParamSpec("P2")
else:
    Protocol = object

T = TypeVar("T")


class GenericFunction(Protocol):
    def __call__(
        self, func: "Callable[P1, list[T]]"
    ) -> "Callable[P2, tuple[list[T], str | None]]": ...


def paginate(pagination_model: dict[str, Any]) -> GenericFunction:
    def pagination_decorator(
        func: Callable[..., list[T]],
    ) -> Callable[..., tuple[list[T], str | None]]:
        @wraps(func)
        def pagination_wrapper(*args: Any, **kwargs: Any) -> Any:  # type: ignore
            method = func.__name__
            model = pagination_model
            pagination_config = model.get(method)
            if not pagination_config:
                raise ValueError(f"No pagination config for backend method: {method}")
            # Get the pagination arguments, to be used by the paginator
            next_token_name = pagination_config.get("input_token", "next_token")
            limit_name = pagination_config.get("limit_key")
            input_token = kwargs.get(next_token_name)
            limit = kwargs.get(limit_name, None)
            # Remove pagination arguments from our input kwargs
            # We need this to verify that our input kwargs are the same across invocations
            #   list_all(service="x")                   next_token = "a"
            #   list_all(service="x", next_token="a") ==> Works fine
            #   list_all(service="y", next_token="a") ==> Should throw an error, as the input_kwargs are different
            input_kwargs = deepcopy(kwargs)
            input_kwargs.pop(next_token_name, None)
            input_kwargs.pop(limit_name, None)
            fail_on_invalid_token = pagination_config.get("fail_on_invalid_token", True)
            paginator = Paginator(
                max_results=limit,
                max_results_default=pagination_config.get("limit_default"),
                starting_token=input_token,
                unique_attribute=pagination_config.get("unique_attribute"),
                param_values_to_check=input_kwargs,
                fail_on_invalid_token=fail_on_invalid_token,
                token_strategy=pagination_config.get("token_strategy", "opaque"),
                token_position=pagination_config.get("token_position", "after_last"),
            )

            # Determine which parameters to pass
            (arg_names, _, has_kwargs, _, _, _, _) = inspect.getfullargspec(func)
            # If the target-func expects `**kwargs`, we can pass everything
            if not has_kwargs:
                # If the target-function does not expect the next_token/limit, do not pass it
                if next_token_name not in arg_names:
                    kwargs.pop(next_token_name, None)
                if limit_name not in arg_names:
                    kwargs.pop(limit_name, None)

            results = func(*args, **kwargs)
            return paginator.paginate(results)

        return pagination_wrapper

    return pagination_decorator


class Paginator:
    """Return one page of a list of results.

    Two token strategies are supported:

    - ``opaque`` (default): tokens are encoded by the paginator and identify
      the first item of the next page.  They include a checksum of the other
      request parameters, so a token can't be reused with different filters.
    - ``marker``: tokens are the raw value of the item's unique attribute,
      e.g. Kinesis ``ExclusiveStartShardId``.  The marker must match an item.
      ``token_position`` says whether it is the last item returned
      (``after_last``, an exclusive start) or the first item of the next page
      (``at_next``, an inclusive start).
    """

    TOKEN_STRATEGIES = ("opaque", "marker")
    TOKEN_POSITIONS = ("after_last", "at_next")

    def __init__(
        self,
        max_results: Any = None,
        max_results_default: Any = None,
        starting_token: Any = None,
        unique_attribute: Any = None,
        param_values_to_check: Any = None,
        fail_on_invalid_token: bool = True,
        token_strategy: str = "opaque",
        token_position: str = "after_last",
    ):
        if token_strategy not in self.TOKEN_STRATEGIES:
            raise ValueError(f"Unknown token_strategy: {token_strategy}")
        if token_position not in self.TOKEN_POSITIONS:
            raise ValueError(f"Unknown token_position: {token_position}")
        self._max_results = max_results if max_results else max_results_default
        self._starting_token = starting_token
        self._unique_attributes = (
            unique_attribute
            if isinstance(unique_attribute, list)
            else [unique_attribute]
        )
        if token_strategy == "marker" and len(self._unique_attributes) != 1:
            raise ValueError("Marker tokens require exactly one unique_attribute")
        self._param_values_to_check = param_values_to_check
        self._fail_on_invalid_token = fail_on_invalid_token
        self._token_strategy = token_strategy
        self._token_position = token_position
        self._token_encoder = TokenEncoder()
        self._token_decoder = TokenDecoder()
        self._param_checksum = self._calculate_parameter_checksum()
        self._parsed_token = (
            self._parse_starting_token() if token_strategy == "opaque" else None
        )

    def _parse_starting_token(self) -> dict[str, Any] | None:
        if self._starting_token is None:
            return None
        # The starting token is a dict passed as a base64 encoded string.
        next_token = self._starting_token
        try:
            next_token = self._token_decoder.decode(next_token)
        except (ValueError, TypeError, UnicodeDecodeError):
            self._raise_exception_if_required(next_token)
            return None
        if next_token.get("parameterChecksum") != self._param_checksum:
            raise InvalidToken(f"Input inconsistent with page token: {str(next_token)}")
        return next_token

    def _raise_exception_if_required(self, token: str | None) -> None:
        if self._fail_on_invalid_token:
            if isinstance(self._fail_on_invalid_token, type):
                # we need to raise a custom exception
                func_info = inspect.getfullargspec(self._fail_on_invalid_token)
                arg_names, _, _, _, _, _, _ = func_info
                # arg_names == [self] or [self, token_argument_that_can_have_any_name]
                requires_token_arg = len(arg_names) > 1
                if requires_token_arg:
                    raise self._fail_on_invalid_token(token)
                else:
                    raise self._fail_on_invalid_token()
            raise InvalidToken("Invalid token")

    def _calculate_parameter_checksum(self) -> int:
        def freeze(o: Any) -> Any:
            if not o:
                return None
            if isinstance(o, dict):
                return frozenset({k: freeze(v) for k, v in o.items()}.items())

            if isinstance(o, (list, tuple, set)):
                return tuple([freeze(v) for v in o])

            return o

        return hash(freeze(self._param_values_to_check))

    def _check_predicate(self, item: Any) -> bool:
        if self._parsed_token is None:
            return False
        predicate_values = self._parsed_token["uniqueAttributes"]
        if not isinstance(predicate_values, list) or len(predicate_values) != len(
            self._unique_attributes
        ):
            return False
        for attr, predicate_value in zip(
            self._unique_attributes, predicate_values, strict=True
        ):
            curr_val = self._get_unique_value(item, attr, None)
            if not str(curr_val) == predicate_value:
                return False

        return True

    @staticmethod
    def _get_unique_value(item: Any, attr: Any, default: Any = None) -> Any:
        # Scalar items (e.g. a list of ARNs or URLs) are their own unique value
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            return item[attr]
        return getattr(item, attr, default)

    def _build_next_token(self, next_item: Any) -> str:
        token_dict: dict[str, Any] = {}
        if self._param_checksum:
            token_dict["parameterChecksum"] = self._param_checksum
        range_keys = []
        for attr in self._unique_attributes:
            range_keys.append(str(self._get_unique_value(next_item, attr)))
        # Encode as a list (not a delimited string) so attribute values containing
        # any character, including the old "|" delimiter, successfully round-trip.
        token_dict["uniqueAttributes"] = range_keys
        return self._token_encoder.encode(token_dict)

    def paginate(self, results: list[Any]) -> tuple[list[Any], str | None]:
        if self._token_strategy == "marker":
            return self._paginate_with_marker(results)
        index_start = 0
        if self._starting_token:
            try:
                index_start = next(
                    index
                    for (index, result) in enumerate(results)
                    if self._check_predicate(result)
                )
            except StopIteration:
                if self._fail_on_invalid_token:
                    raise InvalidToken("Resource not found!")
                else:
                    return [], None

        index_end = index_start + self._max_results
        if index_end > len(results):
            index_end = len(results)

        results_page = results[index_start:index_end]

        next_token = None
        if results_page and index_end < len(results):
            last_resource_on_this_page = results[index_end]
            next_token = self._build_next_token(last_resource_on_this_page)
        return results_page, next_token

    def _paginate_with_marker(self, results: list[Any]) -> tuple[list[Any], str | None]:
        attr = self._unique_attributes[0]
        index_start = 0
        if self._starting_token:
            marker = str(self._starting_token)
            try:
                marker_index = next(
                    index
                    for (index, result) in enumerate(results)
                    if str(self._get_unique_value(result, attr)) == marker
                )
            except StopIteration:
                if self._fail_on_invalid_token:
                    raise InvalidToken("Resource not found!")
                return [], None
            index_start = marker_index
            if self._token_position == "after_last":
                index_start += 1

        index_end = min(index_start + self._max_results, len(results))
        results_page = results[index_start:index_end]

        next_token = None
        if results_page and index_end < len(results):
            if self._token_position == "after_last":
                marker_item = results_page[-1]
            else:
                marker_item = results[index_end]
            next_token = str(self._get_unique_value(marker_item, attr))
        return results_page, next_token
