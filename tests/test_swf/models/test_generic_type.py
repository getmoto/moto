from moto.swf.models import GenericType
import sure  # noqa


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
    _type.to_short_dict().should.equal({"name": "test-foo", "version": "v1.0"})


def test_type_medium_dict_representation():
    _type = FooType("test-foo", "v1.0")
    _type.to_medium_dict()["fooType"].should.equal(_type.to_short_dict())
    _type.to_medium_dict()["status"].should.equal("REGISTERED")
    _type.to_medium_dict().should.contain("creationDate")
    _type.to_medium_dict().should_not.contain("deprecationDate")
    _type.to_medium_dict().should_not.contain("description")

    _type.description = "foo bar"
    _type.to_medium_dict()["description"].should.equal("foo bar")

    _type.status = "DEPRECATED"
    _type.to_medium_dict().should.contain("deprecationDate")


def test_type_full_dict_representation():
    _type = FooType("test-foo", "v1.0")
    _type.to_full_dict()["typeInfo"].should.equal(_type.to_medium_dict())
    _type.to_full_dict()["configuration"].should.equal({})

    _type.task_list = "foo"
    _type.to_full_dict()["configuration"][
        "defaultTaskList"].should.equal({"name": "foo"})

    _type.just_an_example_timeout = "60"
    _type.to_full_dict()["configuration"][
        "justAnExampleTimeout"].should.equal("60")

    _type.non_whitelisted_property = "34"
    keys = _type.to_full_dict()["configuration"].keys()
    sorted(keys).should.equal(["defaultTaskList", "justAnExampleTimeout"])


def test_type_string_representation():
    _type = FooType("test-foo", "v1.0")
    str(_type).should.equal(
        "FooType(name: test-foo, version: v1.0, status: REGISTERED)")
