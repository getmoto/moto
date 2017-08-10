from __future__ import unicode_literals
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

    'NULL': lambda item_value: item_value is None,
    'NOT_NULL': lambda item_value: item_value is not None,
    'CONTAINS': lambda item_value, test_value: test_value in item_value,
    'NOT_CONTAINS': lambda item_value, test_value: test_value not in item_value,
    'BEGINS_WITH': lambda item_value, test_value: item_value.startswith(test_value),
    'IN': lambda item_value, *test_values: item_value in test_values,
    'BETWEEN': lambda item_value, lower_test_value, upper_test_value: lower_test_value <= item_value <= upper_test_value,
}


def get_comparison_func(range_comparison):
    return COMPARISON_FUNCS.get(range_comparison)
