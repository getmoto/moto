from functools import wraps

from botocore.paginate import TokenDecoder, TokenEncoder
from six.moves import reduce

from moto.core.exceptions import InvalidToken


def paginate(pagination_model, original_function=None):
    def pagination_decorator(func):
        @wraps(func)
        def pagination_wrapper(*args, **kwargs):

            method = func.__name__
            model = pagination_model
            pagination_config = model.get(method)
            if not pagination_config:
                raise ValueError(
                    "No pagination config for backend method: {}".format(method)
                )
            # We pop the pagination arguments, so the remaining kwargs (if any)
            # can be used to compute the optional parameters checksum.
            input_token = kwargs.pop(pagination_config.get("input_token"), None)
            limit = kwargs.pop(pagination_config.get("limit_key"), None)
            fail_on_invalid_token = pagination_config.get("fail_on_invalid_token", True)
            paginator = Paginator(
                max_results=limit,
                max_results_default=pagination_config.get("limit_default"),
                starting_token=input_token,
                page_ending_range_keys=pagination_config.get("page_ending_range_keys"),
                param_values_to_check=kwargs,
                fail_on_invalid_token=fail_on_invalid_token,
            )
            results = func(*args, **kwargs)
            return paginator.paginate(results)

        return pagination_wrapper

    if original_function:
        return pagination_decorator(original_function)

    return pagination_decorator


class Paginator(object):
    def __init__(
        self,
        max_results=None,
        max_results_default=None,
        starting_token=None,
        page_ending_range_keys=None,
        param_values_to_check=None,
        fail_on_invalid_token=True,
    ):
        self._max_results = max_results if max_results else max_results_default
        self._starting_token = starting_token
        self._page_ending_range_keys = page_ending_range_keys
        self._param_values_to_check = param_values_to_check
        self._fail_on_invalid_token = fail_on_invalid_token
        self._token_encoder = TokenEncoder()
        self._token_decoder = TokenDecoder()
        self._param_checksum = self._calculate_parameter_checksum()
        self._parsed_token = self._parse_starting_token()

    def _parse_starting_token(self):
        if self._starting_token is None:
            return None
        # The starting token is a dict passed as a base64 encoded string.
        next_token = self._starting_token
        try:
            next_token = self._token_decoder.decode(next_token)
        except (ValueError, TypeError, UnicodeDecodeError):
            if self._fail_on_invalid_token:
                raise InvalidToken("Invalid token")
            return None
        if next_token.get("parameterChecksum") != self._param_checksum:
            raise InvalidToken(
                "Input inconsistent with page token: {}".format(str(next_token))
            )
        return next_token

    def _calculate_parameter_checksum(self):
        if not self._param_values_to_check:
            return None
        return reduce(
            lambda x, y: x ^ y,
            [hash(item) for item in self._param_values_to_check.items()],
        )

    def _check_predicate(self, item):
        if self._parsed_token is None:
            return False
        page_ending_range_key = self._parsed_token["pageEndingRangeKey"]
        predicate_values = page_ending_range_key.split("|")
        for (index, attr) in enumerate(self._page_ending_range_keys):
            curr_val = item[attr] if type(item) == dict else getattr(item, attr, None)
            if not curr_val == predicate_values[index]:
                return False
        return True

    def _build_next_token(self, next_item):
        token_dict = {}
        if self._param_checksum:
            token_dict["parameterChecksum"] = self._param_checksum
        range_keys = []
        for (index, attr) in enumerate(self._page_ending_range_keys):
            if type(next_item) == dict:
                range_keys.append(next_item[attr])
            else:
                range_keys.append(getattr(next_item, attr))
        token_dict["pageEndingRangeKey"] = "|".join(range_keys)
        return self._token_encoder.encode(token_dict)

    def paginate(self, results):
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
            page_ending_result = results[index_end]
            next_token = self._build_next_token(page_ending_result)
        return results_page, next_token
