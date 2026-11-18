# mypy: ignore-errors
"""DynamoDB type tags need no alias search; custom pickers still do."""

import json

import pytest

from moto.core.serialize import (
    AttributeAliasProvider,
    JSONSerializer,
    NoAlias,
    XFormedAttributePicker,
    get_serializer_class,
)
from moto.core.utils import get_service_model


def serialize(item, picker, optimized=True):
    operation = get_service_model("dynamodb").operation_model("GetItem")
    serializer = (
        get_serializer_class("dynamodb", "json") if optimized else JSONSerializer
    )
    return serializer(operation, value_picker=picker).serialize({"Item": item})


def test_canonical_attribute_values_skip_alias_search(monkeypatch):
    item = {
        "string": {"S": ""},
        "number": {"N": "1.25"},
        "binary": {"B": b"\x00\x01"},
        "boolean": {"BOOL": False},
        "null": {"NULL": True},
        "strings": {"SS": ["a", "b"]},
        "numbers": {"NS": ["1", "2"]},
        "binaries": {"BS": [b"a", b"b"]},
        "empty_map": {"M": {}},
        "empty_list": {"L": []},
        "nested": {"M": {"S": {"L": [{"N": "0"}, {"M": {"x": {"BOOL": True}}}]}}},
    }
    original = XFormedAttributePicker.__call__
    attribute_lookups = []

    def track(self, context):
        parent = getattr(context.shape, "parent", None)
        if parent is not None and parent.name == "AttributeValue":
            attribute_lookups.append(context.key)
        return original(self, context)

    monkeypatch.setattr(XFormedAttributePicker, "__call__", track)
    expected = serialize(item, XFormedAttributePicker(), optimized=False)
    assert attribute_lookups
    attribute_lookups.clear()
    actual = serialize(item, XFormedAttributePicker())
    assert actual == expected
    assert attribute_lookups == []


class AliasStringToNumber(AttributeAliasProvider):
    def has_alias(self, key):
        return key == "S"

    def get_alias(self, key):
        return "N"


def test_custom_alias_providers_are_preserved():
    item = {"value": {"N": "7"}}
    picker = XFormedAttributePicker(alias_providers=[AliasStringToNumber, NoAlias])
    result = serialize(item, picker)
    assert result == serialize(item, picker, optimized=False)
    assert json.loads(result["body"])["Item"]["value"]["S"] == "7"


def test_response_transformers_are_preserved():
    item = {"value": {"S": "original"}}
    picker = XFormedAttributePicker(
        response_transformers={
            ".S": lambda value: "transformed" if value is not None else None
        }
    )
    result = serialize(item, picker)
    assert result == serialize(item, picker, optimized=False)
    assert json.loads(result["body"])["Item"]["value"]["S"] == "transformed"


@pytest.mark.parametrize(
    "subclass", [False, True], ids=["custom-picker", "picker-subclass"]
)
def test_custom_value_pickers_are_preserved(subclass):
    class CustomPicker(XFormedAttributePicker):
        def __call__(self, context):
            if context.key == "S":
                return "custom"
            return super().__call__(context)

    def custom_picker(context):
        return "custom" if context.key == "S" else context.obj.get(context.key)

    picker = CustomPicker() if subclass else custom_picker
    item = {"value": {"S": "original"}}
    result = serialize(item, picker)
    assert result == serialize(item, picker, optimized=False)
    assert json.loads(result["body"])["Item"]["value"]["S"] == "custom"


@pytest.mark.parametrize("source", ["lowercase", "dict-subclass", "object"])
def test_noncanonical_attribute_values_keep_alias_lookup(source):
    class AliasedDict(dict):
        class Meta:
            serialization_aliases = {"S": "N"}

    class Value:
        s = "original"

    value = {
        "lowercase": {"s": "original"},
        "dict-subclass": AliasedDict(N="original"),
        "object": Value(),
    }[source]
    item = {"value": value}
    result = serialize(item, XFormedAttributePicker())
    assert result == serialize(item, XFormedAttributePicker(), optimized=False)
    assert json.loads(result["body"])["Item"]["value"]["S"] == "original"
