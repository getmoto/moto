import pytest

from moto.dynamodb.exceptions import (
    InvalidTokenException,
    InvalidExpressionAttributeNameKey,
)
from moto.dynamodb.parsing.tokens import ExpressionTokenizer, Token


def test_expression_tokenizer_single_set_action():
    set_action = "SET attrName = :attrValue"
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE, "attrName"),
        Token(Token.WHITESPACE, " "),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE_VALUE, ":attrValue"),
    ]


def test_expression_tokenizer_single_set_action_leading_space():
    set_action = "Set attrName = :attrValue"
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "Set"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE, "attrName"),
        Token(Token.WHITESPACE, " "),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE_VALUE, ":attrValue"),
    ]


def test_expression_tokenizer_single_set_action_attribute_name_leading_space():
    set_action = "SET #a = :attrValue"
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE_NAME, "#a"),
        Token(Token.WHITESPACE, " "),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE_VALUE, ":attrValue"),
    ]


def test_expression_tokenizer_single_set_action_trailing_space():
    set_action = "SET attrName = :attrValue "
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE, "attrName"),
        Token(Token.WHITESPACE, " "),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE_VALUE, ":attrValue"),
        Token(Token.WHITESPACE, " "),
    ]


def test_expression_tokenizer_single_set_action_multi_spaces():
    set_action = "SET    attrName    =  :attrValue  "
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, "    "),
        Token(Token.ATTRIBUTE, "attrName"),
        Token(Token.WHITESPACE, "    "),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.WHITESPACE, "  "),
        Token(Token.ATTRIBUTE_VALUE, ":attrValue"),
        Token(Token.WHITESPACE, "  "),
    ]


def test_expression_tokenizer_single_set_action_with_numbers_in_identifiers():
    set_action = "SET attrName3 = :attr3Value"
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE, "attrName3"),
        Token(Token.WHITESPACE, " "),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE_VALUE, ":attr3Value"),
    ]


def test_expression_tokenizer_single_set_action_with_underscore_in_identifier():
    set_action = "SET attr_Name = :attr_Value"
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE, "attr_Name"),
        Token(Token.WHITESPACE, " "),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE_VALUE, ":attr_Value"),
    ]


def test_expression_tokenizer_leading_underscore_in_attribute_name_expression():
    """Leading underscore is not allowed for an attribute name"""
    set_action = "SET attrName = _idid"
    with pytest.raises(InvalidTokenException) as te:
        ExpressionTokenizer.make_list(set_action)
    assert te.value.token == "_"
    assert te.value.near == "= _idid"


def test_expression_tokenizer_leading_underscore_in_attribute_value_expression():
    """Leading underscore is allowed in an attribute value"""
    set_action = "SET attrName = :_attrValue"
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE, "attrName"),
        Token(Token.WHITESPACE, " "),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE_VALUE, ":_attrValue"),
    ]


def test_expression_tokenizer_single_set_action_nested_attribute():
    set_action = "SET attrName.elem = :attrValue"
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE, "attrName"),
        Token(Token.DOT, "."),
        Token(Token.ATTRIBUTE, "elem"),
        Token(Token.WHITESPACE, " "),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE_VALUE, ":attrValue"),
    ]


def test_expression_tokenizer_list_index_with_sub_attribute():
    set_action = "SET itemmap.itemlist[1].foos=:Item"
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE, "itemmap"),
        Token(Token.DOT, "."),
        Token(Token.ATTRIBUTE, "itemlist"),
        Token(Token.OPEN_SQUARE_BRACKET, "["),
        Token(Token.NUMBER, "1"),
        Token(Token.CLOSE_SQUARE_BRACKET, "]"),
        Token(Token.DOT, "."),
        Token(Token.ATTRIBUTE, "foos"),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.ATTRIBUTE_VALUE, ":Item"),
    ]


def test_expression_tokenizer_list_index_surrounded_with_whitespace():
    set_action = "SET itemlist[ 1  ]=:Item"
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE, "itemlist"),
        Token(Token.OPEN_SQUARE_BRACKET, "["),
        Token(Token.WHITESPACE, " "),
        Token(Token.NUMBER, "1"),
        Token(Token.WHITESPACE, "  "),
        Token(Token.CLOSE_SQUARE_BRACKET, "]"),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.ATTRIBUTE_VALUE, ":Item"),
    ]


def test_expression_tokenizer_single_set_action_attribute_name_invalid_key():
    """
    ExpressionAttributeNames contains invalid key: Syntax error; key: "#va#l2"
    """
    set_action = "SET #va#l2 = 3"
    with pytest.raises(InvalidExpressionAttributeNameKey) as e:
        ExpressionTokenizer.make_list(set_action)
    assert e.value.key == "#va#l2"


def test_expression_tokenizer_single_set_action_attribute_name_invalid_key_double_hash():
    """
    ExpressionAttributeNames contains invalid key: Syntax error; key: "#va#l"
    """
    set_action = "SET #va#l = 3"
    with pytest.raises(InvalidExpressionAttributeNameKey) as e:
        ExpressionTokenizer.make_list(set_action)
    assert e.value.key == "#va#l"


def test_expression_tokenizer_single_set_action_attribute_name_valid_key():
    set_action = "SET attr=#val2"
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE, "attr"),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.ATTRIBUTE_NAME, "#val2"),
    ]


def test_expression_tokenizer_single_set_action_attribute_name_leading_number():
    set_action = "SET attr=#0"
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE, "attr"),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.ATTRIBUTE_NAME, "#0"),
    ]


def test_expression_tokenizer_single_set_action_attribute_name_leading_underscore():
    set_action = "SET attr=#_sth"
    token_list = ExpressionTokenizer.make_list(set_action)
    assert token_list == [
        Token(Token.ATTRIBUTE, "SET"),
        Token(Token.WHITESPACE, " "),
        Token(Token.ATTRIBUTE, "attr"),
        Token(Token.EQUAL_SIGN, "="),
        Token(Token.ATTRIBUTE_NAME, "#_sth"),
    ]


def test_expression_tokenizer_just_a_pipe():
    set_action = "|"
    with pytest.raises(InvalidTokenException) as te:
        ExpressionTokenizer.make_list(set_action)
    assert te.value.token == "|"
    assert te.value.near == "|"


def test_expression_tokenizer_just_a_pipe_with_leading_white_spaces():
    set_action = "   |"
    with pytest.raises(InvalidTokenException) as te:
        ExpressionTokenizer.make_list(set_action)
    assert te.value.token == "|"
    assert te.value.near == "   |"


def test_expression_tokenizer_just_a_pipe_for_set_expression():
    set_action = "SET|"
    with pytest.raises(InvalidTokenException) as te:
        ExpressionTokenizer.make_list(set_action)
    assert te.value.token == "|"
    assert te.value.near == "SET|"


def test_expression_tokenizer_just_an_attribute_and_a_pipe_for_set_expression():
    set_action = "SET a|"
    with pytest.raises(InvalidTokenException) as te:
        ExpressionTokenizer.make_list(set_action)
    assert te.value.token == "|"
    assert te.value.near == "a|"
