from __future__ import (
    absolute_import, print_function, division, unicode_literals
)

import inspect
import json as json_module
import re
import six

from collections import namedtuple, Sequence, Sized
from functools import update_wrapper
from cookies import Cookies
from requests.adapters import HTTPAdapter
from requests.utils import cookiejar_from_dict
from requests.exceptions import ConnectionError
from requests.sessions import REDIRECT_STATI

try:
    from requests.packages.urllib3.response import HTTPResponse
except ImportError:
    from urllib3.response import HTTPResponse

if six.PY2:
    from urlparse import urlparse, parse_qsl
else:
    from urllib.parse import urlparse, parse_qsl

if six.PY2:
    try:
        from six import cStringIO as BufferIO
    except ImportError:
        from six import StringIO as BufferIO
else:
    from io import BytesIO as BufferIO


Call = namedtuple('Call', ['request', 'response'])

_wrapper_template = """\
def wrapper%(signature)s:
    with responses:
        return func%(funcargs)s
"""


def _is_string(s):
    return isinstance(s, (six.string_types, six.text_type))


def _is_redirect(response):
    try:
        # 2.0.0 <= requests <= 2.2
        return response.is_redirect
    except AttributeError:
        # requests > 2.2
        return (
            # use request.sessions conditional
            response.status_code in REDIRECT_STATI and
            'location' in response.headers
        )


def get_wrapped(func, wrapper_template, evaldict):
    # Preserve the argspec for the wrapped function so that testing
    # tools such as pytest can continue to use their fixture injection.
    args, a, kw, defaults = inspect.getargspec(func)

    signature = inspect.formatargspec(args, a, kw, defaults)
    is_bound_method = hasattr(func, '__self__')
    if is_bound_method:
        args = args[1:]     # Omit 'self'
    callargs = inspect.formatargspec(args, a, kw, None)

    ctx = {'signature': signature, 'funcargs': callargs}
    six.exec_(wrapper_template % ctx, evaldict)

    wrapper = evaldict['wrapper']

    update_wrapper(wrapper, func)
    if is_bound_method:
        wrapper = wrapper.__get__(func.__self__, type(func.__self__))
    return wrapper


class CallList(Sequence, Sized):

    def __init__(self):
        self._calls = []

    def __iter__(self):
        return iter(self._calls)

    def __len__(self):
        return len(self._calls)

    def __getitem__(self, idx):
        return self._calls[idx]

    def add(self, request, response):
        self._calls.append(Call(request, response))

    def reset(self):
        self._calls = []


def _ensure_url_default_path(url, match_querystring):
    if _is_string(url) and url.count('/') == 2:
        if match_querystring:
            return url.replace('?', '/?', 1)
        else:
            return url + '/'
    return url


class RequestsMock(object):
    DELETE = 'DELETE'
    GET = 'GET'
    HEAD = 'HEAD'
    OPTIONS = 'OPTIONS'
    PATCH = 'PATCH'
    POST = 'POST'
    PUT = 'PUT'

    def __init__(self, assert_all_requests_are_fired=True, pass_through=True):
        self._calls = CallList()
        self.reset()
        self.assert_all_requests_are_fired = assert_all_requests_are_fired
        self.pass_through = pass_through
        self.original_send = HTTPAdapter.send

    def reset(self):
        self._urls = []
        self._calls.reset()

    def add(self, method, url, body='', match_querystring=False,
            status=200, adding_headers=None, stream=False,
            content_type='text/plain', json=None):

        # if we were passed a `json` argument,
        # override the body and content_type
        if json is not None:
            body = json_module.dumps(json)
            content_type = 'application/json'

        # ensure the url has a default path set if the url is a string
        url = _ensure_url_default_path(url, match_querystring)

        # body must be bytes
        if isinstance(body, six.text_type):
            body = body.encode('utf-8')

        self._urls.append({
            'url': url,
            'method': method,
            'body': body,
            'content_type': content_type,
            'match_querystring': match_querystring,
            'status': status,
            'adding_headers': adding_headers,
            'stream': stream,
        })

    def add_callback(self, method, url, callback, match_querystring=False,
                     content_type='text/plain'):
        # ensure the url has a default path set if the url is a string
        # url = _ensure_url_default_path(url, match_querystring)

        self._urls.append({
            'url': url,
            'method': method,
            'callback': callback,
            'content_type': content_type,
            'match_querystring': match_querystring,
        })

    @property
    def calls(self):
        return self._calls

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        success = type is None
        self.stop(allow_assert=success)
        self.reset()
        return success

    def activate(self, func):
        evaldict = {'responses': self, 'func': func}
        return get_wrapped(func, _wrapper_template, evaldict)

    def _find_match(self, request):
        for match in self._urls:
            if request.method != match['method']:
                continue

            if not self._has_url_match(match, request.url):
                continue

            break
        else:
            return None
        if self.assert_all_requests_are_fired:
            # for each found match remove the url from the stack
            self._urls.remove(match)
        return match

    def _has_url_match(self, match, request_url):
        url = match['url']

        if not match['match_querystring']:
            request_url = request_url.split('?', 1)[0]

        if _is_string(url):
            if match['match_querystring']:
                return self._has_strict_url_match(url, request_url)
            else:
                return url == request_url
        elif isinstance(url, re._pattern_type) and url.match(request_url):
            return True
        else:
            return False

    def _has_strict_url_match(self, url, other):
        url_parsed = urlparse(url)
        other_parsed = urlparse(other)

        if url_parsed[:3] != other_parsed[:3]:
            return False

        url_qsl = sorted(parse_qsl(url_parsed.query))
        other_qsl = sorted(parse_qsl(other_parsed.query))
        return url_qsl == other_qsl

    def _on_request(self, adapter, request, **kwargs):
        match = self._find_match(request)
        # TODO(dcramer): find the correct class for this
        if match is None:
            if self.pass_through:
                return self.original_send(adapter, request, **kwargs)

            error_msg = 'Connection refused: {0} {1}'.format(request.method,
                                                             request.url)
            response = ConnectionError(error_msg)
            response.request = request

            self._calls.add(request, response)
            raise response

        if 'body' in match and isinstance(match['body'], Exception):
            self._calls.add(request, match['body'])
            raise match['body']

        headers = {}
        if match['content_type'] is not None:
            headers['Content-Type'] = match['content_type']

        if 'callback' in match:  # use callback
            status, r_headers, body = match['callback'](request)
            if isinstance(body, six.text_type):
                body = body.encode('utf-8')
            body = BufferIO(body)
            headers.update(r_headers)

        elif 'body' in match:
            if match['adding_headers']:
                headers.update(match['adding_headers'])
            status = match['status']
            body = BufferIO(match['body'])

        response = HTTPResponse(
            status=status,
            reason=six.moves.http_client.responses[status],
            body=body,
            headers=headers,
            preload_content=False,
            # Need to not decode_content to mimic requests
            decode_content=False,
        )

        response = adapter.build_response(request, response)
        if not match.get('stream'):
            response.content  # NOQA

        try:
            resp_cookies = Cookies.from_request(response.headers['set-cookie'])
            response.cookies = cookiejar_from_dict(dict(
                (v.name, v.value)
                for _, v
                in resp_cookies.items()
            ))
        except (KeyError, TypeError):
            pass

        self._calls.add(request, response)

        return response

    def start(self):
        try:
            from unittest import mock
        except ImportError:
            import mock

        def unbound_on_send(adapter, request, *a, **kwargs):
            return self._on_request(adapter, request, *a, **kwargs)
        self._patcher1 = mock.patch('botocore.vendored.requests.adapters.HTTPAdapter.send',
                                    unbound_on_send)
        self._patcher1.start()
        self._patcher2 = mock.patch('requests.adapters.HTTPAdapter.send',
                                    unbound_on_send)
        self._patcher2.start()

    def stop(self, allow_assert=True):
        self._patcher1.stop()
        self._patcher2.stop()
        if allow_assert and self.assert_all_requests_are_fired and self._urls:
            raise AssertionError(
                'Not all requests have been executed {0!r}'.format(
                    [(url['method'], url['url']) for url in self._urls]))


# expose default mock namespace
mock = _default_mock = RequestsMock(assert_all_requests_are_fired=False, pass_through=False)
__all__ = []
for __attr in (a for a in dir(_default_mock) if not a.startswith('_')):
    __all__.append(__attr)
    globals()[__attr] = getattr(_default_mock, __attr)
