from __future__ import unicode_literals

import datetime
import inspect
import random
import re
import six


def camelcase_to_underscores(argument):
    ''' Converts a camelcase param like theNewAttribute to the equivalent
    python underscore variable like the_new_attribute'''
    result = ''
    prev_char_title = True
    for index, char in enumerate(argument):
        try:
            next_char_title = argument[index + 1].istitle()
        except IndexError:
            next_char_title = True

        upper_to_lower = char.istitle() and not next_char_title
        lower_to_upper = char.istitle() and not prev_char_title

        if index and (upper_to_lower or lower_to_upper):
            # Only add underscore if char is capital, not first letter, and next
            # char is not capital
            result += "_"
        prev_char_title = char.istitle()
        if not char.isspace():  # Only add non-whitespace
            result += char.lower()
    return result


def underscores_to_camelcase(argument):
    ''' Converts a camelcase param like the_new_attribute to the equivalent
    camelcase version like theNewAttribute. Note that the first letter is
    NOT capitalized by this function '''
    result = ''
    previous_was_underscore = False
    for char in argument:
        if char != '_':
            if previous_was_underscore:
                result += char.upper()
            else:
                result += char
        previous_was_underscore = char == '_'
    return result


def method_names_from_class(clazz):
    # On Python 2, methods are different from functions, and the `inspect`
    # predicates distinguish between them. On Python 3, methods are just
    # regular functions, and `inspect.ismethod` doesn't work, so we have to
    # use `inspect.isfunction` instead
    if six.PY2:
        predicate = inspect.ismethod
    else:
        predicate = inspect.isfunction
    return [x[0] for x in inspect.getmembers(clazz, predicate=predicate)]


def get_random_hex(length=8):
    chars = list(range(10)) + ['a', 'b', 'c', 'd', 'e', 'f']
    return ''.join(six.text_type(random.choice(chars)) for x in range(length))


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

    if url_path.endswith("/?"):
        # Flask does own handling of trailing slashes
        url_path = url_path.rstrip("/?")
    return url_path


class convert_httpretty_response(object):

    def __init__(self, callback):
        self.callback = callback

    @property
    def __name__(self):
        # For instance methods, use class and method names. Otherwise
        # use module and method name
        if inspect.ismethod(self.callback):
            outer = self.callback.__self__.__class__.__name__
        else:
            outer = self.callback.__module__
        return "{0}.{1}".format(outer, self.callback.__name__)

    def __call__(self, request, url, headers, **kwargs):
        result = self.callback(request, url, headers)
        status, headers, response = result
        if 'server' not in headers:
            headers["server"] = "amazon.com"
        return status, headers, response


class convert_flask_to_httpretty_response(object):

    def __init__(self, callback):
        self.callback = callback

    @property
    def __name__(self):
        # For instance methods, use class and method names. Otherwise
        # use module and method name
        if inspect.ismethod(self.callback):
            outer = self.callback.__self__.__class__.__name__
        else:
            outer = self.callback.__module__
        return "{0}.{1}".format(outer, self.callback.__name__)

    def __call__(self, args=None, **kwargs):
        from flask import request, Response

        result = self.callback(request, request.url, {})
        # result is a status, headers, response tuple
        if len(result) == 3:
            status, headers, content = result
        else:
            status, headers, content = 200, {}, result

        response = Response(response=content, status=status, headers=headers)
        if request.method == "HEAD" and 'content-length' in headers:
            response.headers['Content-Length'] = headers['content-length']
        return response


class convert_flask_to_responses_response(object):

    def __init__(self, callback):
        self.callback = callback

    @property
    def __name__(self):
        # For instance methods, use class and method names. Otherwise
        # use module and method name
        if inspect.ismethod(self.callback):
            outer = self.callback.__self__.__class__.__name__
        else:
            outer = self.callback.__module__
        return "{0}.{1}".format(outer, self.callback.__name__)

    def __call__(self, request, *args, **kwargs):
        for key, val in request.headers.items():
            if isinstance(val, six.binary_type):
                request.headers[key] = val.decode("utf-8")

        result = self.callback(request, request.url, request.headers)
        status, headers, response = result
        return status, headers, response


def iso_8601_datetime_with_milliseconds(datetime):
    return datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'


def iso_8601_datetime_without_milliseconds(datetime):
    return datetime.strftime("%Y-%m-%dT%H:%M:%S") + 'Z'


RFC1123 = '%a, %d %b %Y %H:%M:%S GMT'


def rfc_1123_datetime(datetime):
    return datetime.strftime(RFC1123)


def str_to_rfc_1123_datetime(str):
    return datetime.datetime.strptime(str, RFC1123)


def unix_time(dt=None):
    dt = dt or datetime.datetime.utcnow()
    epoch = datetime.datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return (delta.days * 86400) + (delta.seconds + (delta.microseconds / 1e6))


def unix_time_millis(dt=None):
    return unix_time(dt) * 1000.0
