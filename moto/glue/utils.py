import abc
import itertools
import operator
import re
import warnings
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from pyparsing import (
    CaselessKeyword,
    OpAssoc,
    ParserElement,
    ParseResults,
    QuotedString,
    Suppress,
    Word,
    alphanums,
    delimited_list,
    exceptions,
    infix_notation,
    one_of,
    pyparsing_common,
)

# LIKE only for strings
# LIKE supports % (zero or more matches) and _ (exactly one match) wildcards
# unary not supported, e.g. "not column > 4" does not work
# NOT LIKE not supported
# references not supported "column_1 > column_2" does not work
# no nested expressions
# only column name to the left, literal to the right
# is / is not only with null; null only with is / is not
# literal value is cast to partition type before comparing
# parentheses can be used to group, nested allowed
# scientific notation for decimal partition columns ok
# IN can contain both string and numeric literals
# arbitrary whitespace (including none) between operands and operators
# literals in parentheses are allowed, e.g. col = (5)

# partition key types that can be filtered on
_ALLOWED_KEY_TYPES = (
    "bigint",  # [-2^63, 2^63 - 1]
    "date",  # 'YYYY-MM-DD'
    "decimal",  # floating point, integer or scientific
    "int",  # [-2^31, 2^31 - 1]
    "long",  # NOTE supposedly supported, assume bigint
    "smallint",  # [-2^15, 2^15 - 1]
    "string",  # single quoted string
    "timestamp",  # 'yyyy-MM-dd HH:mm:ss[.fffffffff]'
    "tinyint",  # [-2^7, 2^7 - 1]
)


def _cast(type_: str, value: str) -> Union[date, datetime, float, int, str]:
    if type_ not in _ALLOWED_KEY_TYPES:
        # TODO raise appropriate exception for unsupported types
        assert False

    # TODO implement


class _Expr(abc.ABC):
    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> Any:
        raise NotImplementedError()


class _Ident(_Expr):
    def __init__(self, tokens: ParseResults):
        self.ident: str = tokens[0]

    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> Any:
        for key, value in zip(part_keys, part_input["Values"]):
            if self.ident == key["Name"]:
                return _cast(key["Type"], value)

        # TODO raise appropriate exception for unknown columns
        assert False


class _IdentIsNull(_Expr):
    def __init__(self, tokens: ParseResults):
        self.ident: _Ident = tokens[0]

    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> bool:
        return self.ident.eval(part_keys, part_input) is None


class _IdentIsNotNull(_Expr):
    def __init__(self, tokens: ParseResults):
        self.ident: _Ident = tokens[0]

    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> bool:
        return self.ident.eval(part_keys, part_input) is not None


class _IdentBinOp(_Expr):
    def __init__(self, tokens: ParseResults):
        self.ident: _Ident = tokens[0]
        self.bin_op: str = tokens[1]
        self.literal: str = tokens[2]

    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> bool:
        lhs = self.ident.eval(part_keys, part_input)

        # simulate partition input for the lateral
        rhs = self.ident.eval(part_keys, {"Values": itertools.repeat(self.literal)})

        return {
            "<>": operator.ne,
            ">=": operator.ge,
            "<=": operator.le,
            ">": operator.gt,
            "<": operator.lt,
            "=": operator.eq,
        }[self.bin_op](lhs, rhs)


class _IdentLike(_Expr):
    def __init__(self, tokens: ParseResults):
        self.ident: _Ident = tokens[0]
        self.literal: str = tokens[2]

    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> bool:
        lhs = self.ident.eval(part_keys, part_input)
        if not isinstance(lhs, str):
            # TODO raise appropriate exception for LIKE without string
            assert False

        rhs = (
            # LIKE clauses always start at the beginning
            "^"
            # convert wildcards to regex, no literal matches possible
            + _cast("string", self.literal).replace("_", ".").replace("%", ".*")
            # LIKE clauses always stop at the end
            + "$"
        )

        return re.search(rhs, lhs) is not None


class _PartitionFilterExpressionCache:
    def __init__(self):
        # build grammar according to Glue.Client.get_partitions(Expression)
        lpar, rpar = map(Suppress, "()")

        # NOTE these are AWS Athena column name best practices
        ident = Word(alphanums + "._")
        ident.set_parse_action(_Ident).set_name("ident")

        num_literal = pyparsing_common.number.set_name("number")
        str_literal = QuotedString(quote_char="'", esc_quote="''").set_name("str")
        any_literal = (num_literal | str_literal).set_name("literal")

        bin_op = one_of("<> >= <= > < =").set_name("binary op")

        and_, or_, in_, between, like, not_, is_, null = map(
            CaselessKeyword, "and or in between like not is null".split()
        )

        cond = (
            (ident + is_ + null).set_parse_action(_IdentIsNull)
            | (ident + is_ + not_ + null).set_parse_action(_IdentIsNotNull)
            | (ident + bin_op + any_literal).set_parse_action(_IdentBinOp)
            | (ident + like + str_literal).set_parse_action(_IdentLike)
            | ident + in_ + lpar + delimited_list(any_literal, min=1) + rpar
            | ident + between + any_literal + and_ + any_literal
        ).set_name("cond")

        # conditions can be joined using 2-ary AND and/or OR
        self._expr = infix_notation(
            cond, [(and_, 2, OpAssoc.LEFT), (or_, 2, OpAssoc.LEFT)]
        ).set_name("expr")

        self._cache: Dict[str, _Expr] = {}

    def get(self, expression: Optional[str]) -> Optional[_Expr]:
        if expression is None:
            return None

        if expression not in self._cache:
            ParserElement.enable_packrat()

            try:
                expr: ParseResults = self._expr.parse_string(expression, parse_all=True)
                self._cache[expression] = expr[0]
            except exceptions.ParseException as ex:
                raise ValueError(f"Could not parse expression='{expression}'") from ex

        return self._cache[expression]


_PARTITION_FILTER_EXPRESSION_CACHE = _PartitionFilterExpressionCache()


class PartitionFilter:
    def __init__(self, expression: Optional[str], part_keys: List[Dict[str, str]]):
        self.expression = expression
        self.part_keys = part_keys

    def __call__(self, part_input: Dict[str, Any]) -> bool:
        warnings.warn("Expression filtering is experimental")

        expression = _PARTITION_FILTER_EXPRESSION_CACHE.get(self.expression)
        if expression is None:
            return True

        return expression.eval(self.part_keys, part_input)
