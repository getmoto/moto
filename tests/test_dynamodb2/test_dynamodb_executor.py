from moto.dynamodb2.exceptions import IncorrectOperandType, IncorrectDataType
from moto.dynamodb2.models import Item, DynamoType
from moto.dynamodb2.parsing.executors import UpdateExpressionExecutor
from moto.dynamodb2.parsing.expressions import UpdateExpressionParser
from moto.dynamodb2.parsing.validators import UpdateExpressionValidator
from parameterized import parameterized


def test_execution_of_if_not_exists_not_existing_value():
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
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "a": {"S": "A"}},
    )
    assert expected_item == item


def test_execution_of_if_not_exists_with_existing_attribute_should_return_attribute():
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
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "a": {"S": "B"}, "b": {"S": "B"}},
    )
    assert expected_item == item


def test_execution_of_if_not_exists_with_existing_attribute_should_return_value():
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
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "b": {"N": "3"}, "a": {"N": "3"}},
    )
    assert expected_item == item


def test_execution_of_if_not_exists_with_non_existing_attribute_should_return_value():
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
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "a": {"N": "4"}},
    )
    assert expected_item == item


def test_execution_of_sum_operation():
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
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "a": {"N": "7"}, "b": {"N": "4"}},
    )
    assert expected_item == item


def test_execution_of_remove():
    update_expression = "Remove a"
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
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "1"}, "b": {"N": "4"}},
    )
    assert expected_item == item


def test_execution_of_remove_in_map():
    update_expression = "Remove itemmap.itemlist[1].foo11"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
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
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={
            "id": {"S": "foo2"},
            "itemmap": {
                "M": {
                    "itemlist": {
                        "L": [
                            {"M": {"foo00": {"S": "bar1"}, "foo01": {"S": "bar2"}}},
                            {"M": {"foo10": {"S": "bar1"},}},
                        ]
                    }
                }
            },
        },
    )
    assert expected_item == item


def test_execution_of_remove_in_list():
    update_expression = "Remove itemmap.itemlist[1]"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
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
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={
            "id": {"S": "foo2"},
            "itemmap": {
                "M": {
                    "itemlist": {
                        "L": [{"M": {"foo00": {"S": "bar1"}, "foo01": {"S": "bar2"}}},]
                    }
                }
            },
        },
    )
    assert expected_item == item


def test_execution_of_delete_element_from_set():
    update_expression = "delete s :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "foo2"}, "s": {"SS": ["value1", "value2", "value3"]},},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values={":value": {"SS": ["value2", "value5"]}},
        item=item,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "foo2"}, "s": {"SS": ["value1", "value3"]},},
    )
    assert expected_item == item


def test_execution_of_add_number():
    update_expression = "add s :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "foo2"}, "s": {"N": "5"},},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values={":value": {"N": "10"}},
        item=item,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "foo2"}, "s": {"N": "15"}},
    )
    assert expected_item == item


def test_execution_of_add_set_to_a_number():
    update_expression = "add s :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "foo2"}, "s": {"N": "5"},},
    )
    try:
        validated_ast = UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values={":value": {"SS": ["s1"]}},
            item=item,
        ).validate()
        UpdateExpressionExecutor(validated_ast, item, None).execute()
        expected_item = Item(
            hash_key=DynamoType({"S": "id"}),
            hash_key_type="TYPE",
            range_key=None,
            range_key_type=None,
            attrs={"id": {"S": "foo2"}, "s": {"N": "15"}},
        )
        assert expected_item == item
        assert False
    except IncorrectDataType:
        assert True


def test_execution_of_add_to_a_set():
    update_expression = "ADD s :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "foo2"}, "s": {"SS": ["value1", "value2", "value3"]},},
    )
    validated_ast = UpdateExpressionValidator(
        update_expression_ast,
        expression_attribute_names=None,
        expression_attribute_values={":value": {"SS": ["value2", "value5"]}},
        item=item,
    ).validate()
    UpdateExpressionExecutor(validated_ast, item, None).execute()
    expected_item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={
            "id": {"S": "foo2"},
            "s": {"SS": ["value1", "value2", "value3", "value5"]},
        },
    )
    assert expected_item == item


@parameterized(
    [
        ({":value": {"S": "10"}}, "STRING",),
        ({":value": {"N": "10"}}, "NUMBER",),
        ({":value": {"B": "10"}}, "BINARY",),
        ({":value": {"BOOL": True}}, "BOOLEAN",),
        ({":value": {"NULL": True}}, "NULL",),
        ({":value": {"M": {"el0": {"S": "10"}}}}, "MAP",),
        ({":value": {"L": []}}, "LIST",),
    ]
)
def test_execution_of__delete_element_from_set_invalid_value(
    expression_attribute_values, unexpected_data_type
):
    """A delete statement must use a value of type SS in order to delete elements from a set."""
    update_expression = "delete s :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "foo2"}, "s": {"SS": ["value1", "value2", "value3"]},},
    )
    try:
        validated_ast = UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values=expression_attribute_values,
            item=item,
        ).validate()
        UpdateExpressionExecutor(validated_ast, item, None).execute()
        assert False, "Must raise exception"
    except IncorrectOperandType as e:
        assert e.operator_or_function == "operator: DELETE"
        assert e.operand_type == unexpected_data_type


def test_execution_of_delete_element_from_a_string_attribute():
    """A delete statement must use a value of type SS in order to delete elements from a set."""
    update_expression = "delete s :value"
    update_expression_ast = UpdateExpressionParser.make(update_expression)
    item = Item(
        hash_key=DynamoType({"S": "id"}),
        hash_key_type="TYPE",
        range_key=None,
        range_key_type=None,
        attrs={"id": {"S": "foo2"}, "s": {"S": "5"},},
    )
    try:
        validated_ast = UpdateExpressionValidator(
            update_expression_ast,
            expression_attribute_names=None,
            expression_attribute_values={":value": {"SS": ["value2"]}},
            item=item,
        ).validate()
        UpdateExpressionExecutor(validated_ast, item, None).execute()
        assert False, "Must raise exception"
    except IncorrectDataType:
        assert True
