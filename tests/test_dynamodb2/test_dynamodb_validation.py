import pytest

from moto.dynamodb2.exceptions import (
    AttributeIsReservedKeyword,
    ExpressionAttributeValueNotDefined,
    AttributeDoesNotExist,
    ExpressionAttributeNameNotDefined,
    IncorrectOperandType,
    InvalidUpdateExpressionInvalidDocumentPath,
    EmptyKeyAttributeException,
)
from moto.dynamodb2.models import Item, DynamoType
from moto.dynamodb2.parsing.ast_nodes import (
    NodeDepthLeftTypeFetcher,
    UpdateExpressionSetAction,
    DDBTypedValue,
)
from moto.dynamodb2.parsing.expressions import UpdateExpressionParser
from moto.dynamodb2.parsing.validators import UpdateExpressionValidator


def test_valid_update_expression(table):
    update_expression = "set forum_name=:NewName, forum_type=:NewType"
    update_expression_values = {
        ":NewName": {"S": "AmazingForum"},
        ":NewType": {"S": "BASIC"},
    }
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "forum_name"}),
        hash_key_type="TYPE",
        range_key=DynamoType({"S": "forum_type"}),
        range_key_type="TYPE",
        attrs={"forum_name": {"S": "hello"}},
    )
    UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=update_expression_values,
        item=item,
        table=table,
    ).validate()


def test_validation_of_empty_string_key_val(table):
    with pytest.raises(EmptyKeyAttributeException):
        update_expression = "set forum_name=:NewName"
        update_expression_values = {":NewName": {"S": ""}}
        update_expression_ast = UpdateExpressionParser.make(update_expression)
        item = Item(
            hash_key=DynamoType({"S": "forum_name"}),
            hash_key_type="TYPE",
            range_key=None,
            range_key_type=None,
            attrs={"forum_name": {"S": "hello"}},
        )
        UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values=update_expression_values,
            item=item,
            table=table,
        ).validate()


def test_validation_of_update_expression_with_keyword(table):
    try:
        update_expression = "SET myNum = path + :val"
        update_expression_values = {":val": {"N": "3"}}
        update_expression_ast = UpdateExpressionParser.make(update_expression)
        item = Item(
            hash_key=DynamoType({"S": "id"}),
            hash_key_type="TYPE",
            range_key=None,
            range_key_type=None,
            attrs={"id": {"S": "1"}, "path": {"N": "3"}},
        )
        UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values=update_expression_values,
            item=item,
            table=table,
        ).validate()
        assert False, "No exception raised"
    except AttributeIsReservedKeyword as e:
        assert e.keyword == "path"


@pytest.mark.parametrize(
    "update_expression", ["SET a = #b + :val2", "SET a = :val2 + #b",],
)
def test_validation_of_a_set_statement_with_incorrect_passed_value(
    update_expression, table
):
    """
    By running permutations it shows that values are replaced prior to resolving attributes.

    An error occurred (ValidationException) when calling the UpdateItem operation: Invalid UpdateExpression:
    An expression attribute value used in expression is not defined; attribute value: :val2
    """
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "b": {"N": "3"}},
    )
    try:
        UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names={"#b": "ok"},
            expression_attribute_values={":val": {"N": "3"}},
            item=item,
            table=table,
        ).validate()
    except ExpressionAttributeValueNotDefined as e:
        assert e.attribute_value == ":val2"


def test_validation_of_update_expression_with_attribute_that_does_not_exist_in_item(
    table,
):
    """
    When an update expression tries to get an attribute that does not exist it must throw the appropriate exception.

    An error occurred (ValidationException) when calling the UpdateItem operation:
    The provided expression refers to an attribute that does not exist in the item
    """
    try:
        update_expression = "SET a = nonexistent"
        update_expression_ast = UpdateExpressionParser.make(update_expression)
        item = Item(
            hash_key=DynamoType({"S": "id"}),
            hash_key_type="TYPE",
            range_key=None,
            range_key_type=None,
            attrs={"id": {"S": "1"}, "path": {"N": "3"}},
        )
        UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values=None,
            item=item,
            table=table,
        ).validate()
        assert False, "No exception raised"
    except AttributeDoesNotExist:
        assert True


@pytest.mark.parametrize(
    "update_expression", ["SET a = #c", "SET a = #c + #d",],
)
def test_validation_of_update_expression_with_attribute_name_that_is_not_defined(
    update_expression, table,
):
    """
    When an update expression tries to get an attribute name that is not provided it must throw an exception.

    An error occurred (ValidationException) when calling the UpdateItem operation: Invalid UpdateExpression:
    An expression attribute name used in the document path is not defined; attribute name: #c
    """
    try:
        update_expression_ast = UpdateExpressionParser.make(update_expression)
        item = Item(
            hash_key=DynamoType({"S": "id"}),
            hash_key_type="TYPE",
            range_key=None,
            range_key_type=None,
            attrs={"id": {"S": "1"}, "path": {"N": "3"}},
        )
        UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names={"#b": "ok"},
            expression_attribute_values=None,
            item=item,
            table=table,
        ).validate()
        assert False, "No exception raised"
    except ExpressionAttributeNameNotDefined as e:
        assert e.not_defined_attribute_name == "#c"


def test_validation_of_if_not_exists_not_existing_invalid_replace_value(table):
    try:
        update_expression = "SET a = if_not_exists(b, a.c)"
        update_expression_ast = UpdateExpressionParser.make(update_expression)
        item = Item(
            hash_key=DynamoType({"S": "id"}),
            hash_key_type="TYPE",
            range_key=None,
            range_key_type=None,
            attrs={"id": {"S": "1"}, "a": {"S": "A"}},
        )
        UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values=None,
            item=item,
            table=table,
        ).validate()
        assert False, "No exception raised"
    except AttributeDoesNotExist:
        assert True


def get_first_node_of_type(ast, node_type):
    return next(NodeDepthLeftTypeFetcher(node_type, ast))


def get_set_action_value(ast):
    """
    Helper that takes an AST and gets the first UpdateExpressionSetAction and retrieves the value of that action.
    This should only be called on validated expressions.
    Args:
        ast(Node):

    Returns:
        DynamoType: The DynamoType object representing the Dynamo value.
    """
    set_action = get_first_node_of_type(ast, UpdateExpressionSetAction)
    typed_value = set_action.children[1]
    assert isinstance(typed_value, DDBTypedValue)
    dynamo_value = typed_value.children[0]
    assert isinstance(dynamo_value, DynamoType)
    return dynamo_value


def test_validation_of_if_not_exists_not_existing_value(table):
    update_expression = "SET a = if_not_exists(b, a)"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "a": {"S": "A"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=None,
        item=item,
        table=table,
    ).validate()
    dynamo_value = get_set_action_value(validated_ast)
    assert dynamo_value == DynamoType({"S": "A"})


def test_validation_of_if_not_exists_with_existing_attribute_should_return_attribute(
    table,
):
    update_expression = "SET a = if_not_exists(b, a)"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "a": {"S": "A"}, "b": {"S": "B"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=None,
        item=item,
        table=table,
    ).validate()
    dynamo_value = get_set_action_value(validated_ast)
    assert dynamo_value == DynamoType({"S": "B"})


def test_validation_of_if_not_exists_with_existing_attribute_should_return_value(table):
    update_expression = "SET a = if_not_exists(b, :val)"
    update_expression_values = {":val": {"N": "4"}}
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "b": {"N": "3"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=update_expression_values,
        item=item,
        table=table,
    ).validate()
    dynamo_value = get_set_action_value(validated_ast)
    assert dynamo_value == DynamoType({"N": "3"})


def test_validation_of_if_not_exists_with_non_existing_attribute_should_return_value(
    table,
):
    update_expression = "SET a = if_not_exists(b, :val)"
    update_expression_values = {":val": {"N": "4"}}
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=update_expression_values,
        item=item,
        table=table,
    ).validate()
    dynamo_value = get_set_action_value(validated_ast)
    assert dynamo_value == DynamoType({"N": "4"})


def test_validation_of_sum_operation(table):
    update_expression = "SET a = a + b"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "a": {"N": "3"}, "b": {"N": "4"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=None,
        item=item,
        table=table,
    ).validate()
    dynamo_value = get_set_action_value(validated_ast)
    assert dynamo_value == DynamoType({"N": "7"})


def test_validation_homogeneous_list_append_function(table):
    update_expression = "SET ri = list_append(ri, :vals)"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "ri": {"L": [{"S": "i1"}, {"S": "i2"}]}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values={":vals": {"L": [{"S": "i3"}, {"S": "i4"}]}},
        item=item,
        table=table,
    ).validate()
    dynamo_value = get_set_action_value(validated_ast)
    assert dynamo_value == DynamoType(
        {"L": [{"S": "i1"}, {"S": "i2"}, {"S": "i3"}, {"S": "i4"}]}
    )


def test_validation_hetereogenous_list_append_function(table):
    update_expression = "SET ri = list_append(ri, :vals)"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "ri": {"L": [{"S": "i1"}, {"S": "i2"}]}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values={":vals": {"L": [{"N": "3"}]}},
        item=item,
        table=table,
    ).validate()
    dynamo_value = get_set_action_value(validated_ast)
    assert dynamo_value == DynamoType({"L": [{"S": "i1"}, {"S": "i2"}, {"N": "3"}]})


def test_validation_list_append_function_with_non_list_arg(table):
    """
    Must error out:
    Invalid UpdateExpression: Incorrect operand type for operator or function;
     operator or function: list_append, operand type: S'
    Returns:

    """
    try:
        update_expression = "SET ri = list_append(ri, :vals)"
        update_expression_ast = UpdateExpressionParser.make(update_expression)
        item = Item(
            hash_key=DynamoType({"S": "id"}),
            hash_key_type="TYPE",
            range_key=None,
            range_key_type=None,
            attrs={"id": {"S": "1"}, "ri": {"L": [{"S": "i1"}, {"S": "i2"}]}},
        )
        UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values={":vals": {"S": "N"}},
            item=item,
            table=table,
        ).validate()
    except IncorrectOperandType as e:
        assert e.operand_type == "S"
        assert e.operator_or_function == "list_append"


def test_sum_with_incompatible_types(table):
    """
    Must error out:
    Invalid UpdateExpression: Incorrect operand type for operator or function; operator or function: +, operand type: S'
    Returns:

    """
    try:
        update_expression = "SET ri = :val + :val2"
        update_expression_ast = UpdateExpressionParser.make(update_expression)
        item = Item(
            hash_key=DynamoType({"S": "id"}),
            hash_key_type="TYPE",
            range_key=None,
            range_key_type=None,
            attrs={"id": {"S": "1"}, "ri": {"L": [{"S": "i1"}, {"S": "i2"}]}},
        )
        UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values={":val": {"S": "N"}, ":val2": {"N": "3"}},
            item=item,
            table=table,
        ).validate()
    except IncorrectOperandType as e:
        assert e.operand_type == "S"
        assert e.operator_or_function == "+"


def test_validation_of_subraction_operation(table):
    update_expression = "SET ri = :val - :val2"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "a": {"N": "3"}, "b": {"N": "4"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values={":val": {"N": "1"}, ":val2": {"N": "3"}},
        item=item,
        table=table,
    ).validate()
    dynamo_value = get_set_action_value(validated_ast)
    assert dynamo_value == DynamoType({"N": "-2"})


def test_cannot_index_into_a_string(table):
    """
    Must error out:
    The document path provided in the update expression is invalid for update'
    """
    try:
        update_expression = "set itemstr[1]=:Item"
        update_expression_ast = UpdateExpressionParser.make(update_expression)
        item = Item(
            hash_key=DynamoType({"S": "id"}),
            hash_key_type="TYPE",
            range_key=None,
            range_key_type=None,
            attrs={"id": {"S": "foo2"}, "itemstr": {"S": "somestring"}},
        )
        UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values={":Item": {"S": "string_update"}},
            item=item,
            table=table,
        ).validate()
        assert False, "Must raise exception"
    except InvalidUpdateExpressionInvalidDocumentPath:
        assert True


def test_validation_set_path_does_not_need_to_be_resolvable_when_setting_a_new_attribute(
    table,
):
    """If this step just passes we are happy enough"""
    update_expression = "set d=a"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "foo2"}, "a": {"N": "3"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=None,
        item=item,
        table=table,
    ).validate()
    dynamo_value = get_set_action_value(validated_ast)
    assert dynamo_value == DynamoType({"N": "3"})


def test_validation_set_path_does_not_need_to_be_resolvable_but_must_be_creatable_when_setting_a_new_attribute(
    table,
):
    try:
        update_expression = "set d.e=a"
        update_expression_ast = UpdateExpressionParser.make(update_expression)
        item = Item(
            hash_key=DynamoType({"S": "id"}),
            hash_key_type="TYPE",
            range_key=None,
            range_key_type=None,
            attrs={"id": {"S": "foo2"}, "a": {"N": "3"}},
        )
        UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values=None,
            item=item,
            table=table,
        ).validate()
        assert False, "Must raise exception"
    except InvalidUpdateExpressionInvalidDocumentPath:
        assert True
