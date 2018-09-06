from __future__ import absolute_import, print_function, division, unicode_literals

import _io
import inspect
import json as json_module
import logging
import re
import six

from collections import namedtuple, Sequence, Sized
from functools import update_wrapper
from cookies import Cookies
from botocore.httpsession import URLLib3Session
from requests.exceptions import ConnectionError
from requests.sessions import REDIRECT_STATI
from requests.utils import cookiejar_from_dict
from urllib3.response import HTTPResponse
from botocore.awsrequest import AWSResponse

if six.PY2:
    from urlparse import urlparse, parse_qsl, urlsplit, urlunsplit
    from urllib import quote
else:
    from urllib.parse import urlparse, parse_qsl, urlsplit, urlunsplit, quote

if six.PY2:
    try:
        from six import cStringIO as BufferIO
    except ImportError:
        from six import StringIO as BufferIO
else:
    from io import BytesIO as BufferIO

try:
    from unittest import mock as std_mock
except ImportError:
    import mock as std_mock

try:
    Pattern = re._pattern_type
except AttributeError:
    # Python 3.7
    Pattern = re.Pattern

UNSET = object()

Call = namedtuple("Call", ["request", "response"])

_real_send = URLLib3Session.send

_wrapper_template = """\
def wrapper%(signature)s:
    with responses:
        return func%(funcargs)s
"""

logger = logging.getLogger("responses")


def _is_string(s):
    return isinstance(s, six.string_types)


def _has_unicode(s):
    return any(ord(char) > 128 for char in s)


def _clean_unicode(url):
    # Clean up domain names, which use punycode to handle unicode chars
    urllist = list(urlsplit(url))
    netloc = urllist[1]
    if _has_unicode(netloc):
        domains = netloc.split(".")
        for i, d in enumerate(domains):
            if _has_unicode(d):
                d = "xn--" + d.encode("punycode").decode("ascii")
                domains[i] = d
        urllist[1] = ".".join(domains)
        url = urlunsplit(urllist)

    # Clean up path/query/params, which use url-encoding to handle unicode chars
    if isinstance(url.encode("utf8"), six.string_types):
        url = url.encode("utf8")
    chars = list(url)
    for i, x in enumerate(chars):
        if ord(x) > 128:
            chars[i] = quote(x)

    return "".join(chars)


def _is_redirect(response):
    try:
        # 2.0.0 <= requests <= 2.2
        return response.is_redirect

    except AttributeError:
        # requests > 2.2
        return (
            # use request.sessions conditional
            response.status_code in REDIRECT_STATI and "location" in response.headers
        )


def get_wrapped(func, wrapper_template, evaldict):
    # Preserve the argspec for the wrapped function so that testing
    # tools such as pytest can continue to use their fixture injection.
    if six.PY2:
        args, a, kw, defaults = inspect.getargspec(func)
    else:
        args, a, kw, defaults, kwonlyargs, kwonlydefaults, annotations = inspect.getfullargspec(
            func
        )

    signature = inspect.formatargspec(args, a, kw, defaults)
    is_bound_method = hasattr(func, "__self__")
    if is_bound_method:
        args = args[1:]  # Omit 'self'
    callargs = inspect.formatargspec(args, a, kw, None)

    ctx = {"signature": signature, "funcargs": callargs}
    six.exec_(wrapper_template % ctx, evaldict)

    wrapper = evaldict["wrapper"]

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


def _ensure_url_default_path(url):
    if _is_string(url):
        url_parts = list(urlsplit(url))
        if url_parts[2] == "":
            url_parts[2] = "/"
        url = urlunsplit(url_parts)
    return url


def _handle_body(body):
    if isinstance(body, six.text_type):
        body = body.encode("utf-8")
    if isinstance(body, _io.BufferedReader):
        return body

    return BufferIO(body)


_unspecified = object()


class BaseResponse(object):
    content_type = None
    headers = None

    stream = False

    def __init__(self, method, url, match_querystring=_unspecified):
        self.method = method
        # ensure the url has a default path set if the url is a string
        self.url = _ensure_url_default_path(url)
        self.match_querystring = self._should_match_querystring(match_querystring)
        self.call_count = 0

    def __eq__(self, other):
        if not isinstance(other, BaseResponse):
            return False

        if self.method != other.method:
            return False

        # Can't simply do a equality check on the objects directly here since __eq__ isn't
        # implemented for regex. It might seem to work as regex is using a cache to return
        # the same regex instances, but it doesn't in all cases.
        self_url = self.url.pattern if isinstance(self.url, Pattern) else self.url
        other_url = other.url.pattern if isinstance(other.url, Pattern) else other.url

        return self_url == other_url

    def __ne__(self, other):
        return not self.__eq__(other)

    def _url_matches_strict(self, url, other):
        url_parsed = urlparse(url)
        other_parsed = urlparse(other)

        if url_parsed[:3] != other_parsed[:3]:
            return False

        url_qsl = sorted(parse_qsl(url_parsed.query))
        other_qsl = sorted(parse_qsl(other_parsed.query))

        if len(url_qsl) != len(other_qsl):
            return False

        for (a_k, a_v), (b_k, b_v) in zip(url_qsl, other_qsl):
            if a_k != b_k:
                return False

            if a_v != b_v:
                return False

        return True

    def _should_match_querystring(self, match_querystring_argument):
        if match_querystring_argument is not _unspecified:
            return match_querystring_argument

        if isinstance(self.url, Pattern):
            # the old default from <= 0.9.0
            return False

        return bool(urlparse(self.url).query)

    def _url_matches(self, url, other, match_querystring=False):
        if _is_string(url):
            if _has_unicode(url):
                url = _clean_unicode(url)
                if not isinstance(other, six.text_type):
                    other = other.encode("ascii").decode("utf8")
            if match_querystring:
                return self._url_matches_strict(url, other)

            else:
                url_without_qs = url.split("?", 1)[0]
                other_without_qs = other.split("?", 1)[0]
                return url_without_qs == other_without_qs

        elif isinstance(url, Pattern) and url.match(other):
            return True

        else:
            return False

    def get_headers(self):
        headers = {}
        if self.content_type is not None:
            headers["Content-Type"] = self.content_type
        if self.headers:
            headers.update(self.headers)
        return headers

    def get_response(self, request):
        raise NotImplementedError

    def matches(self, request):
        if request.method != self.method:
            return False

        if not self._url_matches(self.url, request.url, self.match_querystring):
            return False

        return True


class Response(BaseResponse):
    def __init__(
        self,
        method,
        url,
        body="",
        json=None,
        status=200,
        headers=None,
        stream=False,
        content_type=UNSET,
        **kwargs
    ):
        # if we were passed a `json` argument,
        # override the body and content_type
        if json is not None:
            assert not body
            body = json_module.dumps(json)
            if content_type is UNSET:
                content_type = "application/json"

        if content_type is UNSET:
            content_type = "text/plain"

        # body must be bytes
        if isinstance(body, six.text_type):
            body = body.encode("utf-8")

        self.body = body
        self.status = status
        self.headers = headers
        self.stream = stream
        self.content_type = content_type
        super(Response, self).__init__(method, url, **kwargs)

    def get_response(self, request):
        if self.body and isinstance(self.body, Exception):
            raise self.body

        headers = self.get_headers()
        status = self.status
        body = _handle_body(self.body)

        return HTTPResponse(
            status=status,
            reason=six.moves.http_client.responses.get(status),
            body=body,
            headers=headers,
            preload_content=False,
        )


class CallbackResponse(BaseResponse):
    def __init__(
        self, method, url, callback, stream=False, content_type="text/plain", **kwargs
    ):
        self.callback = callback
        self.stream = stream
        self.content_type = content_type
        super(CallbackResponse, self).__init__(method, url, **kwargs)

    def get_response(self, request):
        headers = self.get_headers()

        result = self.callback(request)
        if isinstance(result, Exception):
            raise result

        status, r_headers, body = result
        body = _handle_body(body)
        headers.update(r_headers)

        return HTTPResponse(
            status=status,
            reason=six.moves.http_client.responses.get(status),
            body=body,
            headers=headers,
            preload_content=False,
        )


class RequestsMock(object):
    DELETE = "DELETE"
    GET = "GET"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"
    POST = "POST"
    PUT = "PUT"
    response_callback = None

    def __init__(
        self,
        assert_all_requests_are_fired=True,
        response_callback=None,
        passthru_prefixes=(),
        target="botocore.httpsession.URLLib3Session.send",
    ):
        self._calls = CallList()
        self.reset()
        self.assert_all_requests_are_fired = assert_all_requests_are_fired
        self.response_callback = response_callback
        self.passthru_prefixes = tuple(passthru_prefixes)
        self.target = target

    def reset(self):
        self._matches = []
        self._calls.reset()

    def add(
        self,
        method=None,  # method or ``Response``
        url=None,
        body="",
        adding_headers=None,
        *args,
        **kwargs
    ):
        """
        A basic request:
        >>> responses.add(responses.GET, 'http://example.com')
        You can also directly pass an object which implements the
        ``BaseResponse`` interface:
        >>> responses.add(Response(...))
        A JSON payload:
        >>> responses.add(
        >>>     method='GET',
        >>>     url='http://example.com',
        >>>     json={'foo': 'bar'},
        >>> )
        Custom headers:
        >>> responses.add(
        >>>     method='GET',
        >>>     url='http://example.com',
        >>>     headers={'X-Header': 'foo'},
        >>> )
        Strict query string matching:
        >>> responses.add(
        >>>     method='GET',
        >>>     url='http://example.com?foo=bar',
        >>>     match_querystring=True
        >>> )
        """
        if isinstance(method, BaseResponse):
            self._matches.append(method)
            return

        if adding_headers is not None:
            kwargs.setdefault("headers", adding_headers)

        self._matches.append(Response(method=method, url=url, body=body, **kwargs))

    def add_passthru(self, prefix):
        """
        Register a URL prefix to passthru any non-matching mock requests to.
        For example, to allow any request to 'https://example.com', but require
        mocks for the remainder, you would add the prefix as so:
        >>> responses.add_passthru('https://example.com')
        """
        if _has_unicode(prefix):
            prefix = _clean_unicode(prefix)
        self.passthru_prefixes += (prefix,)

    def remove(self, method_or_response=None, url=None):
        """
        Removes a response previously added using ``add()``, identified
        either by a response object inheriting ``BaseResponse`` or
        ``method`` and ``url``. Removes all matching responses.
        >>> response.add(responses.GET, 'http://example.org')
        >>> response.remove(responses.GET, 'http://example.org')
        """
        if isinstance(method_or_response, BaseResponse):
            response = method_or_response
        else:
            response = BaseResponse(method=method_or_response, url=url)

        while response in self._matches:
            self._matches.remove(response)

    def replace(self, method_or_response=None, url=None, body="", *args, **kwargs):
        """
        Replaces a response previously added using ``add()``. The signature
        is identical to ``add()``. The response is identified using ``method``
        and ``url``, and the first matching response is replaced.
        >>> responses.add(responses.GET, 'http://example.org', json={'data': 1})
        >>> responses.replace(responses.GET, 'http://example.org', json={'data': 2})
        """
        if isinstance(method_or_response, BaseResponse):
            response = method_or_response
        else:
            response = Response(method=method_or_response, url=url, body=body, **kwargs)

        index = self._matches.index(response)
        self._matches[index] = response

    def add_callback(
        self, method, url, callback, match_querystring=False, content_type="text/plain"
    ):
        # ensure the url has a default path set if the url is a string
        # url = _ensure_url_default_path(url, match_querystring)

        self._matches.append(
            CallbackResponse(
                url=url,
                method=method,
                callback=callback,
                content_type=content_type,
                match_querystring=match_querystring,
            )
        )

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
        evaldict = {"responses": self, "func": func}
        return get_wrapped(func, _wrapper_template, evaldict)

    def _find_match(self, request):
        found = None
        found_match = None
        for i, match in enumerate(self._matches):
            if match.matches(request):
                if found is None:
                    found = i
                    found_match = match
                else:
                    # Multiple matches found.  Remove & return the first match.
                    return self._matches.pop(found)

        return found_match

    def _on_request(self, adapter, request, **kwargs):
        match = self._find_match(request)
        resp_callback = self.response_callback

        if match is None:
            if request.url.startswith(self.passthru_prefixes):
                logger.info("request.allowed-passthru", extra={"url": request.url})
                return _real_send(adapter, request, **kwargs)

            error_msg = "Connection refused: {0} {1}".format(
                request.method, request.url
            )
            response = ConnectionError(error_msg)
            response.request = request

            self._calls.add(request, response)
            response = resp_callback(response) if resp_callback else response
            raise response

        try:
            response = self._build_response(request, match.get_response(request))
        except Exception as response:
            match.call_count += 1
            self._calls.add(request, response)
            response = resp_callback(response) if resp_callback else response
            raise

        if not match.stream:
            response.content  # NOQA

        try:
            resp_cookies = Cookies.from_request(response.headers["set-cookie"])
            response.cookies = cookiejar_from_dict(
                dict((v.name, v.value) for _, v in resp_cookies.items())
            )
        except (KeyError, TypeError):
            pass

        response = resp_callback(response) if resp_callback else response
        match.call_count += 1
        self._calls.add(request, response)
        return response

    def _build_response(self, req, resp):
        """

        :param req:
        :type: botocore.awsrequest.AWSRequest
        :param resp:
        :type: urllib3.response.HTTPResponse
        :return:
        :rtype: botocore.awsrequest.AWSResponse
        """
        return AWSResponse(
            req.url,
            resp.status,
            resp.headers,
            resp,
        )

    def start(self):
        def unbound_on_send(adapter, request, *a, **kwargs):
            return self._on_request(adapter, request, *a, **kwargs)

        self._patcher = std_mock.patch(target=self.target, new=unbound_on_send)
        self._patcher.start()

    def stop(self, allow_assert=True):
        self._patcher.stop()
        if not self.assert_all_requests_are_fired:
            return

        if not allow_assert:
            return

        not_called = [m for m in self._matches if m.call_count == 0]
        if not_called:
            raise AssertionError(
                "Not all requests have been executed {0!r}".format(
                    [(match.method, match.url) for match in not_called]
                )
            )


# expose default mock namespace
mock = _default_mock = RequestsMock(assert_all_requests_are_fired=False)
__all__ = ["CallbackResponse", "Response", "RequestsMock"]
for __attr in (a for a in dir(_default_mock) if not a.startswith("_")):
    __all__.append(__attr)
    globals()[__attr] = getattr(_default_mock, __attr)
