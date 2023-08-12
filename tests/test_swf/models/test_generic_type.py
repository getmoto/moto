from moto.swf.models import GenericType


# Tests for GenericType (ActivityType, WorkflowType)
class FooType(GenericType):
    @property
    def kind(self):
        return "foo"

    @property
    def _configuration_keys(self):
        return ["justAnExampleTimeout"]


def test_type_short_dict_representation():
    _type = FooType("test-foo", "v1.0")
    assert _type.to_short_dict() == {"name": "test-foo", "version": "v1.0"}


def test_type_medium_dict_representation():
    _type = FooType("test-foo", "v1.0")
    assert _type.to_medium_dict()["fooType"] == _type.to_short_dict()
    assert _type.to_medium_dict()["status"] == "REGISTERED"
    assert "creationDate" in _type.to_medium_dict()
    assert "deprecationDate" not in _type.to_medium_dict()
    assert "description" not in _type.to_medium_dict()

    _type.description = "foo bar"
    assert _type.to_medium_dict()["description"] == "foo bar"

    _type.status = "DEPRECATED"
    assert "deprecationDate" in _type.to_medium_dict()


def test_type_full_dict_representation():
    _type = FooType("test-foo", "v1.0")
    assert _type.to_full_dict()["typeInfo"] == _type.to_medium_dict()
    assert not _type.to_full_dict()["configuration"]

    _type.task_list = "foo"
    assert _type.to_full_dict()["configuration"]["defaultTaskList"] == {"name": "foo"}

    _type.just_an_example_timeout = "60"
    assert _type.to_full_dict()["configuration"]["justAnExampleTimeout"] == "60"

    _type.non_whitelisted_property = "34"
    keys = _type.to_full_dict()["configuration"].keys()
    assert sorted(keys) == ["defaultTaskList", "justAnExampleTimeout"]


def test_type_string_representation():
    _type = FooType("test-foo", "v1.0")
    assert str(_type) == "FooType(name: test-foo, version: v1.0, status: REGISTERED)"
