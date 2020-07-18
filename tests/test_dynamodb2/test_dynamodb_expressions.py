from moto.dynamodb2.exceptions import InvalidTokenException
from moto.dynamodb2.parsing.expressions import UpdateExpressionParser
from moto.dynamodb2.parsing.reserved_keywords import ReservedKeywords


def test_get_reserved_keywords():
    reserved_keywords = ReservedKeywords.get_reserved_keywords()
    assert "SET" in reserved_keywords
    assert "DELETE" in reserved_keywords
    assert "ADD" in reserved_keywords
    # REMOVE is not part of the list of reserved keywords.
    assert "REMOVE" not in reserved_keywords


def test_update_expression_numeric_literal_in_expression():
    set_action = "SET attrName = 3"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "3"
        assert te.near == "= 3"


def test_expression_tokenizer_multi_number_numeric_literal_in_expression():
    set_action = "SET attrName = 34"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "34"
        assert te.near == "= 34"


def test_expression_tokenizer_numeric_literal_unclosed_square_bracket():
    set_action = "SET MyStr[ 3"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "<EOF>"
        assert te.near == "3"


def test_expression_tokenizer_wrong_closing_bracket_with_space():
    set_action = "SET MyStr[3 )"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == ")"
        assert te.near == "3 )"


def test_expression_tokenizer_wrong_closing_bracket():
    set_action = "SET MyStr[3)"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == ")"
        assert te.near == "3)"


def test_expression_tokenizer_only_numeric_literal_for_set():
    set_action = "SET 2"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "2"
        assert te.near == "SET 2"


def test_expression_tokenizer_only_numeric_literal():
    set_action = "2"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "2"
        assert te.near == "2"


def test_expression_tokenizer_set_closing_round_bracket():
    set_action = "SET )"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == ")"
        assert te.near == "SET )"


def test_expression_tokenizer_set_closing_followed_by_numeric_literal():
    set_action = "SET ) 3"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == ")"
        assert te.near == "SET ) 3"


def test_expression_tokenizer_numeric_literal_unclosed_square_bracket_trailing_space():
    set_action = "SET MyStr[ 3 "
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "<EOF>"
        assert te.near == "3 "


def test_expression_tokenizer_unbalanced_round_brackets_only_opening():
    set_action = "SET MyStr = (:_val"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "<EOF>"
        assert te.near == ":_val"


def test_expression_tokenizer_unbalanced_round_brackets_only_opening_trailing_space():
    set_action = "SET MyStr = (:_val "
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "<EOF>"
        assert te.near == ":_val "


def test_expression_tokenizer_unbalanced_square_brackets_only_opening():
    set_action = "SET MyStr = [:_val"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "["
        assert te.near == "= [:_val"


def test_expression_tokenizer_unbalanced_square_brackets_only_opening_trailing_spaces():
    set_action = "SET MyStr = [:_val  "
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "["
        assert te.near == "= [:_val"


def test_expression_tokenizer_unbalanced_round_brackets_multiple_opening():
    set_action = "SET MyStr = (:_val + (:val2"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "<EOF>"
        assert te.near == ":val2"


def test_expression_tokenizer_unbalanced_round_brackets_only_closing():
    set_action = "SET MyStr = ):_val"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == ")"
        assert te.near == "= ):_val"


def test_expression_tokenizer_unbalanced_square_brackets_only_closing():
    set_action = "SET MyStr = ]:_val"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "]"
        assert te.near == "= ]:_val"


def test_expression_tokenizer_unbalanced_round_brackets_only_closing_followed_by_other_parts():
    set_action = "SET MyStr = ):_val + :val2"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == ")"
        assert te.near == "= ):_val"


def test_update_expression_starts_with_keyword_reset_followed_by_identifier():
    update_expression = "RESET NonExistent"
    try:
        UpdateExpressionParser.make(update_expression)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "RESET"
        assert te.near == "RESET NonExistent"


def test_update_expression_starts_with_keyword_reset_followed_by_identifier_and_value():
    update_expression = "RESET NonExistent value"
    try:
        UpdateExpressionParser.make(update_expression)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "RESET"
        assert te.near == "RESET NonExistent"


def test_update_expression_starts_with_leading_spaces_and_keyword_reset_followed_by_identifier_and_value():
    update_expression = "  RESET NonExistent value"
    try:
        UpdateExpressionParser.make(update_expression)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "RESET"
        assert te.near == "  RESET NonExistent"


def test_update_expression_with_only_keyword_reset():
    update_expression = "RESET"
    try:
        UpdateExpressionParser.make(update_expression)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "RESET"
        assert te.near == "RESET"


def test_update_nested_expression_with_selector_just_should_fail_parsing_at_numeric_literal_value():
    update_expression = "SET a[0].b = 5"
    try:
        UpdateExpressionParser.make(update_expression)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "5"
        assert te.near == "= 5"


def test_update_nested_expression_with_selector_and_spaces_should_only_fail_parsing_at_numeric_literal_value():
    update_expression = "SET a [  2 ]. b = 5"
    try:
        UpdateExpressionParser.make(update_expression)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "5"
        assert te.near == "= 5"


def test_update_nested_expression_with_double_selector_and_spaces_should_only_fail_parsing_at_numeric_literal_value():
    update_expression = "SET a [2][ 3  ]. b = 5"
    try:
        UpdateExpressionParser.make(update_expression)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "5"
        assert te.near == "= 5"


def test_update_nested_expression_should_only_fail_parsing_at_numeric_literal_value():
    update_expression = "SET a . b = 5"
    try:
        UpdateExpressionParser.make(update_expression)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "5"
        assert te.near == "= 5"


def test_nested_selectors_in_update_expression_should_fail_at_nesting():
    update_expression = "SET a [  [2] ]. b = 5"
    try:
        UpdateExpressionParser.make(update_expression)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "["
        assert te.near == "[  [2"


def test_update_expression_number_in_selector_cannot_be_splite():
    update_expression = "SET a [2 1]. b = 5"
    try:
        UpdateExpressionParser.make(update_expression)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "1"
        assert te.near == "2 1]"


def test_update_expression_cannot_have_successive_attributes():
    update_expression = "SET #a a = 5"
    try:
        UpdateExpressionParser.make(update_expression)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "a"
        assert te.near == "#a a ="


def test_update_expression_path_with_both_attribute_and_attribute_name_should_only_fail_at_numeric_value():
    update_expression = "SET #a.a = 5"
    try:
        UpdateExpressionParser.make(update_expression)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "5"
        assert te.near == "= 5"


def test_expression_tokenizer_2_same_operators_back_to_back():
    set_action = "SET MyStr = NoExist + + :_val "
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "+"
        assert te.near == "+ + :_val"


def test_expression_tokenizer_2_different_operators_back_to_back():
    set_action = "SET MyStr = NoExist + - :_val "
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "-"
        assert te.near == "+ - :_val"


def test_update_expression_remove_does_not_allow_operations():
    remove_action = "REMOVE NoExist + "
    try:
        UpdateExpressionParser.make(remove_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "+"
        assert te.near == "NoExist + "


def test_update_expression_add_does_not_allow_attribute_after_path():
    """value here is not really a value since a value starts with a colon (:)"""
    add_expr = "ADD attr val foobar"
    try:
        UpdateExpressionParser.make(add_expr)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "val"
        assert te.near == "attr val foobar"


def test_update_expression_add_does_not_allow_attribute_foobar_after_value():
    add_expr = "ADD attr :val foobar"
    try:
        UpdateExpressionParser.make(add_expr)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "foobar"
        assert te.near == ":val foobar"


def test_update_expression_delete_does_not_allow_attribute_after_path():
    """value here is not really a value since a value starts with a colon (:)"""
    delete_expr = "DELETE attr val"
    try:
        UpdateExpressionParser.make(delete_expr)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "val"
        assert te.near == "attr val"


def test_update_expression_delete_does_not_allow_attribute_foobar_after_value():
    delete_expr = "DELETE attr :val foobar"
    try:
        UpdateExpressionParser.make(delete_expr)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "foobar"
        assert te.near == ":val foobar"


def test_update_expression_parsing_is_not_keyword_aware():
    """path and VALUE are keywords. Yet a token error will be thrown for the numeric literal 1."""
    delete_expr = "SET path = VALUE 1"
    try:
        UpdateExpressionParser.make(delete_expr)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "1"
        assert te.near == "VALUE 1"


def test_expression_if_not_exists_is_not_valid_in_remove_statement():
    set_action = "REMOVE if_not_exists(a,b)"
    try:
        UpdateExpressionParser.make(set_action)
        assert False, "Exception not raised correctly"
    except InvalidTokenException as te:
        assert te.token == "("
        assert te.near == "if_not_exists(a"
