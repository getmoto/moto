import abc
import operator
import re
import warnings
from datetime import date, datetime, timedelta
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

from .exceptions import InvalidInputException, InvalidStateException

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


def _cast(type_: str, value: Any) -> Union[date, datetime, float, int, str]:
    if type_ in ("bigint", "int", "smallint", "tinyint"):
        try:
            return int(value)  # no size is enforced
        except:
            raise ValueError(f'"{value}" is not an integer.')

    if type_ == "decimal":
        try:
            return float(value)
        except:
            raise ValueError(f"{value} is not a decimal.")

    if type_ in ("char", "string", "varchar"):
        return str(value)  # no length is enforced

    if type_ == "date":
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except:
            raise ValueError(f"{value} is not a date.")

    if type_ == "timestamp":
        match = re.search(
            r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?P<ns>\.\d{1,9})?$",
            value,
        )
        if match is None:
            raise ValueError(
                "Timestamp format must be yyyy-mm-dd hh:mm:ss[.fffffffff]"
                f" {value} is not a timestamp."
            )

        timestamp = datetime.strptime(match.group("timestamp"), "%Y-%m-%d %H:%M:%S")

        nanoseconds = match.group("ns")
        if nanoseconds is not None:
            # strip leading dot and left pad with zeros to nanoseconds
            nanoseconds = nanoseconds[1:].zfill(9)
            for i, nanosecond in enumerate(reversed(nanoseconds)):
                # precision loss here, as nanoseconds are not supported in datetime
                timestamp += timedelta(microseconds=(int(nanosecond) * 10**i) / 1000)

        return timestamp

    raise InvalidInputException(
        "An error occurred (InvalidInputException) when calling the"
        f" GetPartitions operation: Unknown type : '{type_}'"
    )


class _Expr(abc.ABC):
    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> Any:
        raise NotImplementedError()


class _Ident(_Expr):
    def __init__(self, tokens: ParseResults):
        self.ident: str = tokens[0]

    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> Any:
        for key, value in zip(part_keys, part_input["Values"]):
            if self.ident == key["Name"]:
                try:
                    return _cast(key["Type"], value)
                except ValueError as e:
                    # existing partition values cannot be cast to current schema
                    raise InvalidStateException(
                        "An error occurred (InvalidStateException) when calling the"
                        f" GePartitions operation: {e}"
                    )

        raise InvalidInputException(
            "An error occurred (InvalidInputException) when calling the"
            f" GetPartitions operation: Unknown column '{self.ident}'"
        )

    def leval(self, part_keys: List[Dict[str, str]], literal: Any) -> Any:
        # evaluate literal by simulating partition input
        for key in part_keys:
            if self.ident == key["Name"]:
                try:
                    return _cast(key["Type"], literal)
                except ValueError as e:
                    # expression literal cannot be cast to current schema
                    raise InvalidInputException(
                        "An error occurred (InvalidInputException) when calling the"
                        f" GePartitions operation: {e}"
                    )

        raise InvalidInputException(
            "An error occurred (InvalidInputException) when calling the"
            f" GetPartitions operation: Unknown column '{self.ident}'"
        )

    def type_(self, part_keys: List[Dict[str, str]]) -> str:
        for key in part_keys:
            if self.ident == key["Name"]:
                return key["Type"]

        raise InvalidInputException(
            "An error occurred (InvalidInputException) when calling the"
            f" GetPartitions operation: Unknown column '{self.ident}'"
        )


class _IsNull(_Expr):
    def __init__(self, tokens: ParseResults):
        self.ident: _Ident = tokens[0]

    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> bool:
        return self.ident.eval(part_keys, part_input) is None


class _IsNotNull(_Expr):
    def __init__(self, tokens: ParseResults):
        self.ident: _Ident = tokens[0]

    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> bool:
        return self.ident.eval(part_keys, part_input) is not None


class _BinOp(_Expr):
    def __init__(self, tokens: ParseResults):
        self.ident: _Ident = tokens[0]
        self.bin_op: str = tokens[1]
        self.literal: Any = tokens[2]

    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> bool:
        ident = self.ident.eval(part_keys, part_input)

        # simulate partition input for the lateral
        rhs = self.ident.leval(part_keys, self.literal)

        return {
            "<>": operator.ne,
            ">=": operator.ge,
            "<=": operator.le,
            ">": operator.gt,
            "<": operator.lt,
            "=": operator.eq,
        }[self.bin_op](ident, rhs)


class _Like(_Expr):
    def __init__(self, tokens: ParseResults):
        self.ident: _Ident = tokens[0]
        self.literal: str = tokens[2]

    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> bool:
        type_ = self.ident.type_(part_keys)
        if type_ in ("bigint", "int", "smallint", "tinyint"):
            raise InvalidInputException(
                "An error occurred (InvalidInputException) when calling the "
                "GetPartitions operation: Integral data type"
                " doesn't support operation 'LIKE'"
            )

        if type_ in ("date", "decimal", "timestamp"):
            raise InvalidInputException(
                "An error occurred (InvalidInputException) when calling the "
                f"GetPartitions operation: {type_[0].upper()}{type_[1:]} data type"
                " doesn't support operation 'LIKE'"
            )

        ident = self.ident.eval(part_keys, part_input)
        assert isinstance(ident, str)
        pattern = (
            # LIKE clauses always start at the beginning
            "^"
            # convert wildcards to regex, no literal matches possible
            + _cast("string", self.literal).replace("_", ".").replace("%", ".*")
            # LIKE clauses always stop at the end
            + "$"
        )

        return re.search(pattern, ident) is not None


class _In(_Expr):
    def __init__(self, tokens: ParseResults):
        self.ident: _Ident = tokens[0]
        self.values: List[Any] = tokens[2:]

    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> bool:
        ident = self.ident.eval(part_keys, part_input)
        values = (self.ident.leval(part_keys, value) for value in self.values)

        return ident in values


class _Between(_Expr):
    def __ini__(self, tokens: ParseResults):
        self.ident: _Ident = tokens[0]
        self.left: Any = tokens[2]
        self.right: Any = tokens[4]

    def eval(self, part_keys: List[Dict[str, str]], part_input: Dict[str, Any]) -> bool:
        ident = self.ident.eval(part_keys, part_input)
        left = self.ident.leval(part_keys, self.left)
        right = self.ident.leval(part_keys, self.right)

        return left <= ident <= right


class _PartitionFilterExpressionCache:
    def __init__(self):
        # build grammar according to Glue.Client.get_partitions(Expression)
        lpar, rpar = map(Suppress, "()")

        # NOTE these are AWS Athena column name best practices
        ident = Word(alphanums + "._").set_parse_action(_Ident).set_name("ident")

        number = pyparsing_common.number.set_name("number")
        string = QuotedString(quote_char="'", esc_quote="''").set_name("string")
        literal = (number | string).set_name("literal")
        literal_list = delimited_list(literal, min=1).set_name("list")

        bin_op = one_of("<> >= <= > < =").set_name("binary op")

        and_, or_, in_, between, like, not_, is_, null = map(
            CaselessKeyword, "and or in between like not is null".split()
        )

        cond = (
            (ident + is_ + null).set_parse_action(_IsNull)
            | (ident + is_ + not_ + null).set_parse_action(_IsNotNull)
            | (ident + bin_op + literal).set_parse_action(_BinOp)
            | (ident + like + string).set_parse_action(_Like)
            | (ident + in_ + lpar + literal_list + rpar).set_parse_action(_In)
            | (ident + between + literal + and_ + literal).set_parse_action(_Between)
        ).set_name("cond")

        # conditions can be joined using 2-ary AND and/or OR
        expr = infix_notation(cond, [(and_, 2, OpAssoc.LEFT), (or_, 2, OpAssoc.LEFT)])
        self._expr = expr.set_name("expr")

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
                raise InvalidInputException(
                    "An error occurred (InvalidInputException) when calling the"
                    f" GetPartitions operation: Unsupported expression '{expression}'"
                )

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
