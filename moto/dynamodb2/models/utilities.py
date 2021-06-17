import re


def bytesize(val):
    return len(val.encode("utf-8"))


def attribute_is_list(attr):
    """
    Checks if attribute denotes a list, and returns the name of the list and the given list index if so
    :param attr: attr or attr[index]
    :return: attr, index or None
    """
    list_index_update = re.match("(.+)\\[([0-9]+)\\]", attr)
    if list_index_update:
        attr = list_index_update.group(1)
    return attr, list_index_update.group(2) if list_index_update else None
