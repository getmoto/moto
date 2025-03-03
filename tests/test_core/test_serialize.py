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

from botocore.model import ServiceModel
from xmltodict import parse

from moto.core.serialize import QuerySerializer


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
