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


class _PartitionFilterExpressionCache:
    def __init__(self):
        # build grammar according to Glue.Client.get_partitions(Expression)
        lpar, rpar = map(Suppress, "()")

        # NOTE these are AWS Athena column name best practices
        ident = Word(alphanums + "._").set_name("ident")

        num_literal = pyparsing_common.number.set_name("number")
        str_literal = QuotedString(quote_char="'", esc_quote="''").set_name("str")
        any_literal = (num_literal | str_literal).set_name("literal")

        bin_op = one_of("= <> > < >= <=").set_name("binary op")

        and_, or_, in_, between, like, not_, is_, null = map(
            CaselessKeyword, "and or in between like not is null".split()
        )

        cond = (
            ident + is_ + null
            | ident + is_ + not_ + null
            | ident + bin_op + any_literal
            | ident + like + str_literal
            | ident + in_ + lpar + delimited_list(any_literal, min=1) + rpar
            | ident + between + any_literal + and_ + any_literal
        ).set_name("cond")

        # conditions can be joined using 2-ary AND and/or OR
        self._expr = infix_notation(
            cond, [(and_, 2, OpAssoc.LEFT), (or_, 2, OpAssoc.LEFT)]
        ).set_name("expr")

        self._cache = {}

    def get(self, expression):
        if expression is None:
            return None

        if expression not in self._cache:
            ParserElement.enable_packrat()

            try:
                self._cache[expression] = self._expr.parse_string(expression)
            except exceptions.ParseException as ex:
                raise ValueError(f"Could not parse expression='{expression}'") from ex

        return self._cache[expression]


_PARTITION_FILTER_EXPRESSION_CACHE = _PartitionFilterExpressionCache()


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
        self.expression = expression
        self.keys = keys

    def __call__(self, value):
        if self.expression is None:
            return True

        warnings.warn("Expression filtering is experimental")
        expression = _PARTITION_FILTER_EXPRESSION_CACHE.get(self.expression)
