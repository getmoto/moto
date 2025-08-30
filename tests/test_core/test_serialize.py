# mypy: ignore-errors
"""Additional tests for response serialization.

While there are compliance tests in ``test_protocols.py``, where the majority
of the response serialization is tested, this file contains additional tests
that go above and beyond the specification(s) for a number of reasons:

* We are testing Python-specific behavior that doesn't make sense as a
  compliance test.
* We are testing behavior that is not strictly part of the specification.
  These may result in a coverage gap that would otherwise be untested.

"""

import time

from botocore.model import ServiceModel, ShapeResolver
from xmltodict import parse

from moto.core.exceptions import ServiceException
from moto.core.serialize import (
    AttributePickerContext,
    JSONSerializer,
    QuerySerializer,
    XFormedAttributePicker,
    never_return,
    return_if_not_empty,
    url_encode,
)


def test_aws_query_compatible_error() -> None:
    model = {
        "metadata": {
            "protocol": "json",
            "apiVersion": "2014-01-01",
            "awsQueryCompatible": {},
        },
        "documentation": "",
        "operations": {
            "TestOperation": {
                "name": "TestOperation",
                "http": {
                    "method": "POST",
                    "requestUri": "/",
                },
            }
        },
        "shapes": {
            "QueryCompatibleError": {
                "type": "structure",
                "members": {
                    "message": {"shape": "StringType"},
                },
                "error": {
                    "code": "PreservedErrorCode",
                    "httpStatusCode": 409,
                    "senderFault": True,
                },
                "exception": True,
            },
            "StringType": {
                "type": "string",
            },
        },
    }

    class TestError(ServiceException):
        pass

    service_model = ServiceModel(model)
    operation_model = service_model.operation_model("TestOperation")
    serializer = JSONSerializer(operation_model)
    serialized = serializer.serialize(TestError("PreservedErrorCode", "test-message"))
    assert serialized["status_code"] == 409
    headers = serialized["headers"]
    assert headers.get("x-amzn-query-error") == "PreservedErrorCode;Sender"


def test_serialize_from_object() -> None:
    model = {
        "metadata": {"protocol": "query", "apiVersion": "2014-01-01"},
        "documentation": "",
        "operations": {
            "TestOperation": {
                "name": "TestOperation",
                "http": {
                    "method": "POST",
                    "requestUri": "/",
                },
                "output": {"shape": "OutputShape"},
            }
        },
        "shapes": {
            "OutputShape": {
                "type": "structure",
                "members": {
                    "string": {"shape": "StringType"},
                },
            },
            "StringType": {
                "type": "string",
            },
        },
    }

    class TestObject:
        string = "test-string"

    service_model = ServiceModel(model)
    operation_model = service_model.operation_model("TestOperation")
    serializer = QuerySerializer(operation_model)
    serialized = serializer.serialize(TestObject())
    assert serialized


def test_datetime_with_microseconds() -> None:
    model = {
        "metadata": {"protocol": "query", "apiVersion": "2014-01-01"},
        "documentation": "",
        "operations": {
            "TestOperation": {
                "name": "TestOperation",
                "http": {
                    "method": "POST",
                    "requestUri": "/",
                },
                "output": {"shape": "OutputShape"},
            }
        },
        "shapes": {
            "OutputShape": {
                "type": "structure",
                "members": {
                    "microseconds": {"shape": "TimestampType"},
                },
            },
            "TimestampType": {
                "type": "timestamp",
            },
        },
    }

    class TestObject:
        microseconds = time.time()

    service_model = ServiceModel(model)
    operation_model = service_model.operation_model("TestOperation")
    serializer = QuerySerializer(operation_model)
    serialized = serializer.serialize(TestObject())
    assert serialized
    parsed = parse(serialized["body"])
    time_str = parsed["TestOperationResponse"]["OutputShapeResult"]["microseconds"]
    assert "." in time_str
    assert time_str[-1] == "Z"


def test_pretty_print_with_short_elements_and_list() -> None:
    model = {
        "metadata": {"protocol": "query", "apiVersion": "2014-01-01"},
        "documentation": "",
        "operations": {
            "TestOperation": {
                "name": "TestOperation",
                "http": {
                    "method": "POST",
                    "requestUri": "/",
                },
                "output": {"shape": "OutputShape"},
            }
        },
        "shapes": {
            "OutputShape": {
                "type": "structure",
                "members": {
                    "DBInstances": {
                        "shape": "DBInstanceList",
                    }
                },
            },
            "DBInstanceList": {
                "type": "list",
                "member": {"shape": "DBInstance", "locationName": "DBInstance"},
            },
            "DBInstance": {
                "type": "structure",
                "members": {
                    "DBInstanceIdentifier": {
                        "shape": "String",
                    }
                },
            },
            "String": {"type": "string"},
        },
    }
    service_model = ServiceModel(model)
    operation_model = service_model.operation_model("TestOperation")
    serializer = QuerySerializer(operation_model, **{"pretty_print": True})
    empty_list_to_serialize = {"DBInstances": []}
    serialized = serializer.serialize(empty_list_to_serialize)
    expected_shortened_list_element = "<DBInstances/>"
    assert expected_shortened_list_element in serialized["body"]


class TestXFormedAttributePicker:
    picker = XFormedAttributePicker()

    def test_missing_attribute(self):
        obj = dict()
        ctx = AttributePickerContext(obj, "Attribute", None)
        value = self.picker(ctx)
        assert value is None

    def test_serialization_key(self):
        shape_map = {
            "Foo": {
                "type": "structure",
                "members": {
                    "Baz": {"shape": "StringType", "locationName": "other"},
                },
            },
            "StringType": {"type": "string"},
        }
        resolver = ShapeResolver(shape_map)
        shape = resolver.resolve_shape_ref(
            {"shape": "StringType", "locationName": "other"}
        )
        assert shape
        obj = {"other": "found me"}
        ctx = AttributePickerContext(obj, "StringType", shape)
        value = self.picker(ctx)
        assert value == "found me"

    def test_short_key(self):
        class Role:
            id = "unique-identifier"

        ctx = AttributePickerContext(Role(), "RoleId", None)
        value = self.picker(ctx)
        assert value == "unique-identifier"

    def test_transformed_key(self):
        class DBInstance:
            db_instance_class = "t2.medium"

        ctx = AttributePickerContext(DBInstance(), "DBInstanceClass", None)
        value = self.picker(ctx)
        assert value == "t2.medium"

    def test_untransformed_key(self):
        obj = {"PascalCasedAttr": True}
        ctx = AttributePickerContext(obj, "PascalCasedAttr", None)
        value = self.picker(ctx)
        assert value is True

    def test_key_path_traversal(self):
        child = {"Child": True}
        parent = {"Parent": child}
        ctx = AttributePickerContext(parent, "Parent.Child", None)
        value = self.picker(ctx)
        assert value is True

    def test_explicit_key_alias(self):
        class DBInstance:
            class Meta:
                serialization_aliases = {"DBInstanceClass": "db_instance_klass"}

            db_instance_klass = "t2.medium"

        ctx = AttributePickerContext(DBInstance(), "DBInstanceClass", None)
        value = self.picker(ctx)
        assert value == "t2.medium"


class TestResponseAttributeTransformers:
    def test_never_return(self):
        assert never_return(None) is None
        assert never_return(True) is None
        assert never_return(False) is None
        assert never_return("Test") is None

    def test_return_if_not_empty(self):
        assert return_if_not_empty([]) is None
        assert return_if_not_empty(None) is None
        assert return_if_not_empty("Test") == "Test"
        assert return_if_not_empty({}) is None
        assert return_if_not_empty("") is None
        assert return_if_not_empty({"key": "value"}) == {"key": "value"}
        assert return_if_not_empty([0, 1, 2]) == [0, 1, 2]

    def test_url_encode(self):
        assert url_encode(None) is None
        assert url_encode("Test") == "Test"
        assert url_encode("Test String") == "Test%20String"
