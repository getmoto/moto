from collections.abc import Iterable, Mapping
from uuid import UUID

from sure import assertion


@assertion
def containing_item_with_attributes(context, **kwargs):
    contains = False
    if kwargs and isinstance(context.obj, Iterable):
        for item in context.obj:
            if not isinstance(item, dict):
                continue
            for k, v in kwargs.items():
                if k not in item or item[k] != v:
                    break
            else:
                contains = True
    if context.negative:
        assert not contains, f"{context.obj} contains matching item {kwargs}"
    else:
        assert contains, f"{context.obj} does not contain matching item {kwargs}"
    return True


@assertion
def match_dict(context, dict_value):
    assert isinstance(dict_value, Mapping), f"Invalid match target value: {dict_value}"
    assert isinstance(
        context.obj, Mapping
    ), f"Expected dict like object, but got: {context.obj}"

    for k, v in dict_value.items():
        assert k in context.obj, f"No such key '{k}' in {context.obj}"
        context.obj[k].should.equal(v)
    return True


@assertion
def match_uuid4(context):
    try:
        uuid_obj = UUID(context.obj, version=4)
    except ValueError:
        return False
    return str(uuid_obj) == context.obj
