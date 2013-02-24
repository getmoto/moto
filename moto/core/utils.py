import inspect
from urlparse import parse_qs


def headers_to_dict(headers):
    result = {}
    for index, header in enumerate(headers.split("\r\n")):
        if not header:
            continue
        if index:
            # Parsing headers
            key, value = header.split(":", 1)
            result[key.strip()] = value.strip()
        else:
            # Parsing method and path
            path_and_querystring = header.split(" /")[1]
            if '?' in path_and_querystring:
                querystring = path_and_querystring.split("?")[1]
            else:
                querystring = path_and_querystring
            queryset_dict = parse_qs(querystring)
            result.update(queryset_dict)
    return result


def camelcase_to_underscores(argument):
    ''' Converts a camelcase param like theNewAttribute to the equivalent
    python underscore variable like the_new_attribute'''
    result = ''
    prev_char_title = True
    for char in argument:
        if char.istitle() and not prev_char_title:
            # Only add underscore if char is capital, not first letter, and prev
            # char wasn't capital
            result += "_"
        prev_char_title = char.istitle()
        if not char.isspace():  # Only add non-whitespace
            result += char.lower()
    return result


def method_names_from_class(clazz):
    return [x[0] for x in inspect.getmembers(clazz, predicate=inspect.ismethod)]
