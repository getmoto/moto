import sure  # noqa
from nose.tools import assert_true, assert_equal, assert_in
from moto.emr.utils import Unflattener, CamelToUnderscoresWalker


def test_unflattener_just_dicts():
    prefix = "a"
    data = {"a.a.a": 1, "a.a.b": 2, "a.b.a": 3, "a.c": 6, "b.a.a": 4, "c.a.a": 5}

    Unflattener.unflatten_complex_params(data, prefix)

    expected = {
        "a": {"a": {"a": 1, "b": 2}, "b": {"a": 3}, "c": 6},
        "b.a.a": 4,
        "c.a.a": 5,
    }
    assert_equal(data, expected)


def test_unflattener_list_of_scalars():
    prefix = "a"
    data = {
        "a.member.1": 1,
        "a.member.2": 2,
        "a.member.3": 3,
        "a.member.4": 4,
        "b.member.1.a.a": 5,
    }

    Unflattener.unflatten_complex_params(data, prefix)

    expected = {"a": [1, 2, 3, 4], "b.member.1.a.a": 5}
    assert_equal(data, expected)


def test_unflattener_list_dicts():
    prefix = "a"
    data = {
        "a.member.1.a.a": 1,
        "a.member.1.a.b": 2,
        "a.member.1.b.c": 3,
        "a.member.2.d.e": 4,
        "b.member.1.a.a": 5,
        "a.member.3": 6,
        "a.member.4.a.member.1": 7,
        "a.member.4.a.member.2.a": 8,
        "a.member.5.member.1": 9,
    }

    Unflattener.unflatten_complex_params(data, prefix)

    expected = {
        "a": [
            {"a": {"a": 1, "b": 2}, "b": {"c": 3}},
            {"d": {"e": 4,},},
            6,
            {"a": [7, {"a": 8}]},
            [9],
        ],
        "b.member.1.a.a": 5,
    }
    assert_equal(data, expected)


def test_camels_to_underscores_walker_flat_dict():
    input = {
        "CamelCase1": 1,
        "CamelCase2": 2,
        "CamelCase3": 3,
    }
    output = CamelToUnderscoresWalker.parse(input)
    expected = {
        "camel_case1": 1,
        "camel_case2": 2,
        "camel_case3": 3,
    }
    assert_equal(output, expected)


def test_camels_to_underscores_walker_deeper_dict():
    input = {
        "CamelCase1": {"CamelCase1A": 1, "CamelCase1B": 2},
        "CamelCase2": {"CamelCase2A": 3, "CamelCase2B": 4},
    }
    output = CamelToUnderscoresWalker.parse(input)
    expected = {
        "camel_case1": {"camel_case1_a": 1, "camel_case1_b": 2},
        "camel_case2": {"camel_case2_a": 3, "camel_case2_b": 4},
    }
    assert_equal(output, expected)


def test_camels_to_underscores_walker_lists_of_dicts():
    input = [{"CamelCase1A": 1, "CamelCase1B": 2}, {"CamelCase2A": 3, "CamelCase2B": 4}]
    output = CamelToUnderscoresWalker.parse(input)
    expected = [
        {"camel_case1_a": 1, "camel_case1_b": 2},
        {"camel_case2_a": 3, "camel_case2_b": 4},
    ]
    assert_equal(output, expected)


def test_camels_to_underscores_walker_dicts_of_lists():
    input = {
        "CamelCase1": [
            {"CamelCase11A": 1, "CamelCase11B": 2},
            {"CamelCase12A": 3, "CamelCase12B": 4},
        ],
        "CamelCase2": [
            {"CamelCase21A": 5, "CamelCase21B": 6},
            {"CamelCase22A": 7, "CamelCase22B": 8},
        ],
    }
    output = CamelToUnderscoresWalker.parse(input)
    expected = {
        "camel_case1": [
            {"camel_case11_a": 1, "camel_case11_b": 2},
            {"camel_case12_a": 3, "camel_case12_b": 4},
        ],
        "camel_case2": [
            {"camel_case21_a": 5, "camel_case21_b": 6},
            {"camel_case22_a": 7, "camel_case22_b": 8},
        ],
    }
    assert_equal(output, expected)
