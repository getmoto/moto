from collections import namedtuple

from botocore.utils import merge_dicts

from collections import OrderedDict

FilterDef = namedtuple(
    "FilterDef",
    [
        # A list of object attributes to check against the filter values.
        # Set to None if filter is not yet implemented in `moto`.
        "attrs_to_check",
        # Description of the filter, e.g. 'Object Identifiers'.
        # Used in filter error messaging.
        "description",
    ],
)


def get_object_value(obj, attr):
    """Retrieves an arbitrary attribute value from an object.

    Nested attributes can be specified using dot notation,
    e.g. 'parent.child'.

    :param object obj:
        A valid Python object.
    :param str attr:
        The attribute name of the value to retrieve from the object.
    :returns:
        The attribute value, if it exists, or None.
    :rtype:
        any
    """
    keys = attr.split(".")
    val = obj
    for key in keys:
        if hasattr(val, key):
            val = getattr(val, key)
        else:
            return None
    return val


def merge_filters(filters_to_update, filters_to_merge):
    """Given two groups of filters, merge the second into the first.

    List values are appended instead of overwritten:

    >>> merge_filters({'filter-name': ['value1']}, {'filter-name':['value2']})
    >>> {'filter-name': ['value1', 'value2']}

    :param filters_to_update:
        The filters to update.
    :type filters_to_update:
        dict[str, list] or None
    :param filters_to_merge:
        The filters to merge.
    :type filters_to_merge:
        dict[str, list] or None
    :returns:
        The updated filters.
    :rtype:
        dict[str, list]
    """
    if filters_to_update is None:
        filters_to_update = {}
    if filters_to_merge is None:
        filters_to_merge = {}
    merge_dicts(filters_to_update, filters_to_merge, append_lists=True)
    return filters_to_update


def validate_filters(filters, filter_defs):
    """Validates filters against a set of filter definitions.

    Raises standard Python exceptions which should be caught
    and translated to an appropriate AWS/Moto exception higher
    up the call stack.

    :param dict[str, list] filters:
        The filters to validate.
    :param dict[str, FilterDef] filter_defs:
        The filter definitions to validate against.
    :returns: None
    :rtype: None
    :raises KeyError:
        if filter name not found in the filter definitions.
    :raises ValueError:
        if filter values is an empty list.
    :raises NotImplementedError:
        if `moto` does not yet support this filter.
    """
    for filter_name, filter_values in filters.items():
        filter_def = filter_defs.get(filter_name)
        if filter_def is None:
            raise KeyError("Unrecognized filter name: {}".format(filter_name))
        if not filter_values:
            raise ValueError(
                "The list of {} must not be empty.".format(filter_def.description)
            )
        if filter_def.attrs_to_check is None:
            raise NotImplementedError(
                "{} filter has not been implemented in Moto yet.".format(filter_name)
            )


def apply_filter(resources, filters, filter_defs):
    """Apply an arbitrary filter to a group of resources.

    :param dict[str, object] resources:
        A dictionary mapping resource identifiers to resource objects.
    :param dict[str, list] filters:
        The filters to apply.
    :param dict[str, FilterDef] filter_defs:
        The supported filter definitions for the resource type.
    :returns:
        The filtered collection of resources.
    :rtype:
        dict[str, object]
    """
    resources_filtered = OrderedDict()
    for identifier, obj in resources.items():
        matches_filter = False
        for filter_name, filter_values in filters.items():
            filter_def = filter_defs.get(filter_name)
            for attr in filter_def.attrs_to_check:
                if get_object_value(obj, attr) in filter_values:
                    matches_filter = True
                    break
            else:
                matches_filter = False
            if not matches_filter:
                break
        if matches_filter:
            resources_filtered[identifier] = obj
    return resources_filtered
