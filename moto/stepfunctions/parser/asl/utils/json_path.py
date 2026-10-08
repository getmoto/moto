import re
from typing import Any, Final

from jsonpath_ng.ext import parse
from jsonpath_ng.jsonpath import Index

from moto.stepfunctions.parser.asl.utils.encoding import to_json_str

_PATTERN_SINGLETON_ARRAY_ACCESS_OUTPUT: Final[str] = r"\[\d+\]$"
_PATTERN_SLICE_OR_WILDCARD_ACCESS = (
    r"\$(?:\.[^[]+\[(?:\*|\d*:\d*)\]|\[\*\])(?:\.[^[]+)*$"
)
_PATTERN_FILTER_EXPRESSION: Final[str] = r"\[\s*\?"
_FILTER_OPENING: Final[str] = "[?("


def _is_singleton_array_access(path: str) -> bool:
    # Returns true if the json path terminates with a literal singleton array access.
    return bool(re.search(_PATTERN_SINGLETON_ARRAY_ACCESS_OUTPUT, path))


def _contains_slice_or_wildcard_array(path: str) -> bool:
    # Returns true if the json path contains a slice or wildcard in the array.
    # Slices at the root are discarded, but wildcard at the root is allowed.
    return bool(re.search(_PATTERN_SLICE_OR_WILDCARD_ACCESS, path))


def _contains_filter_expression(path: str) -> bool:
    # Returns true if the json path contains a filter expression `[?(...)]`.
    return bool(re.search(_PATTERN_FILTER_EXPRESSION, path))


def _translate_conjunctions(path: str) -> str:
    """Translate the AWS `&&` filter conjunction to jsonpath_ng's `&`.

    AWS Step Functions' JSONPath dialect combines filter terms with `&&`
    (e.g. `$.items[?(@.a == true && @.b == true)]`), whereas jsonpath_ng
    only understands the single-character `&` operator. Characters inside
    string literals are left untouched.
    """
    if "&&" not in path:
        return path
    result: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(path):
        char = path[index]
        if quote is not None:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == "&" and path.startswith("&&", index):
            result.append(char)
            index += 2
            continue
        result.append(char)
        index += 1
    return "".join(result)


def _split_first_disjunction(path: str) -> tuple[str, str] | None:
    """Split the path at the first top-level `||` inside a filter expression.

    Returns two paths whose filters contain the left/right operand of the
    disjunction, or ``None`` if the path holds no splittable `||`. AWS Step
    Functions' JSONPath dialect gives `&&` a higher precedence than `||`,
    so splitting at the top level of the filter preserves the semantics.
    """
    quote: str | None = None
    paren_depth = 0
    # Innermost open filters as (index of "[?(", depth of its parenthesis).
    filter_stack: list[tuple[int, int]] = []
    index = 0
    while index < len(path):
        char = path[index]
        if quote is not None:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif path.startswith(_FILTER_OPENING, index):
            filter_stack.append((index, paren_depth))
            paren_depth += 1
            index += len(_FILTER_OPENING)
            continue
        elif char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
            if filter_stack and paren_depth == filter_stack[-1][1]:
                filter_stack.pop()
        elif (
            char == "|"
            and path.startswith("||", index)
            and filter_stack
            and paren_depth == filter_stack[-1][1] + 1
        ):
            filter_start, _ = filter_stack[-1]
            filter_end = _find_filter_end(path, filter_start)
            expression_start = filter_start + len(_FILTER_OPENING)
            left_operand = path[expression_start:index].strip()
            right_operand = path[index + 2 : filter_end].strip()
            prefix = path[:expression_start]
            suffix = path[filter_end:]
            return (
                f"{prefix}{left_operand}{suffix}",
                f"{prefix}{right_operand}{suffix}",
            )
        index += 1
    return None


def _find_filter_end(path: str, filter_start: int) -> int:
    """Index of the closing parenthesis of the filter opened at filter_start."""
    quote: str | None = None
    depth = 0
    for index in range(filter_start + len(_FILTER_OPENING) - 1, len(path)):
        char = path[index]
        if quote is not None:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError(f"Unterminated filter expression in JSONPath '{path}'")


def _expand_disjunctions(path: str) -> list[str]:
    """Expand `||` filter disjunctions into one path per disjunct."""
    if "||" not in path:
        return [path]
    split = _split_first_disjunction(path)
    if split is None:
        return [path]
    left, right = split
    return _expand_disjunctions(left) + _expand_disjunctions(right)


def _document_order_key(match: Any) -> list[Any]:
    # Natural-sort key over the full path, so `items.[2]` sorts before
    # `items.[10]` and merged disjunction matches follow document order.
    return [
        int(token) if token.isdigit() else token
        for token in re.split(r"(\d+)", str(match.full_path))
    ]


class NoSuchJsonPathError(Exception):
    json_path: Final[str]
    data: Final[Any]
    _message: str | None

    def __init__(self, json_path: str, data: Any):
        self.json_path = json_path
        self.data = data
        self._message = None

    @property
    def message(self) -> str:
        if self._message is None:
            data_json_str = to_json_str(self.data)
            self._message = f"The JSONPath '{self.json_path}' could not be found in the input '{data_json_str}'"
        return self._message

    def __str__(self):
        return self.message


def extract_json(path: str, data: Any) -> Any:
    variants = _expand_disjunctions(_translate_conjunctions(path))
    if len(variants) == 1:
        matches = parse(variants[0]).find(data)
    else:
        # AWS-dialect `||` disjunction: evaluate one path per disjunct and
        # merge the matches back into document order.
        matches_by_path = {}
        for variant in variants:
            for match in parse(variant).find(data):
                matches_by_path.setdefault(str(match.full_path), match)
        matches = sorted(matches_by_path.values(), key=_document_order_key)

    if not matches:
        if _contains_slice_or_wildcard_array(path) or _contains_filter_expression(path):
            # On AWS, filters (and slices/wildcards) that match nothing
            # produce an empty list rather than an error.
            return []
        raise NoSuchJsonPathError(json_path=path, data=data)

    if (
        len(matches) > 1
        or isinstance(matches[0].path, Index)
        # Last condition is different from LS and fixes a very specific bug
        # https://github.com/getmoto/moto/issues/7825
        or (matches[0].context and isinstance(matches[0].context.path, Index))
    ):
        value = [match.value for match in matches]

        # AWS StepFunctions breaks jsonpath specifications and instead
        # unpacks literal singleton array accesses.
        if _is_singleton_array_access(path=path) and len(value) == 1:
            value = value[0]
    else:
        value = matches[0].value

    return value
