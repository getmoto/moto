import abc
import six


@six.add_metaclass(abc.ABCMeta)
class Node:
    def __init__(self, children=None):
        self.type = self.__class__.__name__
        assert children is None or isinstance(children, list)
        self.children = children
        self.parent = None

        if isinstance(children, list):
            for child in children:
                if isinstance(child, Node):
                    child.set_parent(self)

    def set_parent(self, parent_node):
        self.parent = parent_node


class LeafNode(Node):
    """A LeafNode is a Node where none of the children are Nodes themselves."""

    def __init__(self, children=None):
        super(LeafNode, self).__init__(children)


@six.add_metaclass(abc.ABCMeta)
class Expression(Node):
    """
    Abstract Syntax Tree representing the expression

    For the Grammar start here and jump down into the classes at the righ-hand side to look further. Nodes marked with
    a star are abstract and won't appear in the final AST.

    Expression* => UpdateExpression
    Expression* => ConditionExpression
    """


class UpdateExpression(Expression):
    """
    UpdateExpression => UpdateExpressionClause*
    UpdateExpression => UpdateExpressionClause* UpdateExpression
    """


@six.add_metaclass(abc.ABCMeta)
class UpdateExpressionClause(UpdateExpression):
    """
    UpdateExpressionClause* => UpdateExpressionSetClause
    UpdateExpressionClause* => UpdateExpressionRemoveClause
    UpdateExpressionClause* => UpdateExpressionAddClause
    UpdateExpressionClause* => UpdateExpressionDeleteClause
    """


class UpdateExpressionSetClause(UpdateExpressionClause):
    """
    UpdateExpressionSetClause => SET SetActions
    """


class UpdateExpressionSetActions(UpdateExpressionClause):
    """
    UpdateExpressionSetClause => SET SetActions

    SetActions => SetAction
    SetActions => SetAction , SetActions

    """


class UpdateExpressionSetAction(UpdateExpressionClause):
    """
    SetAction => Path = Value
    """


class UpdateExpressionRemoveActions(UpdateExpressionClause):
    """
    UpdateExpressionSetClause => REMOVE RemoveActions

    RemoveActions => RemoveAction
    RemoveActions => RemoveAction , RemoveActions
    """


class UpdateExpressionRemoveAction(UpdateExpressionClause):
    """
    RemoveAction => Path
    """


class UpdateExpressionAddActions(UpdateExpressionClause):
    """
    UpdateExpressionAddClause => ADD RemoveActions

    AddActions => AddAction
    AddActions => AddAction , AddActions
    """


class UpdateExpressionAddAction(UpdateExpressionClause):
    """
    AddAction => Path Value
    """


class UpdateExpressionDeleteActions(UpdateExpressionClause):
    """
    UpdateExpressionDeleteClause => DELETE RemoveActions

    DeleteActions => DeleteAction
    DeleteActions => DeleteAction , DeleteActions
    """


class UpdateExpressionDeleteAction(UpdateExpressionClause):
    """
    DeleteAction => Path Value
    """


class UpdateExpressionPath(UpdateExpressionClause):
    pass


class UpdateExpressionValue(UpdateExpressionClause):
    """
    Value => Operand
    Value => Operand + Value
    Value => Operand - Value
    """


class UpdateExpressionGroupedValue(UpdateExpressionClause):
    """
    GroupedValue => ( Value )
    """


class UpdateExpressionRemoveClause(UpdateExpressionClause):
    """
    UpdateExpressionRemoveClause => REMOVE RemoveActions
    """


class UpdateExpressionAddClause(UpdateExpressionClause):
    """
    UpdateExpressionAddClause => ADD AddActions
    """


class UpdateExpressionDeleteClause(UpdateExpressionClause):
    """
    UpdateExpressionDeleteClause => DELETE DeleteActions
    """


class ExpressionPathDescender(Node):
    """Node identifying descender into nested structure (.) in expression"""


class ExpressionSelector(LeafNode):
    """Node identifying selector [selection_index] in expresion"""

    def __init__(self, selection_index):
        super(ExpressionSelector, self).__init__(children=[selection_index])


class ExpressionAttribute(LeafNode):
    """An attribute identifier as used in the DDB item"""

    def __init__(self, attribute):
        super(ExpressionAttribute, self).__init__(children=[attribute])


class ExpressionAttributeName(LeafNode):
    """An ExpressionAttributeName is an alias for an attribute identifier"""

    def __init__(self, attribute_name):
        super(ExpressionAttributeName, self).__init__(children=[attribute_name])


class ExpressionAttributeValue(LeafNode):
    """An ExpressionAttributeValue is an alias for an value"""

    def __init__(self, value):
        super(ExpressionAttributeValue, self).__init__(children=[value])


class ExpressionValueOperator(LeafNode):
    """An ExpressionValueOperator is an operation that works on 2 values"""

    def __init__(self, value):
        super(ExpressionValueOperator, self).__init__(children=[value])


class UpdateExpressionFunction(Node):
    """
    A Node representing a function of an Update Expression. The first child is the function name the others are the
    arguments.
    """
