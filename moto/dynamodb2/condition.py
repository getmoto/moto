import re
import json
import enum
from collections import deque
from collections import namedtuple


class Kind(enum.Enum):
    """Defines types of nodes in the syntax tree."""

    # Condition nodes
    # ---------------
    OR = enum.auto()
    AND = enum.auto()
    NOT = enum.auto()
    PARENTHESES = enum.auto()
    FUNCTION = enum.auto()
    BETWEEN = enum.auto()
    IN = enum.auto()
    COMPARISON = enum.auto()

    # Operand nodes
    # -------------
    EXPRESSION_ATTRIBUTE_VALUE = enum.auto()
    PATH = enum.auto()

    # Literal nodes
    # --------------
    LITERAL = enum.auto()


class Nonterminal(enum.Enum):
    """Defines nonterminals for defining productions."""
    CONDITION = enum.auto()
    OPERAND = enum.auto()
    COMPARATOR = enum.auto()
    FUNCTION_NAME = enum.auto()
    IDENTIFIER = enum.auto()
    AND = enum.auto()
    OR = enum.auto()
    NOT = enum.auto()
    BETWEEN = enum.auto()
    IN = enum.auto()
    COMMA = enum.auto()
    LEFT_PAREN = enum.auto()
    RIGHT_PAREN = enum.auto()
    WHITESPACE = enum.auto()


Node = namedtuple('Node', ['nonterminal', 'kind', 'text', 'value', 'children'])


class ConditionExpressionParser:
    def __init__(self, condition_expression, expression_attribute_names,
                 expression_attribute_values):
        self.condition_expression = condition_expression
        self.expression_attribute_names = expression_attribute_names
        self.expression_attribute_values = expression_attribute_values

    def parse(self):
        """Returns a syntax tree for the expression.

        The tree, and all of the nodes in the tree are a tuple of
        - kind: str
        - children/value:
            list of nodes for parent nodes
            value for leaf nodes

        Raises AssertionError if the condition expression is invalid
        Raises KeyError if expression attribute names/values are invalid

        Here are the types of nodes that can be returned.
        The types of child nodes are denoted with a colon (:).
        An arbitrary number of children is denoted with ...

        Condition:
            ('OR', [lhs : Condition, rhs : Condition])
            ('AND', [lhs: Condition, rhs: Condition])
            ('NOT', [argument: Condition])
            ('PARENTHESES', [argument: Condition])
            ('FUNCTION', [('LITERAL', function_name: str), argument: Operand, ...])
            ('BETWEEN', [query: Operand, low: Operand, high: Operand])
            ('IN', [query: Operand, possible_value: Operand, ...])
            ('COMPARISON', [lhs: Operand, ('LITERAL', comparator: str), rhs: Operand])

        Operand:
            ('EXPRESSION_ATTRIBUTE_VALUE', value: dict, e.g. {'S': 'foobar'})
            ('PATH', [('LITERAL', path_element: str), ...])
            NOTE: Expression attribute names will be expanded

        Literal:
            ('LITERAL', value: str)

        """
        if not self.condition_expression:
            return None
        nodes = self._lex_condition_expression()
        nodes = self._parse_paths(nodes)
        self._print_debug(nodes)
        nodes = self._apply_comparator(nodes)
        self._print_debug(nodes)
        nodes = self._apply_in(nodes)
        self._print_debug(nodes)
        nodes = self._apply_between(nodes)
        self._print_debug(nodes)
        nodes = self._apply_functions(nodes)
        self._print_debug(nodes)
        nodes = self._apply_parens_and_booleans(nodes)
        self._print_debug(nodes)
        node = nodes[0]
        return self._make_node_tree(node)

    def _lex_condition_expression(self):
        nodes = deque()
        remaining_expression = self.condition_expression
        while remaining_expression:
            node, remaining_expression = \
                self._lex_one_node(remaining_expression)
            if node.nonterminal == Nonterminal.WHITESPACE:
                continue
            nodes.append(node)
        return nodes

    def _lex_one_node(self, remaining_expression):

        attribute_regex = '(:|#)?[A-z0-9\-_]+'
        patterns = [(
            Nonterminal.WHITESPACE, re.compile('^ +')
        ), (
            Nonterminal.COMPARATOR, re.compile(
                '^('
                '=|'
                '<>|'
                '<|'
                '<=|'
                '>|'
                '>=)'),
        ), (
            Nonterminal.OPERAND, re.compile(
                '^' +
                attribute_regex + '(\.' + attribute_regex + ')*')
        ), (
            Nonterminal.COMMA, re.compile('^,')
        ), (
            Nonterminal.LEFT_PAREN, re.compile('^\(')
        ), (
            Nonterminal.RIGHT_PAREN, re.compile('^\)')
        )]

        for nonterminal, pattern in patterns:
            match = pattern.match(remaining_expression)
            if match:
                match_text = match.group()
                break
        else:
            raise AssertionError("Cannot parse condition starting at: " +
                                 remaining_expression)

        value = match_text
        node = Node(
            nonterminal=nonterminal,
            kind=Kind.LITERAL,
            text=match_text,
            value=match_text,
            children=[])

        remaining_expression = remaining_expression[len(match_text):]

        return node, remaining_expression

    def _parse_paths(self, nodes):
        output = deque()

        while nodes:
            node = nodes.popleft()

            if node.nonterminal == Nonterminal.OPERAND:
                path = node.value.split('.')
                children = [
                    self._parse_path_element(name)
                    for name in path]
                if len(children) == 1:
                    child = children[0]
                    if child.nonterminal != Nonterminal.IDENTIFIER:
                        output.append(child)
                        continue
                else:
                    for child in children:
                        self._assert(
                            child.nonterminal == Nonterminal.IDENTIFIER,
                            "Cannot use %s in path" % child.text, [node])
                output.append(Node(
                    nonterminal=Nonterminal.OPERAND,
                    kind=Kind.PATH,
                    text=node.text,
                    value=None,
                    children=children))
            else:
                output.append(node)
        return output

    def _parse_path_element(self, name):
        reserved = {
            'AND': Nonterminal.AND,
            'OR': Nonterminal.OR,
            'IN': Nonterminal.IN,
            'BETWEEN': Nonterminal.BETWEEN,
            'NOT': Nonterminal.NOT,
        }

        functions = {
            'attribute_exists',
            'attribute_not_exists',
            'attribute_type',
            'begins_with',
            'contains',
            'size',
        }


        if name in reserved:
            nonterminal = reserved[name]
            return Node(
                nonterminal=nonterminal,
                kind=Kind.LITERAL,
                text=name,
                value=name,
                children=[])
        elif name in functions:
            return Node(
                nonterminal=Nonterminal.FUNCTION_NAME,
                kind=Kind.LITERAL,
                text=name,
                value=name,
                children=[])
        elif name.startswith(':'):
            return Node(
                nonterminal=Nonterminal.OPERAND,
                kind=Kind.EXPRESSION_ATTRIBUTE_VALUE,
                text=name,
                value=self._lookup_expression_attribute_value(name),
                children=[])
        elif name.startswith('#'):
            return Node(
                nonterminal=Nonterminal.IDENTIFIER,
                kind=Kind.LITERAL,
                text=name,
                value=self._lookup_expression_attribute_name(name),
                children=[])
        else:
            return Node(
                nonterminal=Nonterminal.IDENTIFIER,
                kind=Kind.LITERAL,
                text=name,
                value=name,
                children=[])

    def _lookup_expression_attribute_value(self, name):
        return self.expression_attribute_values[name]

    def _lookup_expression_attribute_name(self, name):
        return self.expression_attribute_names[name]

    # NOTE: The following constructions are ordered from high precedence to low precedence
    # according to
    # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.OperatorsAndFunctions.html#Expressions.OperatorsAndFunctions.Precedence
    #
    # = <> < <= > >=
    # IN
    # BETWEEN
    # attribute_exists attribute_not_exists begins_with contains
    # Parentheses
    # NOT
    # AND
    # OR
    #
    # The grammar is taken from
    # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.OperatorsAndFunctions.html#Expressions.OperatorsAndFunctions.Syntax
    #
    # condition-expression ::=
    #     operand comparator operand
    #     operand BETWEEN operand AND operand
    #     operand IN ( operand (',' operand (, ...) ))
    #     function
    #     condition AND condition
    #     condition OR condition
    #     NOT condition
    #     ( condition )
    #
    # comparator ::=
    #     =
    #     <>
    #     <
    #     <=
    #     >
    #     >=
    #
    # function ::=
    #     attribute_exists (path)
    #     attribute_not_exists (path)
    #     attribute_type (path, type)
    #     begins_with (path, substr)
    #     contains (path, operand)
    #     size (path)

    def _matches(self, nodes, production):
        """Check if the nodes start with the given production.

        Parameters
        ----------
        nodes: list of Node
        production: list of str
            The name of a Nonterminal, or '*' for anything

        """
        if len(nodes) < len(production):
            return False
        for i in range(len(production)):
            if production[i] == '*':
                continue
            expected = getattr(Nonterminal, production[i])
            if nodes[i].nonterminal != expected:
                return False
        return True

    def _apply_comparator(self, nodes):
        """Apply condition := operand comparator operand."""
        output = deque()

        while nodes:
            if self._matches(nodes, ['*', 'COMPARATOR']):
                self._assert(
                    self._matches(nodes, ['OPERAND', 'COMPARATOR', 'OPERAND']),
                    "Bad comparison", list(nodes)[:3])
                lhs = nodes.popleft()
                comparator = nodes.popleft()
                rhs = nodes.popleft()
                output.append(Node(
                    nonterminal=Nonterminal.CONDITION,
                    kind=Kind.COMPARISON,
                    text=" ".join([
                        lhs.text,
                        comparator.text,
                        rhs.text]),
                    value=None,
                    children=[lhs, comparator, rhs]))
            else:
                output.append(nodes.popleft())
        return output

    def _apply_in(self, nodes):
        """Apply condition := operand IN ( operand , ... )."""
        output = deque()
        while nodes:
            if self._matches(nodes, ['*', 'IN']):
                self._assert(
                    self._matches(nodes, ['OPERAND', 'IN', 'LEFT_PAREN']),
                    "Bad IN expression", list(nodes)[:3])
                lhs = nodes.popleft()
                in_node = nodes.popleft()
                left_paren = nodes.popleft()
                all_children = [lhs, in_node, left_paren]
                rhs = []
                while True:
                    if self._matches(nodes, ['OPERAND', 'COMMA']):
                        operand = nodes.popleft()
                        separator = nodes.popleft()
                        all_children += [operand, separator]
                        rhs.append(operand)
                    elif self._matches(nodes, ['OPERAND', 'RIGHT_PAREN']):
                        operand = nodes.popleft()
                        separator = nodes.popleft()
                        all_children += [operand, separator]
                        rhs.append(operand)
                        break  # Close
                    else:
                        self._assert(
                            False,
                            "Bad IN expression starting at", nodes)
                output.append(Node(
                    nonterminal=Nonterminal.CONDITION,
                    kind=Kind.IN,
                    text=" ".join([t.text for t in all_children]),
                    value=None,
                    children=[lhs] + rhs))
            else:
                output.append(nodes.popleft())
        return output

    def _apply_between(self, nodes):
        """Apply condition := operand BETWEEN operand AND operand."""
        output = deque()
        while nodes:
            if self._matches(nodes, ['*', 'BETWEEN']):
                self._assert(
                    self._matches(nodes, ['OPERAND', 'BETWEEN', 'OPERAND',
                                          'AND', 'OPERAND']),
                    "Bad BETWEEN expression", list(nodes)[:5])
                lhs = nodes.popleft()
                between_node = nodes.popleft()
                low = nodes.popleft()
                and_node = nodes.popleft()
                high = nodes.popleft()
                all_children = [lhs, between_node, low, and_node, high]
                output.append(Node(
                    nonterminal=Nonterminal.CONDITION,
                    kind=Kind.BETWEEN,
                    text=" ".join([t.text for t in all_children]),
                    value=None,
                    children=[lhs, low, high]))
            else:
                output.append(nodes.popleft())
        return output

    def _apply_functions(self, nodes):
        """Apply condition := function_name (operand , ...)."""
        output = deque()
        expected_argument_kind_map = {
            'attribute_exists': [{Kind.PATH}],
            'attribute_not_exists': [{Kind.PATH}],
            'attribute_type': [{Kind.PATH}, {Kind.EXPRESSION_ATTRIBUTE_VALUE}],
            'begins_with': [{Kind.PATH}, {Kind.EXPRESSION_ATTRIBUTE_VALUE}],
            'contains': [{Kind.PATH}, {Kind.PATH, Kind.EXPRESSION_ATTRIBUTE_VALUE}],
            'size': [{Kind.PATH}],
        }
        while nodes:
            if self._matches(nodes, ['FUNCTION_NAME']):
                self._assert(
                    self._matches(nodes, ['FUNCTION_NAME', 'LEFT_PAREN',
                                          'OPERAND', '*']),
                    "Bad function expression at", list(nodes)[:4])
                function_name = nodes.popleft()
                left_paren = nodes.popleft()
                all_children = [function_name, left_paren]
                arguments = []
                while True:
                    if self._matches(nodes, ['OPERAND', 'COMMA']):
                        operand = nodes.popleft()
                        separator = nodes.popleft()
                        all_children += [operand, separator]
                        arguments.append(operand)
                    elif self._matches(nodes, ['OPERAND', 'RIGHT_PAREN']):
                        operand = nodes.popleft()
                        separator = nodes.popleft()
                        all_children += [operand, separator]
                        arguments.append(operand)
                        break  # Close paren
                    else:
                        self._assert(
                            False,
                            "Bad function expression", all_children + list(nodes)[:2])
                expected_kinds = expected_argument_kind_map[function_name.value]
                self._assert(
                    len(arguments) == len(expected_kinds),
                    "Wrong number of arguments in", all_children)
                for i in range(len(expected_kinds)):
                    self._assert(
                        arguments[i].kind in expected_kinds[i],
                        "Wrong type for argument %d in" % i, all_children)
                output.append(Node(
                    nonterminal=Nonterminal.CONDITION,
                    kind=Kind.FUNCTION,
                    text=" ".join([t.text for t in all_children]),
                    value=None,
                    children=[function_name] + arguments))
            else:
                output.append(nodes.popleft())
        return output

    def _apply_parens_and_booleans(self, nodes, left_paren=None):
        """Apply condition := ( condition ) and booleans."""
        output = deque()
        while nodes:
            if self._matches(nodes, ['LEFT_PAREN']):
                parsed = self._apply_parens_and_booleans(nodes, left_paren=nodes.popleft())
                self._assert(
                    len(parsed) >= 1,
                    "Failed to close parentheses at", nodes)
                parens = parsed.popleft()
                self._assert(
                    parens.kind == Kind.PARENTHESES,
                    "Failed to close parentheses at", nodes)
                output.append(parens)
                nodes = parsed
            elif self._matches(nodes, ['RIGHT_PAREN']):
                self._assert(
                    left_paren is not None,
                    "Unmatched ) at", nodes)
                close_paren = nodes.popleft()
                children = self._apply_booleans(output)
                all_children = [left_paren, *children, close_paren]
                return deque([
                    Node(
                        nonterminal=Nonterminal.CONDITION,
                        kind=Kind.PARENTHESES,
                        text=" ".join([t.text for t in all_children]),
                        value=None,
                        children=list(children),
                    ), *nodes])
            else:
                output.append(nodes.popleft())

        self._assert(
            left_paren is None,
            "Unmatched ( at", list(output))
        return self._apply_booleans(output)

    def _apply_booleans(self, nodes):
        """Apply and, or, and not constructions."""
        nodes = self._apply_not(nodes)
        nodes = self._apply_and(nodes)
        nodes = self._apply_or(nodes)
        # The expression should reduce to a single condition
        self._assert(
            len(nodes) == 1,
            "Unexpected expression at", list(nodes)[1:])
        self._assert(
            nodes[0].nonterminal == Nonterminal.CONDITION,
            "Incomplete condition", nodes)
        return nodes

    def _apply_not(self, nodes):
        """Apply condition := NOT condition."""
        output = deque()
        while nodes:
            if self._matches(nodes, ['NOT']):
                self._assert(
                    self._matches(nodes, ['NOT', 'CONDITION']),
                    "Bad NOT expression", list(nodes)[:2])
                not_node = nodes.popleft()
                child = nodes.popleft()
                output.append(Node(
                    nonterminal=Nonterminal.CONDITION,
                    kind=Kind.NOT,
                    text=" ".join([not_node['text'], value['text']]),
                    value=None,
                    children=[child]))
            else:
                output.append(nodes.popleft())

        return output

    def _apply_and(self, nodes):
        """Apply condition := condition AND condition."""
        output = deque()
        while nodes:
            if self._matches(nodes, ['*', 'AND']):
                self._assert(
                    self._matches(nodes, ['CONDITION', 'AND', 'CONDITION']),
                    "Bad AND expression", list(nodes)[:3])
                lhs = nodes.popleft()
                and_node = nodes.popleft()
                rhs = nodes.popleft()
                all_children = [lhs, and_node, rhs]
                output.append(Node(
                    nonterminal=Nonterminal.CONDITION,
                    kind=Kind.AND,
                    text=" ".join([t.text for t in all_children]),
                    value=None,
                    children=[lhs, rhs]))
            else:
                output.append(nodes.popleft())

        return output

    def _apply_or(self, nodes):
        """Apply condition := condition OR condition."""
        output = deque()
        while nodes:
            if self._matches(nodes, ['*', 'OR']):
                self._assert(
                    self._matches(nodes, ['CONDITION', 'OR', 'CONDITION']),
                    "Bad OR expression", list(nodes)[:3])
                lhs = nodes.popleft()
                or_node = nodes.popleft()
                rhs = nodes.popleft()
                all_children = [lhs, or_node, rhs]
                output.append(Node(
                    nonterminal=Nonterminal.CONDITION,
                    kind=Kind.OR,
                    text=" ".join([t.text for t in all_children]),
                    value=None,
                    children=[lhs, rhs]))
            else:
                output.append(nodes.popleft())

        return output

    def _make_node_tree(self, node):
        if len(node.children) > 0:
            return (
                node.kind.name,
                [
                    self._make_node_tree(child)
                    for child in node.children
                ])
        else:
            return (node.kind.name, node.value)

    def _print_debug(self, nodes):
        print('ROOT')
        for node in nodes:
            self._print_node_recursive(node, depth=1)

    def _print_node_recursive(self, node, depth=0):
        if len(node.children) > 0:
            print('  ' * depth, node.nonterminal, node.kind)
            for child in node.children:
                self._print_node_recursive(child, depth=depth + 1)
        else:
            print('  ' * depth, node.nonterminal, node.kind, node.value)



    def _assert(self, condition, message, nodes):
        if not condition:
            raise AssertionError(message + " " + " ".join([t.text for t in nodes]))
