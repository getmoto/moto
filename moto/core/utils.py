from collections import namedtuple
import inspect
import random
import re
from urlparse import parse_qs

from flask import request


def headers_to_dict(headers):
    if isinstance(headers, dict):
        # If already dict, return
        return headers

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


def get_random_hex(length=8):
    chars = range(10) + ['a', 'b', 'c', 'd', 'e', 'f']
    return ''.join(unicode(random.choice(chars)) for x in range(length))


def get_random_message_id():
    return '{}-{}-{}-{}-{}'.format(get_random_hex(8), get_random_hex(4), get_random_hex(4), get_random_hex(4), get_random_hex(12))


def convert_regex_to_flask_path(url_path):
    """
    Converts a regex matching url to one that can be used with flask
    """
    for token in ["$"]:
        url_path = url_path.replace(token, "")

    def caller(reg):
        match_name, match_pattern = reg.groups()
        return '<regex("{0}"):{1}>'.format(match_pattern, match_name)

    url_path = re.sub("\(\?P<(.*?)>(.*?)\)", caller, url_path)
    return url_path


class convert_flask_to_httpretty_response(object):
    def __init__(self, callback):
        self.callback = callback

    @property
    def __name__(self):
        # For instance methods, use class and method names. Otherwise
        # use module and method name
        if inspect.ismethod(self.callback):
            outer = self.callback.im_class.__name__
        else:
            outer = self.callback.__module__
        return "{}.{}".format(outer, self.callback.__name__)

    def __call__(self, args=None, **kwargs):
        hostname = request.host_url
        method = request.method
        path = request.path
        query = request.query_string

        # Mimic the HTTPretty URIInfo class
        URI = namedtuple('URI', 'hostname method path query')
        uri = URI(hostname, method, path, query)

        body = request.data or query
        headers = dict(request.headers)
        result = self.callback(uri, body, headers)
        if isinstance(result, basestring):
            # result is just the response
            return result
        else:
            # result is a responce, headers tuple
            response, headers = result
            status = headers.pop('status', None)
            return response, status, headers
