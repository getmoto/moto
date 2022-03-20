import warnings

from pyparsing import (
    CaselessKeyword,
    OpAssoc,
    ParserElement,
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

# grammar based on Glue.Client.get_partitions(Expression)

ParserElement.enable_packrat()

_LPAR, _RPAR = map(Suppress, "()")

# NOTE these are AWS Athena column names
_IDENTIFIER = Word(alphanums + "._").set_name("identifier")

_NUMBER_LITERAL = pyparsing_common.number.set_name("number")
_STRING_LITERAL = QuotedString(quote_char="'", esc_quote="''").set_name("string")
_LITERAL = (_NUMBER_LITERAL | _STRING_LITERAL).set_name("literal")

_OPERATOR = one_of("= <> > < >= <=").set_name("operator")

_AND, _OR, _IN, _BETWEEN, _LIKE, _NOT, _IS, _NULL = map(
    CaselessKeyword, "and or in between like not is null".split()
)

_CONDITION = (
    _IDENTIFIER + _IS + _NULL
    | _IDENTIFIER + _IS + _NOT + _NULL
    | _IDENTIFIER + _OPERATOR + _LITERAL
    | _IDENTIFIER + _LIKE + _STRING_LITERAL
    | _IDENTIFIER + _IN + _LPAR + delimited_list(_LITERAL, min=1) + _RPAR
    | _IDENTIFIER + _BETWEEN + _LITERAL + _AND + _LITERAL
).set_name("condition")

_BINARY = 2
_EXPRESSION = infix_notation(
    _CONDITION,
    [
        (_AND, _BINARY, OpAssoc.LEFT),
        (_OR, _BINARY, OpAssoc.LEFT),
    ],
).set_name("expression")

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


class PartitionFilter:
    def __init__(self, expression, keys):
        self._expression = None

        if expression is not None:
            warnings.warn("Expression filtering is experimental")
            try:
                self._expression = _EXPRESSION.parse_string(expression)
            except exceptions.ParseException as ex:
                raise ValueError(f"Could not parse expression='{expression}'") from ex

    def __call__(self, values):
        if self._expression is None:
            return True
