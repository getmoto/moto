import pytest

from moto.dynamodb.exceptions import IncorrectOperandType, IncorrectDataType
from moto.dynamodb.models import Item, DynamoType
from moto.dynamodb.parsing.ast_nodes import (
    UpdateExpression,
    UpdateExpressionAddClause,
    UpdateExpressionAddAction,
    UpdateExpressionRemoveAction,
    UpdateExpressionSetAction,
)
from moto.dynamodb.parsing.executors import UpdateExpressionExecutor
from moto.dynamodb.parsing.expressions import UpdateExpressionParser
from moto.dynamodb.parsing.validators import UpdateExpressionValidator


def test_execution_of_if_not_exists_not_existing_value(table):
    update_expression = "SET a = if_not_exists(b, a)"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "1"}, "a": {"S": "A"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=None,
        item=item,
        table=table,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "1"}, "a": {"S": "A"}},
    )
    assert expected_item == item


def test_execution_of_if_not_exists_with_existing_attribute_should_return_attribute(
    table,
):
    update_expression = "SET a = if_not_exists(b, a)"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "1"}, "a": {"S": "A"}, "b": {"S": "B"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=None,
        item=item,
        table=table,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "1"}, "a": {"S": "B"}, "b": {"S": "B"}},
    )
    assert expected_item == item


def test_execution_of_if_not_exists_with_existing_attribute_should_return_value(table):
    update_expression = "SET a = if_not_exists(b, :val)"
    update_expression_values = {":val": {"N": "4"}}
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "1"}, "b": {"N": "3"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=update_expression_values,
        item=item,
        table=table,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "1"}, "b": {"N": "3"}, "a": {"N": "3"}},
    )
    assert expected_item == item


def test_execution_of_if_not_exists_with_non_existing_attribute_should_return_value(
    table,
):
    update_expression = "SET a = if_not_exists(b, :val)"
    update_expression_values = {":val": {"N": "4"}}
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}), range_key=None, attrs={"id": {"S": "1"}}
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=update_expression_values,
        item=item,
        table=table,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "1"}, "a": {"N": "4"}},
    )
    assert expected_item == item


def test_execution_of_sum_operation(table):
    update_expression = "SET a = a + b"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "1"}, "a": {"N": "3"}, "b": {"N": "4"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=None,
        item=item,
        table=table,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "1"}, "a": {"N": "7"}, "b": {"N": "4"}},
    )
    assert expected_item == item


def test_execution_of_remove(table):
    update_expression = "Remove a"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "1"}, "a": {"N": "3"}, "b": {"N": "4"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=None,
        item=item,
        table=table,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "1"}, "b": {"N": "4"}},
    )
    assert expected_item == item


def test_execution_of_remove_in_map(table):
    update_expression = "Remove itemmap.itemlist[1].foo11"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={
            "id": {"S": "foo2"},
            "itemmap": {
                "M": {
                    "itemlist": {
                        "L": [
                            {"M": {"foo00": {"S": "bar1"}, "foo01": {"S": "bar2"}}},
                            {"M": {"foo10": {"S": "bar1"}, "foo11": {"S": "bar2"}}},
                        ]
                    }
                }
            },
        },
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=None,
        item=item,
        table=table,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={
            "id": {"S": "foo2"},
            "itemmap": {
                "M": {
                    "itemlist": {
                        "L": [
                            {"M": {"foo00": {"S": "bar1"}, "foo01": {"S": "bar2"}}},
                            {"M": {"foo10": {"S": "bar1"}}},
                        ]
                    }
                }
            },
        },
    )
    assert expected_item == item


def test_execution_of_remove_in_list(table):
    update_expression = "Remove itemmap.itemlist[1]"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={
            "id": {"S": "foo2"},
            "itemmap": {
                "M": {
                    "itemlist": {
                        "L": [
                            {"M": {"foo00": {"S": "bar1"}, "foo01": {"S": "bar2"}}},
                            {"M": {"foo10": {"S": "bar1"}, "foo11": {"S": "bar2"}}},
                        ]
                    }
                }
            },
        },
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values=None,
        item=item,
        table=table,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={
            "id": {"S": "foo2"},
            "itemmap": {
                "M": {
                    "itemlist": {
                        "L": [
                            {"M": {"foo00": {"S": "bar1"}, "foo01": {"S": "bar2"}}},
                        ]
                    }
                }
            },
        },
    )
    assert expected_item == item


@pytest.mark.parametrize("attr_name", ["s", "#placeholder"])
def test_execution_of_delete_element_from_set(table, attr_name):
    expression_attribute_names = {"#placeholder": "s"}
    update_expression = f"delete {attr_name} :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "foo2"}, "s": {"SS": ["value1", "value2", "value3"]}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=expression_attribute_names,
        expression_attribute_values={":value": {"SS": ["value2", "value5"]}},
        item=item,
        table=table,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, expression_attribute_names).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "foo2"}, "s": {"SS": ["value1", "value3"]}},
    )
    assert expected_item == item

    # delete last elements
    update_expression = f"delete {attr_name} :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=expression_attribute_names,
        expression_attribute_values={":value": {"SS": ["value1", "value3"]}},
        item=item,
        table=table,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, expression_attribute_names).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}), range_key=None, attrs={"id": {"S": "foo2"}}
    )
    assert expected_item == item


def test_execution_of_add_number(table):
    update_expression = "add s :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "foo2"}, "s": {"N": "5"}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values={":value": {"N": "10"}},
        item=item,
        table=table,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "foo2"}, "s": {"N": "15"}},
    )
    assert expected_item == item


def test_execution_of_add_set_to_a_number(table):
    update_expression = "add s :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "foo2"}, "s": {"N": "5"}},
    )
    try:
        validated_ast = UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values={":value": {"SS": ["s1"]}},
            item=item,
            table=table,
        ).validate()
        UpdateExpressionExecutor(validated_ast, item, None).execute()
        expected_item = Item(
            hash_key=DynamoType({"S": "id"}),
            range_key=None,
            attrs={"id": {"S": "foo2"}, "s": {"N": "15"}},
        )
        assert expected_item == item
        assert False
    except IncorrectDataType:
        assert True


def test_execution_of_add_to_a_set(table):
    update_expression = "ADD s :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "foo2"}, "s": {"SS": ["value1", "value2", "value3"]}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values={":value": {"SS": ["value2", "value5"]}},
        item=item,
        table=table,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={
            "id": {"S": "foo2"},
            "s": {"SS": ["value1", "value2", "value3", "value5"]},
        },
    )
    assert expected_item == item


@pytest.mark.parametrize(
    "expression_attribute_values,unexpected_data_type",
    [
        ({":value": {"S": "10"}}, "STRING"),
        ({":value": {"N": "10"}}, "NUMBER"),
        ({":value": {"B": "10"}}, "BINARY"),
        ({":value": {"BOOL": True}}, "BOOLEAN"),
        ({":value": {"NULL": True}}, "NULL"),
        ({":value": {"M": {"el0": {"S": "10"}}}}, "MAP"),
        ({":value": {"L": []}}, "LIST"),
    ],
)
def test_execution_of__delete_element_from_set_invalid_value(
    expression_attribute_values, unexpected_data_type, table
):
    """A delete statement must use a value of type SS in order to delete elements from a set."""
    update_expression = "delete s :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "foo2"}, "s": {"SS": ["value1", "value2", "value3"]}},
    )
    try:
        validated_ast = UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values=expression_attribute_values,
            item=item,
            table=table,
        ).validate()
        UpdateExpressionExecutor(validated_ast, item, None).execute()
        assert False, "Must raise exception"
    except IncorrectOperandType as e:
        assert e.operator_or_function == "operator: DELETE"
        assert e.operand_type == unexpected_data_type


def test_execution_of_delete_element_from_a_string_attribute(table):
    """A delete statement must use a value of type SS in order to delete elements from a set."""
    update_expression = "delete s :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "foo2"}, "s": {"S": "5"}},
    )
    try:
        validated_ast = UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values={":value": {"SS": ["value2"]}},
            item=item,
            table=table,
        ).validate()
        UpdateExpressionExecutor(validated_ast, item, None).execute()
        assert False, "Must raise exception"
    except IncorrectDataType:
        assert True


def test_normalize_with_one_action(table):
    update_expression = "ADD s :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={"id": {"S": "foo2"}, "s": {"SS": ["value1", "value2", "value3"]}},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values={":value": {"SS": ["value2", "value5"]}},
        item=item,
        table=table,
    ).validate()
    validated_ast.children.should.have.length_of(1)
    validated_ast.children[0].should.be.a(UpdateExpressionAddClause)

    validated_ast.normalize()
    validated_ast.children.should.have.length_of(1)
    validated_ast.children[0].should.be.a(UpdateExpressionAddAction)


def test_normalize_with_multiple_actions__order_is_preserved(table):
    update_expression = "ADD s :value REMOVE a[3], a[1], a[2] SET t=:value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        range_key=None,
        attrs={
            "id": {"S": "foo2"},
            "a": {"L": [{"S": "val1"}, {"S": "val2"}, {"S": "val3"}, {"S": "val4"}]},
            "s": {"SS": ["value1", "value2", "value3"]},
        },
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values={":value": {"SS": ["value2", "value5"]}},
        item=item,
        table=table,
    ).validate()
    validated_ast.children.should.have.length_of(2)
    # add clause first
    validated_ast.children[0].should.be.a(UpdateExpressionAddClause)
    # rest of the expression next
    validated_ast.children[1].should.be.a(UpdateExpression)

    validated_ast.normalize()
    validated_ast.children.should.have.length_of(5)
    # add action first
    validated_ast.children[0].should.be.a(UpdateExpressionAddAction)
    # Removal actions in reverse order
    validated_ast.children[1].should.be.a(UpdateExpressionRemoveAction)
    validated_ast.children[1]._get_value().should.equal(3)
    validated_ast.children[2].should.be.a(UpdateExpressionRemoveAction)
    validated_ast.children[2]._get_value().should.equal(2)
    validated_ast.children[3].should.be.a(UpdateExpressionRemoveAction)
    validated_ast.children[3]._get_value().should.equal(1)
    # Set action last, as per insertion order
    validated_ast.children[4].should.be.a(UpdateExpressionSetAction)
