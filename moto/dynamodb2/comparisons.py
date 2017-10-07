from __future__ import unicode_literals
import re
import six
# TODO add tests for all of these

EQ_FUNCTION = lambda item_value, test_value: item_value == test_value  # flake8: noqa
NE_FUNCTION = lambda item_value, test_value: item_value != test_value  # flake8: noqa
LE_FUNCTION = lambda item_value, test_value: item_value <= test_value  # flake8: noqa
LT_FUNCTION = lambda item_value, test_value: item_value < test_value  # flake8: noqa
GE_FUNCTION = lambda item_value, test_value: item_value >= test_value  # flake8: noqa
GT_FUNCTION = lambda item_value, test_value: item_value > test_value  # flake8: noqa

COMPARISON_FUNCS = {
    'EQ': EQ_FUNCTION,
    '=': EQ_FUNCTION,

    'NE': NE_FUNCTION,
    '!=': NE_FUNCTION,

    'LE': LE_FUNCTION,
    '<=': LE_FUNCTION,

    'LT': LT_FUNCTION,
    '<': LT_FUNCTION,

    'GE': GE_FUNCTION,
    '>=': GE_FUNCTION,

    'GT': GT_FUNCTION,
    '>': GT_FUNCTION,

    'NULL': lambda item_value: item_value is None,
    'NOT_NULL': lambda item_value: item_value is not None,
    'CONTAINS': lambda item_value, test_value: test_value in item_value,
    'NOT_CONTAINS': lambda item_value, test_value: test_value not in item_value,
    'BEGINS_WITH': lambda item_value, test_value: item_value.startswith(test_value),
    'IN': lambda item_value, *test_values: item_value in test_values,
    'BETWEEN': lambda item_value, lower_test_value, upper_test_value: lower_test_value <= item_value <= upper_test_value,
}


def get_comparison_func(range_comparison):
    return COMPARISON_FUNCS.get(range_comparison)


#
def get_filter_expression(expr, names, values):
    # Examples
    # expr = 'Id > 5 AND attribute_exists(test) AND Id BETWEEN 5 AND 6 OR length < 6 AND contains(test, 1) AND 5 IN (4,5, 6) OR (Id < 5 AND 5 > Id)'
    # expr = 'Id > 5 AND Subs < 7'

    # Need to do some dodgyness for NOT i think.
    if 'NOT' in expr:
        raise NotImplementedError('NOT not supported yet')

    if names is None:
        names = {}
    if values is None:
        values = {}

    # Do substitutions
    for key, value in names.items():
        expr = expr.replace(key, value)
    for key, value in values.items():
        if 'N' in value:
            expr.replace(key, float(value['N']))
        else:
            expr = expr.replace(key, value['S'])

    # Remove all spaces, tbf we could just skip them in the next step.
    # The number of known options is really small so we can do a fair bit of cheating
    expr = list(re.sub('\s', '', expr))  # 'Id>5ANDattribute_exists(test)ORNOTlength<6'

    # DodgyTokenisation stage 1
    def is_value(val):
        return val not in ('<', '>', '=', '(', ')')

    def contains_keyword(val):
        for kw in ('BETWEEN', 'IN', 'AND', 'OR', 'NOT'):
            if kw in val:
                return kw
        return None

    def is_function(val):
        return val in ('attribute_exists', 'attribute_not_exists', 'attribute_type', 'begins_with', 'contains', 'size')

    # Does the main part of splitting between sections of characters
    tokens = []
    stack = ''
    while len(expr) > 0:
        current_char = expr.pop(0)

        if current_char == ',':  # Split params ,
            if len(stack) > 0:
                tokens.append(stack)
            stack = ''
        elif is_value(current_char):
            stack += current_char

            kw = contains_keyword(stack)
            if kw is not None:
                # We have a kw in the stack, could be AND or something like 5AND
                tmp = stack.replace(kw, '')
                if len(tmp) > 0:
                    tokens.append(tmp)
                tokens.append(kw)
                stack = ''
        else:
            if len(stack) > 0:
                tokens.append(stack)
            tokens.append(current_char)
            stack = ''
    if len(stack) > 0:
        tokens.append(stack)

    # DodgyTokenisation stage 2, it groups together some elements to make RPN'ing it later easier.
    tokens2 = []
    token_iterator = iter(tokens)
    for token in token_iterator:
        if token == '(':
            tuple_list = []

            next_token = six.next(token_iterator)
            while next_token != ')':
                tuple_list.append(next_token)
                next_token = six.next(token_iterator)

            tokens2.append(tuple(tuple_list))
        elif token == 'BETWEEN':
            op1 = six.next(token_iterator)
            and_op = six.next(token_iterator)
            assert and_op == 'AND'
            op2 = six.next(token_iterator)
            tokens2.append('BETWEEN')
            tokens2.append((op1, op2))

        elif is_function(token):
            function_list = [token]

            lbracket = six.next(token_iterator)
            assert lbracket == '('

            next_token = six.next(token_iterator)
            while next_token != ')':
                function_list.append(next_token)
                next_token = six.next(token_iterator)

            tokens2.append(function_list)

        else:
            try:
                token = int(token)
            except ValueError:
                try:
                    token = float(token)
                except ValueError:
                    pass
            tokens2.append(token)

    # Start of the Shunting-Yard algorigth. <-- Proper beast algorithm!
    def is_number(val):
        return val not in ('<', '>', '=', '>=', '<=', '<>', 'BETWEEN', 'IN', 'AND', 'OR', 'NOT')

    def is_op(val):
        return val in ('<', '>', '=', '>=', '<=', '<>', 'BETWEEN', 'IN', 'AND', 'OR', 'NOT')

    OPS = {'<': 5, '>': 5, '=': 5, '>=': 5, '<=': 5, '<>': 5, 'IN': 8, 'AND': 11, 'OR': 12, 'NOT': 10, 'BETWEEN': 9, '(': 1, ')': 1}

    output = []
    op_stack = []
    # Basically takes in an infix notation calculation, converts it to a reverse polish notation where there is no
    # ambiguaty on which order operators are applied.
    while len(tokens2) > 0:
        token = tokens2.pop(0)

        if token == '(':
            op_stack.append(token)
        elif token == ')':
            while len(op_stack) > 0 and op_stack[-1] != '(':
                output.append(op_stack.pop())
            if len(op_stack) == 0:
                # No left paren on the stack, error
                raise Exception('Missing left paren')

            # Pop off the left paren
            op_stack.pop()

        elif is_number(token):
            output.append(token)
        else:
            # Must be operator kw
            while len(op_stack) > 0 and OPS[op_stack[-1]] <= OPS[token]:
                output.append(op_stack.pop())
            op_stack.append(token)
    while len(op_stack) > 0:
        output.append(op_stack.pop())

    # Hacky funcition to convert dynamo functions (which are represented as lists) to their Class equivelent
    def to_func(val):
        if isinstance(val, list):
            func_name = val.pop(0)
            # Expand rest of the list to arguments
            val = FUNC_CLASS[func_name](*val)

        return val

    # Simple reverse polish notation execution. Builts up a nested filter object.
    # The filter object then takes a dynamo item and returns true/false
    stack = []
    for token in output:
        if is_op(token):
            op2 = stack.pop()
            op1 = stack.pop()

            op_cls = OP_CLASS[token]
            stack.append(op_cls(op1, op2))
        else:
            stack.append(to_func(token))

    return stack[0]


class Op(object):
    """
    Base class for a FilterExpression operator
    """
    OP = ''

    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def _lhs(self, item):
        """
        :type item: moto.dynamodb2.models.Item
        """
        lhs = self.lhs
        if isinstance(self.lhs, (Op, Func)):
            lhs = self.lhs.expr(item)
        elif isinstance(self.lhs, str):
            try:
                lhs = item.attrs[self.lhs].cast_value
            except Exception:
                pass

        return lhs

    def _rhs(self, item):
        rhs = self.rhs
        if isinstance(self.rhs, (Op, Func)):
            rhs = self.rhs.expr(item)
        elif isinstance(self.lhs, str):
            try:
                rhs = item.attrs[self.rhs].cast_value
            except Exception:
                pass
        return rhs

    def expr(self, item):
        return True

    def __repr__(self):
        return '({0} {1} {2})'.format(self.lhs, self.OP, self.rhs)


class Func(object):
    """
    Base class for a FilterExpression function
    """
    FUNC = 'Unknown'

    def expr(self, item):
        return True

    def __repr__(self):
        return 'Func(...)'.format(self.FUNC)


class OpAnd(Op):
    OP = 'AND'

    def expr(self, item):
        lhs = self._lhs(item)
        rhs = self._rhs(item)
        return lhs and rhs


class OpLessThan(Op):
    OP = '<'

    def expr(self, item):
        lhs = self._lhs(item)
        rhs = self._rhs(item)
        return lhs < rhs


class OpGreaterThan(Op):
    OP = '>'

    def expr(self, item):
        lhs = self._lhs(item)
        rhs = self._rhs(item)
        return lhs > rhs


class OpEqual(Op):
    OP = '='

    def expr(self, item):
        lhs = self._lhs(item)
        rhs = self._rhs(item)
        return lhs == rhs


class OpNotEqual(Op):
    OP = '<>'

    def expr(self, item):
        lhs = self._lhs(item)
        rhs = self._rhs(item)
        return lhs == rhs


class OpLessThanOrEqual(Op):
    OP = '<='

    def expr(self, item):
        lhs = self._lhs(item)
        rhs = self._rhs(item)
        return lhs <= rhs


class OpGreaterThanOrEqual(Op):
    OP = '>='

    def expr(self, item):
        lhs = self._lhs(item)
        rhs = self._rhs(item)
        return lhs >= rhs


class OpOr(Op):
    OP = 'OR'

    def expr(self, item):
        lhs = self._lhs(item)
        rhs = self._rhs(item)
        return lhs or rhs


class OpIn(Op):
    OP = 'IN'

    def expr(self, item):
        lhs = self._lhs(item)
        rhs = self._rhs(item)
        return lhs in rhs


class OpBetween(Op):
    OP = 'BETWEEN'

    def expr(self, item):
        lhs = self._lhs(item)
        rhs = self._rhs(item)
        return rhs[0] <= lhs <= rhs[1]


class FuncAttrExists(Func):
    FUNC = 'attribute_exists'

    def __init__(self, attribute):
        self.attr = attribute

    def expr(self, item):
        return self.attr in item.attrs


class FuncAttrNotExists(Func):
    FUNC = 'attribute_not_exists'

    def __init__(self, attribute):
        self.attr = attribute

    def expr(self, item):
        return self.attr not in item.attrs


class FuncAttrType(Func):
    FUNC = 'attribute_type'

    def __init__(self, attribute, _type):
        self.attr = attribute
        self.type = _type

    def expr(self, item):
        return self.attr in item.attrs and item.attrs[self.attr].type == self.type


class FuncBeginsWith(Func):
    FUNC = 'begins_with'

    def __init__(self, attribute, substr):
        self.attr = attribute
        self.substr = substr

    def expr(self, item):
        return self.attr in item.attrs and item.attrs[self.attr].type == 'S' and item.attrs[self.attr].value.startswith(self.substr)


class FuncContains(Func):
    FUNC = 'contains'

    def __init__(self, attribute, operand):
        self.attr = attribute
        self.operand = operand

    def expr(self, item):
        if self.attr not in item.attrs:
            return False

        if item.attrs[self.attr].type in ('S', 'SS', 'NS', 'BS', 'L', 'M'):
            return self.operand in item.attrs[self.attr].value
        return False


class FuncSize(Func):
    FUNC = 'contains'

    def __init__(self, attribute):
        self.attr = attribute

    def expr(self, item):
        if self.attr not in item.attrs:
            raise ValueError('Invalid option')

        if item.attrs[self.attr].type in ('S', 'SS', 'NS', 'B', 'BS', 'L', 'M'):
            return len(item.attrs[self.attr].value)
        raise ValueError('Invalid option')


OP_CLASS = {
    'AND': OpAnd,
    'OR': OpOr,
    'IN': OpIn,
    'BETWEEN': OpBetween,
    '<': OpLessThan,
    '>': OpGreaterThan,
    '<=': OpLessThanOrEqual,
    '>=': OpGreaterThanOrEqual,
    '=': OpEqual,
    '<>': OpNotEqual
}

FUNC_CLASS = {
    'attribute_exists': FuncAttrExists,
    'attribute_not_exists': FuncAttrNotExists,
    'attribute_type': FuncAttrType,
    'begins_with': FuncBeginsWith,
    'contains': FuncContains,
    'size': FuncSize
}
