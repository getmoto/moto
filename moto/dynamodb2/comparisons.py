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

    # NULL means the value should not exist at all
    'NULL': lambda item_value: False,
    # NOT_NULL means the value merely has to exist, and values of None are valid
    'NOT_NULL': lambda item_value: True,
    'CONTAINS': lambda item_value, test_value: test_value in item_value,
    'NOT_CONTAINS': lambda item_value, test_value: test_value not in item_value,
    'BEGINS_WITH': lambda item_value, test_value: item_value.startswith(test_value),
    'IN': lambda item_value, *test_values: item_value in test_values,
    'BETWEEN': lambda item_value, lower_test_value, upper_test_value: lower_test_value <= item_value <= upper_test_value,
}


def get_comparison_func(range_comparison):
    return COMPARISON_FUNCS.get(range_comparison)


class RecursionStopIteration(StopIteration):
    pass


def get_filter_expression(expr, names, values):
    # Examples
    # expr = 'Id > 5 AND attribute_exists(test) AND Id BETWEEN 5 AND 6 OR length < 6 AND contains(test, 1) AND 5 IN (4,5, 6) OR (Id < 5 AND 5 > Id)'
    # expr = 'Id > 5 AND Subs < 7'
    if names is None:
        names = {}
    if values is None:
        values = {}

    # Do substitutions
    for key, value in names.items():
        expr = expr.replace(key, value)

    # Store correct types of values for use later
    values_map = {}
    for key, value in values.items():
        if 'N' in value:
            values_map[key] = float(value['N'])
        elif 'BOOL' in value:
            values_map[key] = value['BOOL']
        elif 'S' in value:
            values_map[key] = value['S']
        elif 'NS' in value:
            values_map[key] = tuple(value['NS'])
        elif 'SS' in value:
            values_map[key] = tuple(value['SS'])
        elif 'L' in value:
            values_map[key] = tuple(value['L'])
        else:
            raise NotImplementedError()

    # Remove all spaces, tbf we could just skip them in the next step.
    # The number of known options is really small so we can do a fair bit of cheating
    expr = list(expr.strip())

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

        if current_char == ' ':
            if len(stack) > 0:
                tokens.append(stack)
            stack = ''
        elif current_char == ',':  # Split params ,
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

    def is_op(val):
        return val in ('<', '>', '=', '>=', '<=', '<>', 'BETWEEN', 'IN', 'AND', 'OR', 'NOT')

    # DodgyTokenisation stage 2, it groups together some elements to make RPN'ing it later easier.
    def handle_token(token, tokens2, token_iterator):
        # ok so this essentially groups up some tokens to make later parsing easier,
        # when it encounters brackets it will recurse and then unrecurse when RecursionStopIteration is raised.
        if token == ')':
            raise RecursionStopIteration()  # Should be recursive so this should work
        elif token == '(':
            temp_list = []

            try:
                while True:
                    next_token = six.next(token_iterator)
                    handle_token(next_token, temp_list, token_iterator)
            except RecursionStopIteration:
                pass  # Continue
            except StopIteration:
                ValueError('Malformed filter expression, type1')

            # Sigh, we only want to group a tuple if it doesnt contain operators
            if any([is_op(item) for item in temp_list]):
                # Its an expression
                tokens2.append('(')
                tokens2.extend(temp_list)
                tokens2.append(')')
            else:
                tokens2.append(tuple(temp_list))
        elif token == 'BETWEEN':
            field = tokens2.pop()
            # if values map contains a number, it would be a float
            # so we need to int() it anyway
            op1 = six.next(token_iterator)
            op1 = int(values_map.get(op1, op1))
            and_op = six.next(token_iterator)
            assert and_op == 'AND'
            op2 = six.next(token_iterator)
            op2 = int(values_map.get(op2, op2))
            tokens2.append(['between', field, op1, op2])
        elif is_function(token):
            function_list = [token]

            lbracket = six.next(token_iterator)
            assert lbracket == '('

            next_token = six.next(token_iterator)
            while next_token != ')':
                if next_token in values_map:
                    next_token = values_map[next_token]
                function_list.append(next_token)
                next_token = six.next(token_iterator)

            tokens2.append(function_list)
        else:
            # Convert tokens back to real types
            if token in values_map:
                token = values_map[token]

            # Need to join >= <= <>
            if len(tokens2) > 0 and ((tokens2[-1] == '>' and token == '=') or (tokens2[-1] == '<' and token == '=') or (tokens2[-1] == '<' and token == '>')):
                tokens2.append(tokens2.pop() + token)
            else:
                tokens2.append(token)

    tokens2 = []
    token_iterator = iter(tokens)
    for token in token_iterator:
        handle_token(token, tokens2, token_iterator)

    # Start of the Shunting-Yard algorithm. <-- Proper beast algorithm!
    def is_number(val):
        return val not in ('<', '>', '=', '>=', '<=', '<>', 'BETWEEN', 'IN', 'AND', 'OR', 'NOT')

    OPS = {'<': 5, '>': 5, '=': 5, '>=': 5, '<=': 5, '<>': 5, 'IN': 8, 'AND': 11, 'OR': 12, 'NOT': 10, 'BETWEEN': 9, '(': 100, ')': 100}

    def shunting_yard(token_list):
        output = []
        op_stack = []

        # Basically takes in an infix notation calculation, converts it to a reverse polish notation where there is no
        # ambiguity on which order operators are applied.
        while len(token_list) > 0:
            token = token_list.pop(0)

            if token == '(':
                op_stack.append(token)
            elif token == ')':
                while len(op_stack) > 0 and op_stack[-1] != '(':
                    output.append(op_stack.pop())
                lbracket = op_stack.pop()
                assert lbracket == '('

            elif is_number(token):
                output.append(token)
            else:
                # Must be operator kw

                # Cheat, NOT is our only RIGHT associative operator, should really have dict of operator associativity
                while len(op_stack) > 0 and OPS[op_stack[-1]] <= OPS[token] and op_stack[-1] != 'NOT':
                    output.append(op_stack.pop())
                op_stack.append(token)
        while len(op_stack) > 0:
            output.append(op_stack.pop())

        return output

    output = shunting_yard(tokens2)

    # Hacky function to convert dynamo functions (which are represented as lists) to their Class equivalent
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
            op_cls = OP_CLASS[token]

            if token == 'NOT':
                op1 = stack.pop()
                op2 = True
            else:
                op2 = stack.pop()
                op1 = stack.pop()

            stack.append(op_cls(op1, op2))
        else:
            stack.append(to_func(token))

    result = stack.pop(0)
    if len(stack) > 0:
        raise ValueError('Malformed filter expression, type2')

    return result


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
        elif isinstance(self.lhs, six.string_types):
            try:
                lhs = item.attrs[self.lhs].cast_value
            except Exception:
                pass

        return lhs

    def _rhs(self, item):
        rhs = self.rhs
        if isinstance(self.rhs, (Op, Func)):
            rhs = self.rhs.expr(item)
        elif isinstance(self.rhs, six.string_types):
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


class OpNot(Op):
    OP = 'NOT'

    def expr(self, item):
        lhs = self._lhs(item)

        return not lhs

    def __str__(self):
        return '({0} {1})'.format(self.OP, self.lhs)


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
        return lhs != rhs


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
            raise ValueError('Invalid attribute name {0}'.format(self.attr))

        if item.attrs[self.attr].type in ('S', 'SS', 'NS', 'B', 'BS', 'L', 'M'):
            return len(item.attrs[self.attr].value)
        raise ValueError('Invalid filter expression')


class FuncBetween(Func):
    FUNC = 'between'

    def __init__(self, attribute, start, end):
        self.attr = attribute
        self.start = start
        self.end = end

    def expr(self, item):
        if self.attr not in item.attrs:
            raise ValueError('Invalid attribute name {0}'.format(self.attr))

        return self.start <= item.attrs[self.attr].cast_value <= self.end


OP_CLASS = {
    'NOT': OpNot,
    'AND': OpAnd,
    'OR': OpOr,
    'IN': OpIn,
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
    'size': FuncSize,
    'between': FuncBetween
}
