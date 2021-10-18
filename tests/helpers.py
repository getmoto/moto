from collections.abc import Iterable
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
