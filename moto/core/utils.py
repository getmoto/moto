import inspect
import random
import re

from flask import request


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
    return '{0}-{1}-{2}-{3}-{4}'.format(get_random_hex(8), get_random_hex(4), get_random_hex(4), get_random_hex(4), get_random_hex(12))


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
        return "{0}.{1}".format(outer, self.callback.__name__)

    def __call__(self, args=None, **kwargs):
        headers = dict(request.headers)
        result = self.callback(request, request.url, headers)
        # result is a status, headers, response tuple
        status, headers, response = result
        return response, status, headers


def iso_8601_datetime(datetime):
    return datetime.strftime("%Y-%m-%dT%H:%M:%SZ")


def rfc_1123_datetime(datetime):
    RFC1123 = '%a, %d %b %Y %H:%M:%S GMT'
    return datetime.strftime(RFC1123)
