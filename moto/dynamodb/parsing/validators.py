"""
See docstring class Validator below for more details on validation
"""
from abc import abstractmethod
from copy import deepcopy

from moto.dynamodb.exceptions import (
    AttributeIsReservedKeyword,
    ExpressionAttributeValueNotDefined,
    AttributeDoesNotExist,
    ExpressionAttributeNameNotDefined,
    IncorrectOperandType,
    InvalidUpdateExpressionInvalidDocumentPath,
    ProvidedKeyDoesNotExist,
    EmptyKeyAttributeException,
    UpdateHashRangeKeyException,
)
from moto.dynamodb.models import DynamoType
from moto.dynamodb.parsing.ast_nodes import (
    ExpressionAttribute,
    UpdateExpressionPath,
    UpdateExpressionSetAction,
    UpdateExpressionAddAction,
    UpdateExpressionDeleteAction,
    UpdateExpressionRemoveAction,
    DDBTypedValue,
    ExpressionAttributeValue,
    ExpressionAttributeName,
    DepthFirstTraverser,
    NoneExistingPath,
    UpdateExpressionFunction,
    ExpressionPathDescender,
    UpdateExpressionValue,
    ExpressionValueOperator,
    ExpressionSelector,
)
from moto.dynamodb.parsing.reserved_keywords import ReservedKeywords


class ExpressionAttributeValueProcessor(DepthFirstTraverser):
    def __init__(self, expression_attribute_values):
        self.expression_attribute_values = expression_attribute_values

    def _processing_map(self):
        return {
            ExpressionAttributeValue: self.replace_expression_attribute_value_with_value
        }

    def replace_expression_attribute_value_with_value(self, node):
        """A node representing an Expression Attribute Value. Resolve and replace value"""
        assert isinstance(node, ExpressionAttributeValue)
        attribute_value_name = node.get_value_name()
        try:
            target = self.expression_attribute_values[attribute_value_name]
        except KeyError:
            raise ExpressionAttributeValueNotDefined(
                attribute_value=attribute_value_name
            )
        return DDBTypedValue(DynamoType(target))


class ExpressionPathResolver(object):
    def __init__(self, expression_attribute_names):
        self.expression_attribute_names = expression_attribute_names

    @classmethod
    def raise_exception_if_keyword(cls, attribute):
        if attribute.upper() in ReservedKeywords.get_reserved_keywords():
            raise AttributeIsReservedKeyword(attribute)

    def resolve_expression_path(self, item, update_expression_path):
        assert isinstance(update_expression_path, UpdateExpressionPath)
        return self.resolve_expression_path_nodes(item, update_expression_path.children)

    def resolve_expression_path_nodes(self, item, update_expression_path_nodes):
        target = item.attrs

        for child in update_expression_path_nodes:
            # First replace placeholder with attribute_name
            attr_name = None
            if isinstance(child, ExpressionAttributeName):
                attr_placeholder = child.get_attribute_name_placeholder()
                try:
                    attr_name = self.expression_attribute_names[attr_placeholder]
                except KeyError:
                    raise ExpressionAttributeNameNotDefined(attr_placeholder)
            elif isinstance(child, ExpressionAttribute):
                attr_name = child.get_attribute_name()
                self.raise_exception_if_keyword(attr_name)
            if attr_name is not None:
                # Resolv attribute_name
                try:
                    target = target[attr_name]
                except (KeyError, TypeError):
                    if child == update_expression_path_nodes[-1]:
                        return NoneExistingPath(creatable=True)
                    return NoneExistingPath()
            else:
                if isinstance(child, ExpressionPathDescender):
                    continue
                elif isinstance(child, ExpressionSelector):
                    index = child.get_index()
                    if target.is_list():
                        try:
                            target = target[index]
                        except IndexError:
                            # When a list goes out of bounds when assigning that is no problem when at the assignment
                            # side. It will just append to the list.
                            if child == update_expression_path_nodes[-1]:
                                return NoneExistingPath(creatable=True)
                            return NoneExistingPath()
                    else:
                        raise InvalidUpdateExpressionInvalidDocumentPath
                else:
                    raise NotImplementedError(
                        "Path resolution for {t}".format(t=type(child))
                    )
        return DDBTypedValue(target)

    def resolve_expression_path_nodes_to_dynamo_type(
        self, item, update_expression_path_nodes
    ):
        node = self.resolve_expression_path_nodes(item, update_expression_path_nodes)
        if isinstance(node, NoneExistingPath):
            raise ProvidedKeyDoesNotExist()
        assert isinstance(node, DDBTypedValue)
        return node.get_value()


class ExpressionAttributeResolvingProcessor(DepthFirstTraverser):
    def _processing_map(self):
        return {
            UpdateExpressionSetAction: self.disable_resolving,
            UpdateExpressionPath: self.process_expression_path_node,
        }

    def __init__(self, expression_attribute_names, item):
        self.expression_attribute_names = expression_attribute_names
        self.item = item
        self.resolving = False

    def pre_processing_of_child(self, parent_node, child_id):
        """
        We have to enable resolving if we are processing a child of UpdateExpressionSetAction that is not first.
        Because first argument is path to be set, 2nd argument would be the value.
        """
        if isinstance(
            parent_node,
            (
                UpdateExpressionSetAction,
                UpdateExpressionRemoveAction,
                UpdateExpressionDeleteAction,
                UpdateExpressionAddAction,
            ),
        ):
            if child_id == 0:
                self.resolving = False
            else:
                self.resolving = True

    def disable_resolving(self, node=None):
        self.resolving = False
        return node

    def process_expression_path_node(self, node):
        """Resolve ExpressionAttribute if not part of a path and resolving is enabled."""
        if self.resolving:
            return self.resolve_expression_path(node)
        else:
            # Still resolve but return original note to make sure path is correct Just make sure nodes are creatable.
            result_node = self.resolve_expression_path(node)
            if (
                isinstance(result_node, NoneExistingPath)
                and not result_node.is_creatable()
            ):
                raise InvalidUpdateExpressionInvalidDocumentPath()

            return node

    def resolve_expression_path(self, node):
        return ExpressionPathResolver(
            self.expression_attribute_names
        ).resolve_expression_path(self.item, node)


class UpdateExpressionFunctionEvaluator(DepthFirstTraverser):
    """
    At time of writing there are only 2 functions for DDB UpdateExpressions. They both are specific to the SET
    expression as per the official AWS docs:
        https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/
        Expressions.UpdateExpressions.html#Expressions.UpdateExpressions.SET
    """

    def _processing_map(self):
        return {UpdateExpressionFunction: self.process_function}

    def process_function(self, node):
        assert isinstance(node, UpdateExpressionFunction)
        function_name = node.get_function_name()
        first_arg = node.get_nth_argument(1)
        second_arg = node.get_nth_argument(2)

        if function_name == "if_not_exists":
            if isinstance(first_arg, NoneExistingPath):
                result = second_arg
            else:
                result = first_arg
            assert isinstance(result, (DDBTypedValue, NoneExistingPath))
            return result
        elif function_name == "list_append":
            first_arg = deepcopy(
                self.get_list_from_ddb_typed_value(first_arg, function_name)
            )
            second_arg = self.get_list_from_ddb_typed_value(second_arg, function_name)
            for list_element in second_arg.value:
                first_arg.value.append(list_element)
            return DDBTypedValue(first_arg)
        else:
            raise NotImplementedError(
                "Unsupported function for moto {name}".format(name=function_name)
            )

    @classmethod
    def get_list_from_ddb_typed_value(cls, node, function_name):
        assert isinstance(node, DDBTypedValue)
        dynamo_value = node.get_value()
        assert isinstance(dynamo_value, DynamoType)
        if not dynamo_value.is_list():
            raise IncorrectOperandType(function_name, dynamo_value.type)
        return dynamo_value


class NoneExistingPathChecker(DepthFirstTraverser):
    """
    Pass through the AST and make sure there are no none-existing paths.
    """

    def _processing_map(self):
        return {NoneExistingPath: self.raise_none_existing_path}

    def raise_none_existing_path(self, node):
        raise AttributeDoesNotExist


class ExecuteOperations(DepthFirstTraverser):
    def _processing_map(self):
        return {UpdateExpressionValue: self.process_update_expression_value}

    def process_update_expression_value(self, node):
        """
        If an UpdateExpressionValue only has a single child the node will be replaced with the childe.
        Otherwise it has 3 children and the middle one is an ExpressionValueOperator which details how to combine them
        Args:
            node(Node):

        Returns:
            Node: The resulting node of the operation if present or the child.
        """
        assert isinstance(node, UpdateExpressionValue)
        if len(node.children) == 1:
            return node.children[0]
        elif len(node.children) == 3:
            operator_node = node.children[1]
            assert isinstance(operator_node, ExpressionValueOperator)
            operator = operator_node.get_operator()
            left_operand = self.get_dynamo_value_from_ddb_typed_value(node.children[0])
            right_operand = self.get_dynamo_value_from_ddb_typed_value(node.children[2])
            if operator == "+":
                return self.get_sum(left_operand, right_operand)
            elif operator == "-":
                return self.get_subtraction(left_operand, right_operand)
            else:
                raise NotImplementedError(
                    "Moto does not support operator {operator}".format(
                        operator=operator
                    )
                )
        else:
            raise NotImplementedError(
                "UpdateExpressionValue only has implementations for 1 or 3 children."
            )

    @classmethod
    def get_dynamo_value_from_ddb_typed_value(cls, node):
        assert isinstance(node, DDBTypedValue)
        dynamo_value = node.get_value()
        assert isinstance(dynamo_value, DynamoType)
        return dynamo_value

    @classmethod
    def get_sum(cls, left_operand, right_operand):
        """
        Args:
            left_operand(DynamoType):
            right_operand(DynamoType):

        Returns:
            DDBTypedValue:
        """
        try:
            return DDBTypedValue(left_operand + right_operand)
        except TypeError:
            raise IncorrectOperandType("+", left_operand.type)

    @classmethod
    def get_subtraction(cls, left_operand, right_operand):
        """
        Args:
            left_operand(DynamoType):
            right_operand(DynamoType):

        Returns:
            DDBTypedValue:
        """
        try:
            return DDBTypedValue(left_operand - right_operand)
        except TypeError:
            raise IncorrectOperandType("-", left_operand.type)


class EmptyStringKeyValueValidator(DepthFirstTraverser):
    def __init__(self, key_attributes):
        self.key_attributes = key_attributes

    def _processing_map(self):
        return {UpdateExpressionSetAction: self.check_for_empty_string_key_value}

    def check_for_empty_string_key_value(self, node):
        """A node representing a SET action. Check that keys are not being assigned empty strings"""
        assert isinstance(node, UpdateExpressionSetAction)
        assert len(node.children) == 2
        key = node.children[0].children[0].children[0]
        val_node = node.children[1].children[0]
        if (
            not val_node.value
            and val_node.type in ["S", "B"]
            and key in self.key_attributes
        ):
            raise EmptyKeyAttributeException(key_in_index=True)
        return node


class UpdateHashRangeKeyValidator(DepthFirstTraverser):
    def __init__(self, table_key_attributes):
        self.table_key_attributes = table_key_attributes

    def _processing_map(self):
        return {UpdateExpressionPath: self.check_for_hash_or_range_key}

    def check_for_hash_or_range_key(self, node):
        """Check that hash and range keys are not updated"""
        key_to_update = node.children[0].children[0]
        if key_to_update in self.table_key_attributes:
            raise UpdateHashRangeKeyException(key_to_update)
        return node


class Validator(object):
    """
    A validator is used to validate expressions which are passed in as an AST.
    """

    def __init__(
        self,
        expression,
        expression_attribute_names,
        expression_attribute_values,
        item,
        table,
    ):
        """
        Besides validation the Validator should also replace referenced parts of an item which is cheapest upon
        validation.

        Args:
            expression(Node): The root node of the AST representing the expression to be validated
            expression_attribute_names(ExpressionAttributeNames):
            expression_attribute_values(ExpressionAttributeValues):
            item(Item): The item which will be updated (pointed to by Key of update_item)
        """
        self.expression_attribute_names = expression_attribute_names
        self.expression_attribute_values = expression_attribute_values
        self.item = item
        self.table = table
        self.processors = self.get_ast_processors()
        self.node_to_validate = deepcopy(expression)

    @abstractmethod
    def get_ast_processors(self):
        """Get the different processors that go through the AST tree and processes the nodes."""

    def validate(self):
        n = self.node_to_validate
        for processor in self.processors:
            n = processor.traverse(n)
        return n


class UpdateExpressionValidator(Validator):
    def get_ast_processors(self):
        """Get the different processors that go through the AST tree and processes the nodes."""
        processors = [
            UpdateHashRangeKeyValidator(self.table.table_key_attrs),
            ExpressionAttributeValueProcessor(self.expression_attribute_values),
            ExpressionAttributeResolvingProcessor(
                self.expression_attribute_names, self.item
            ),
            UpdateExpressionFunctionEvaluator(),
            NoneExistingPathChecker(),
            ExecuteOperations(),
            EmptyStringKeyValueValidator(self.table.attribute_keys),
        ]
        return processors
