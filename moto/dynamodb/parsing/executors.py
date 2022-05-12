from abc import abstractmethod

from moto.dynamodb.exceptions import (
    IncorrectOperandType,
    IncorrectDataType,
    ProvidedKeyDoesNotExist,
)
from moto.dynamodb.models import DynamoType
from moto.dynamodb.models.dynamo_type import DDBTypeConversion, DDBType
from moto.dynamodb.parsing.ast_nodes import (
    UpdateExpressionSetAction,
    UpdateExpressionDeleteAction,
    UpdateExpressionRemoveAction,
    UpdateExpressionAddAction,
    UpdateExpressionPath,
    DDBTypedValue,
    ExpressionAttribute,
    ExpressionSelector,
    ExpressionAttributeName,
)
from moto.dynamodb.parsing.validators import ExpressionPathResolver


class NodeExecutor(object):
    def __init__(self, ast_node, expression_attribute_names):
        self.node = ast_node
        self.expression_attribute_names = expression_attribute_names

    @abstractmethod
    def execute(self, item):
        pass

    def get_item_part_for_path_nodes(self, item, path_nodes):
        """
        For a list of path nodes travers the item by following the path_nodes
        Args:
            item(Item):
            path_nodes(list):

        Returns:

        """
        if len(path_nodes) == 0:
            return item.attrs
        else:
            return ExpressionPathResolver(
                self.expression_attribute_names
            ).resolve_expression_path_nodes_to_dynamo_type(item, path_nodes)

    def get_item_before_end_of_path(self, item):
        """
        Get the part ot the item where the item will perform the action. For most actions this should be the parent. As
        that element will need to be modified by the action.
        Args:
            item(Item):

        Returns:
            DynamoType or dict: The path to be set
        """
        return self.get_item_part_for_path_nodes(
            item, self.get_path_expression_nodes()[:-1]
        )

    def get_item_at_end_of_path(self, item):
        """
        For a DELETE the path points at the stringset so we need to evaluate the full path.
        Args:
            item(Item):

        Returns:
            DynamoType or dict: The path to be set
        """
        return self.get_item_part_for_path_nodes(item, self.get_path_expression_nodes())

    # Get the part ot the item where the item will perform the action. For most actions this should be the parent. As
    # that element will need to be modified by the action.
    get_item_part_in_which_to_perform_action = get_item_before_end_of_path

    def get_path_expression_nodes(self):
        update_expression_path = self.node.children[0]
        assert isinstance(update_expression_path, UpdateExpressionPath)
        return update_expression_path.children

    def get_element_to_action(self):
        return self.get_path_expression_nodes()[-1]

    def get_action_value(self):
        """

        Returns:
            DynamoType: The value to be set
        """
        ddb_typed_value = self.node.children[1]
        assert isinstance(ddb_typed_value, DDBTypedValue)
        dynamo_type_value = ddb_typed_value.children[0]
        assert isinstance(dynamo_type_value, DynamoType)
        return dynamo_type_value


class SetExecutor(NodeExecutor):
    def execute(self, item):
        self.set(
            item_part_to_modify_with_set=self.get_item_part_in_which_to_perform_action(
                item
            ),
            element_to_set=self.get_element_to_action(),
            value_to_set=self.get_action_value(),
            expression_attribute_names=self.expression_attribute_names,
        )

    @classmethod
    def set(
        cls,
        item_part_to_modify_with_set,
        element_to_set,
        value_to_set,
        expression_attribute_names,
    ):
        if isinstance(element_to_set, ExpressionAttribute):
            attribute_name = element_to_set.get_attribute_name()
            item_part_to_modify_with_set[attribute_name] = value_to_set
        elif isinstance(element_to_set, ExpressionSelector):
            index = element_to_set.get_index()
            item_part_to_modify_with_set[index] = value_to_set
        elif isinstance(element_to_set, ExpressionAttributeName):
            attribute_name = expression_attribute_names[
                element_to_set.get_attribute_name_placeholder()
            ]
            item_part_to_modify_with_set[attribute_name] = value_to_set
        else:
            raise NotImplementedError(
                "Moto does not support setting {t} yet".format(t=type(element_to_set))
            )


class DeleteExecutor(NodeExecutor):
    operator = "operator: DELETE"

    def execute(self, item):
        string_set_to_remove = self.get_action_value()
        assert isinstance(string_set_to_remove, DynamoType)
        if not string_set_to_remove.is_set():
            raise IncorrectOperandType(
                self.operator,
                DDBTypeConversion.get_human_type(string_set_to_remove.type),
            )

        string_set = self.get_item_at_end_of_path(item)
        assert isinstance(string_set, DynamoType)
        if string_set.type != string_set_to_remove.type:
            raise IncorrectDataType()
        # String set is currently implemented as a list
        string_set_list = string_set.value

        stringset_to_remove_list = string_set_to_remove.value

        for value in stringset_to_remove_list:
            try:
                string_set_list.remove(value)
            except (KeyError, ValueError):
                # DynamoDB does not mind if value is not present
                pass

        # DynamoDB does not support empty sets.  If we've deleted
        # the last item in the set, we have to remove the attribute.
        if not string_set_list:
            element = self.get_element_to_action()
            if isinstance(element, ExpressionAttributeName):
                attribute_name = self.expression_attribute_names[
                    element.get_attribute_name_placeholder()
                ]
            elif isinstance(element, ExpressionAttribute):
                attribute_name = element.get_attribute_name()
            else:
                raise NotImplementedError(
                    "Moto does not support deleting {t} yet".format(t=type(element))
                )
            container = self.get_item_before_end_of_path(item)
            del container[attribute_name]


class RemoveExecutor(NodeExecutor):
    def execute(self, item):
        element_to_remove = self.get_element_to_action()
        if isinstance(element_to_remove, ExpressionAttribute):
            attribute_name = element_to_remove.get_attribute_name()
            self.get_item_part_in_which_to_perform_action(item).pop(
                attribute_name, None
            )
        elif isinstance(element_to_remove, ExpressionAttributeName):
            attribute_name = self.expression_attribute_names[
                element_to_remove.get_attribute_name_placeholder()
            ]
            self.get_item_part_in_which_to_perform_action(item).pop(
                attribute_name, None
            )
        elif isinstance(element_to_remove, ExpressionSelector):
            index = element_to_remove.get_index()
            try:
                self.get_item_part_in_which_to_perform_action(item).pop(index)
            except IndexError:
                # DynamoDB does not care that index is out of bounds, it will just do nothing.
                pass
        else:
            raise NotImplementedError(
                "Moto does not support setting {t} yet".format(
                    t=type(element_to_remove)
                )
            )


class AddExecutor(NodeExecutor):
    def execute(self, item):
        value_to_add = self.get_action_value()
        if isinstance(value_to_add, DynamoType):
            if value_to_add.is_set():
                try:
                    current_string_set = self.get_item_at_end_of_path(item)
                except ProvidedKeyDoesNotExist:
                    current_string_set = DynamoType({value_to_add.type: []})
                    SetExecutor.set(
                        item_part_to_modify_with_set=self.get_item_before_end_of_path(
                            item
                        ),
                        element_to_set=self.get_element_to_action(),
                        value_to_set=current_string_set,
                        expression_attribute_names=self.expression_attribute_names,
                    )
                assert isinstance(current_string_set, DynamoType)
                if not current_string_set.type == value_to_add.type:
                    raise IncorrectDataType()
                # Sets are implemented as list
                for value in value_to_add.value:
                    if value in current_string_set.value:
                        continue
                    else:
                        current_string_set.value.append(value)
            elif value_to_add.type == DDBType.NUMBER:
                try:
                    existing_value = self.get_item_at_end_of_path(item)
                except ProvidedKeyDoesNotExist:
                    existing_value = DynamoType({DDBType.NUMBER: "0"})

                assert isinstance(existing_value, DynamoType)
                if not existing_value.type == DDBType.NUMBER:
                    raise IncorrectDataType()
                new_value = existing_value + value_to_add
                SetExecutor.set(
                    item_part_to_modify_with_set=self.get_item_before_end_of_path(item),
                    element_to_set=self.get_element_to_action(),
                    value_to_set=new_value,
                    expression_attribute_names=self.expression_attribute_names,
                )
            else:
                raise IncorrectDataType()


class UpdateExpressionExecutor(object):
    execution_map = {
        UpdateExpressionSetAction: SetExecutor,
        UpdateExpressionAddAction: AddExecutor,
        UpdateExpressionRemoveAction: RemoveExecutor,
        UpdateExpressionDeleteAction: DeleteExecutor,
    }

    def __init__(self, update_ast, item, expression_attribute_names):
        self.update_ast = update_ast
        self.item = item
        self.expression_attribute_names = expression_attribute_names

    def execute(self, node=None):
        """
        As explained in moto.dynamodb2.parsing.expressions.NestableExpressionParserMixin._create_node the order of nodes
        in the AST can be translated of the order of statements in the expression. As such we can start at the root node
        and process the nodes 1-by-1. If no specific execution for the node type is defined we can execute the children
        in order since it will be a container node that is expandable and left child will be first in the statement.

        Args:
            node(Node):

        Returns:
            None
        """
        if node is None:
            node = self.update_ast

        node_executor = self.get_specific_execution(node)
        if node_executor is None:
            for node in node.children:
                self.execute(node)
        else:
            node_executor(node, self.expression_attribute_names).execute(self.item)

    def get_specific_execution(self, node):
        for node_class in self.execution_map:
            if isinstance(node, node_class):
                return self.execution_map[node_class]
        return None
