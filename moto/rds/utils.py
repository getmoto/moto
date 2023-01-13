from collections import namedtuple

from botocore.utils import merge_dicts

from collections import OrderedDict
import datetime
import re

SECONDS_IN_ONE_DAY = 24 * 60 * 60
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
            raise KeyError(f"Unrecognized filter name: {filter_name}")
        if not filter_values:
            raise ValueError(f"The list of {filter_def.description} must not be empty.")
        if filter_def.attrs_to_check is None:
            raise NotImplementedError(
                f"{filter_name} filter has not been implemented in Moto yet."
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


def get_start_date_end_date(base_date, window):
    """Gets the start date and end date given DDD:HH24:MM-DDD:HH24:MM.

    :param base_date:
        type datetime
    :param window:
        DDD:HH24:MM-DDD:HH24:MM
    :returns:
        Start and End Date in datetime format
    :rtype:
        tuple
    """
    days = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7}
    start = datetime.datetime.strptime(
        base_date + " " + window[4:9], "%d/%m/%y %H:%M"
    ) + datetime.timedelta(days=days[window[0:3]])
    end = datetime.datetime.strptime(
        base_date + " " + window[14::], "%d/%m/%y %H:%M"
    ) + datetime.timedelta(days=days[window[10:13]])
    return start, end


def get_start_date_end_date_from_time(base_date, window):
    """Gets the start date and end date given HH24:MM-HH24:MM.

    :param base_date:
        type datetime
    :param window:
        HH24:MM-HH24:MM
    :returns:
        Start and End Date in datetime format
        along with flag for spills over a day
        This is useful when determine time overlaps
    :rtype:
        tuple
    """
    times = window.split("-")
    spillover = False
    start = datetime.datetime.strptime(base_date + " " + times[0], "%d/%m/%y %H:%M")
    end = datetime.datetime.strptime(base_date + " " + times[1], "%d/%m/%y %H:%M")
    if end < start:
        end += datetime.timedelta(days=1)
        spillover = True
    return start, end, spillover


def get_overlap_between_two_date_ranges(
    start_time_1, end_time_1, start_time_2, end_time_2
):
    """Determines overlap between 2 date ranges.

    :param start_time_1:
        type datetime
    :param start_time_2:
        type datetime
    :param end_time_1:
        type datetime
    :param end_time_2:
        type datetime
    :returns:
        overlap in seconds
    :rtype:
        int
    """
    latest_start = max(start_time_1, start_time_2)
    earliest_end = min(end_time_1, end_time_2)
    delta = earliest_end - latest_start
    overlap = (delta.days * SECONDS_IN_ONE_DAY) + delta.seconds
    return overlap


def valid_preferred_maintenance_window(maintenance_window, backup_window):
    """Determines validity of preferred_maintenance_window

    :param maintenance_windown:
        type DDD:HH24:MM-DDD:HH24:MM
    :param backup_window:
        type HH24:MM-HH24:MM
    :returns:
        message
    :rtype:
        str
    """
    MINUTES_30 = 1800
    HOURS_24 = 86400
    base_date = datetime.datetime.now().strftime("%d/%m/%y")
    try:
        p = re.compile(
            "([a-z]{3}):([0-9]{2}):([0-9]{2})-([a-z]{3}):([0-9]{2}):([0-9]{2})"
        )
        if len(maintenance_window) != 19 or re.search(p, maintenance_window) is None:
            return f"Invalid maintenance window format: {maintenance_window}. Should be specified as a range ddd:hh24:mi-ddd:hh24:mi (24H Clock UTC). Example: Sun:23:45-Mon:00:15"
        if backup_window:
            (
                backup_window_start,
                backup_window_end,
                backup_spill,
            ) = get_start_date_end_date_from_time(base_date, backup_window)
            (
                maintenance_window_start,
                maintenance_window_end,
                maintenance_spill,
            ) = get_start_date_end_date_from_time(
                base_date, maintenance_window[4:10] + maintenance_window[14::]
            )
            if (
                get_overlap_between_two_date_ranges(
                    backup_window_start,
                    backup_window_end,
                    maintenance_window_start,
                    maintenance_window_end,
                )
                >= 0
            ):
                return "The backup window and maintenance window must not overlap."

            # Due to spill overs, adjust the windows
            elif maintenance_spill:
                backup_window_start += datetime.timedelta(days=1)
                backup_window_end += datetime.timedelta(days=1)
            elif backup_spill:
                maintenance_window_start += datetime.timedelta(days=1)
                maintenance_window_end += datetime.timedelta(days=1)

            # If spills, rerun overlap test with adjusted windows
            if maintenance_spill or backup_spill:
                if (
                    get_overlap_between_two_date_ranges(
                        backup_window_start,
                        backup_window_end,
                        maintenance_window_start,
                        maintenance_window_end,
                    )
                    >= 0
                ):
                    return "The backup window and maintenance window must not overlap."

        maintenance_window_start, maintenance_window_end = get_start_date_end_date(
            base_date, maintenance_window
        )
        delta = maintenance_window_end - maintenance_window_start
        delta_seconds = delta.seconds + (delta.days * SECONDS_IN_ONE_DAY)
        if delta_seconds >= MINUTES_30 and delta_seconds <= HOURS_24:
            return
        elif delta_seconds >= 0 and delta_seconds <= MINUTES_30:
            return "The maintenance window must be at least 30 minutes."
        else:
            return "Maintenance window must be less than 24 hours."
    except Exception:
        return f"Invalid day:hour:minute value: {maintenance_window}"
