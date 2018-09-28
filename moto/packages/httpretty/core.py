# #!/usr/bin/env python
# -*- coding: utf-8 -*-
# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
from __future__ import unicode_literals

import re
import codecs
import inspect
import socket
import functools
import itertools
import warnings
import logging
import traceback
import json
import contextlib


from .compat import (
    PY3,
    StringIO,
    text_type,
    BaseClass,
    BaseHTTPRequestHandler,
    quote,
    quote_plus,
    urlunsplit,
    urlsplit,
    parse_qs,
    unquote,
    unquote_utf8,
    ClassTypes,
    basestring
)
from .http import (
    STATUSES,
    HttpBaseClass,
    parse_requestline,
    last_requestline,
)

from .utils import (
    utf8,
    decode_utf8,
)

from .errors import HTTPrettyError, UnmockedError

from datetime import datetime
from datetime import timedelta
from errno import EAGAIN

# Some versions of python internally shadowed the
# SocketType variable incorrectly https://bugs.python.org/issue20386
BAD_SOCKET_SHADOW = socket.socket != socket.SocketType

old_socket = socket.socket
old_create_connection = socket.create_connection
old_gethostbyname = socket.gethostbyname
old_gethostname = socket.gethostname
old_getaddrinfo = socket.getaddrinfo
old_socksocket = None
old_ssl_wrap_socket = None
old_sslwrap_simple = None
old_sslsocket = None
old_sslcontext_wrap_socket = None

if PY3:  # pragma: no cover
    basestring = (bytes, str)
try:  # pragma: no cover
    import socks
    old_socksocket = socks.socksocket
except ImportError:
    socks = None

try:  # pragma: no cover
    import ssl
    old_ssl_wrap_socket = ssl.wrap_socket
    if not PY3:
        old_sslwrap_simple = ssl.sslwrap_simple
    old_sslsocket = ssl.SSLSocket
    try:
        old_sslcontext_wrap_socket = ssl.SSLContext.wrap_socket
    except AttributeError:
        pass
except ImportError:  # pragma: no cover
    ssl = None

try:  # pragma: no cover
    from requests.packages.urllib3.contrib.pyopenssl import inject_into_urllib3, extract_from_urllib3
    pyopenssl_override = True
except:
    pyopenssl_override = False


DEFAULT_HTTP_PORTS = frozenset([80])
POTENTIAL_HTTP_PORTS = set(DEFAULT_HTTP_PORTS)
DEFAULT_HTTPS_PORTS = frozenset([443])
POTENTIAL_HTTPS_PORTS = set(DEFAULT_HTTPS_PORTS)


class HTTPrettyRequest(BaseHTTPRequestHandler, BaseClass):
    """Represents a HTTP request. It takes a valid multi-line, `\r\n`
    separated string with HTTP headers and parse them out using the
    internal `parse_request` method.

    It also replaces the `rfile` and `wfile` attributes with StringIO
    instances so that we garantee that it won't make any I/O, neighter
    for writing nor reading.

    It has some convenience attributes:

    `headers` -> a mimetype object that can be cast into a dictionary,
    contains all the request headers

    `method` -> the HTTP method used in this request

    `querystring` -> a dictionary containing lists with the
    attributes. Please notice that if you need a single value from a
    query string you will need to get it manually like:

    ```python
    >>> request.querystring
    {'name': ['Gabriel Falcao']}
    >>> print request.querystring['name'][0]
    ```

    `parsed_body` -> a dictionary containing parsed request body or
    None if HTTPrettyRequest doesn't know how to parse it.  It
    currently supports parsing body data that was sent under the
    `content-type` headers values: 'application/json' or
    'application/x-www-form-urlencoded'
    """

    def __init__(self, headers, body=''):
        # first of all, lets make sure that if headers or body are
        # unicode strings, it must be converted into a utf-8 encoded
        # byte string
        self.raw_headers = utf8(headers.strip())
        self.body = utf8(body)

        # Now let's concatenate the headers with the body, and create
        # `rfile` based on it
        self.rfile = StringIO(b'\r\n\r\n'.join([self.raw_headers, self.body]))
        self.wfile = StringIO()  # Creating `wfile` as an empty
        # StringIO, just to avoid any real
        # I/O calls

        # parsing the request line preemptively
        self.raw_requestline = self.rfile.readline()

        # initiating the error attributes with None
        self.error_code = None
        self.error_message = None

        # Parse the request based on the attributes above
        if not self.parse_request():
            return

        # making the HTTP method string available as the command
        self.method = self.command

        # Now 2 convenient attributes for the HTTPretty API:

        # `querystring` holds a dictionary with the parsed query string
        try:
            self.path = self.path.encode('iso-8859-1')
        except UnicodeDecodeError:
            pass

        self.path = decode_utf8(self.path)

        qstring = self.path.split("?", 1)[-1]
        self.querystring = self.parse_querystring(qstring)

        # And the body will be attempted to be parsed as
        # `application/json` or `application/x-www-form-urlencoded`
        self.parsed_body = self.parse_request_body(self.body)

    def __str__(self):
        return '<HTTPrettyRequest("{0}", total_headers={1}, body_length={2})>'.format(
            self.headers.get('content-type', ''),
            len(self.headers),
            len(self.body),
        )

    def parse_querystring(self, qs):
        expanded = unquote_utf8(qs)
        parsed = parse_qs(expanded)
        result = {}
        for k in parsed:
            result[k] = list(map(decode_utf8, parsed[k]))

        return result

    def parse_request_body(self, body):
        """ Attempt to parse the post based on the content-type passed. Return the regular body if not """

        PARSING_FUNCTIONS = {
            'application/json': json.loads,
            'text/json': json.loads,
            'application/x-www-form-urlencoded': self.parse_querystring,
        }
        FALLBACK_FUNCTION = lambda x: x

        content_type = self.headers.get('content-type', '')

        do_parse = PARSING_FUNCTIONS.get(content_type, FALLBACK_FUNCTION)
        try:
            body = decode_utf8(body)
            return do_parse(body)
        except:
            return body


class EmptyRequestHeaders(dict):
    pass


class HTTPrettyRequestEmpty(object):
    body = ''
    headers = EmptyRequestHeaders()


class FakeSockFile(StringIO):

    def close(self):
        self.socket.close()
        StringIO.close(self)


class FakeSSLSocket(object):

    def __init__(self, sock, *args, **kw):
        self._httpretty_sock = sock

    def __getattr__(self, attr):
        return getattr(self._httpretty_sock, attr)


class fakesock(object):

    class socket(object):
        _entry = None
        debuglevel = 0
        _sent_data = []

        def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM,
                     protocol=0):
            self.truesock = (old_socket(family, type, protocol)
                             if httpretty.allow_net_connect
                             else None)
            self._closed = True
            self.fd = FakeSockFile()
            self.fd.socket = self
            self.timeout = socket._GLOBAL_DEFAULT_TIMEOUT
            self._sock = self
            self.is_http = False
            self._bufsize = 1024

        def getpeercert(self, *a, **kw):
            now = datetime.now()
            shift = now + timedelta(days=30 * 12)
            return {
                'notAfter': shift.strftime('%b %d %H:%M:%S GMT'),
                'subjectAltName': (
                    ('DNS', '*.%s' % self._host),
                    ('DNS', self._host),
                    ('DNS', '*'),
                ),
                'subject': (
                    (
                        ('organizationName', '*.%s' % self._host),
                    ),
                    (
                        ('organizationalUnitName',
                         'Domain Control Validated'),
                    ),
                    (
                        ('commonName', '*.%s' % self._host),
                    ),
                ),
            }

        def ssl(self, sock, *args, **kw):
            return sock

        def setsockopt(self, level, optname, value):
            if self.truesock:
                self.truesock.setsockopt(level, optname, value)

        def connect(self, address):
            self._closed = False

            try:
                self._address = (self._host, self._port) = address
            except ValueError:
                # We get here when the address is just a string pointing to a
                # unix socket path/file
                #
                # See issue #206
                self.is_http = False
            else:
                self.is_http = self._port in POTENTIAL_HTTP_PORTS | POTENTIAL_HTTPS_PORTS

            if not self.is_http:
                if self.truesock:
                    self.truesock.connect(self._address)
                else:
                    raise UnmockedError()

        def close(self):
            if not (self.is_http and self._closed):
                if self.truesock:
                    self.truesock.close()
            self._closed = True

        def makefile(self, mode='r', bufsize=-1):
            """Returns this fake socket's own StringIO buffer.

            If there is an entry associated with the socket, the file
            descriptor gets filled in with the entry data before being
            returned.
            """
            self._mode = mode
            self._bufsize = bufsize

            if self._entry:
                self._entry.fill_filekind(self.fd)

            return self.fd

        def real_sendall(self, data, *args, **kw):
            """Sends data to the remote server. This method is called
            when HTTPretty identifies that someone is trying to send
            non-http data.

            The received bytes are written in this socket's StringIO
            buffer so that HTTPretty can return it accordingly when
            necessary.
            """

            if not self.truesock:
                raise UnmockedError()

            if not self.is_http:
                return self.truesock.sendall(data, *args, **kw)

            self.truesock.connect(self._address)

            self.truesock.setblocking(1)
            self.truesock.sendall(data, *args, **kw)

            should_continue = True
            while should_continue:
                try:
                    received = self.truesock.recv(self._bufsize)
                    self.fd.write(received)
                    should_continue = len(received) == self._bufsize

                except socket.error as e:
                    if e.errno == EAGAIN:
                        continue
                    break

            self.fd.seek(0)

        def sendall(self, data, *args, **kw):
            self._sent_data.append(data)
            self.fd = FakeSockFile()
            self.fd.socket = self
            try:
                requestline, _ = data.split(b'\r\n', 1)
                method, path, version = parse_requestline(
                    decode_utf8(requestline))
                is_parsing_headers = True
            except ValueError:
                is_parsing_headers = False

                if not self._entry:
                    # If the previous request wasn't mocked, don't mock the
                    # subsequent sending of data
                    return self.real_sendall(data, *args, **kw)

            self.fd.seek(0)

            if not is_parsing_headers:
                if len(self._sent_data) > 1:
                    headers = utf8(last_requestline(self._sent_data))
                    meta = self._entry.request.headers
                    body = utf8(self._sent_data[-1])
                    if meta.get('transfer-encoding', '') == 'chunked':
                        if not body.isdigit() and body != b'\r\n' and body != b'0\r\n\r\n':
                            self._entry.request.body += body
                    else:
                        self._entry.request.body += body

                    httpretty.historify_request(headers, body, False)
                    return

            # path might come with
            s = urlsplit(path)
            POTENTIAL_HTTP_PORTS.add(int(s.port or 80))
            headers, body = list(map(utf8, data.split(b'\r\n\r\n', 1)))

            request = httpretty.historify_request(headers, body)

            info = URIInfo(hostname=self._host, port=self._port,
                           path=s.path,
                           query=s.query,
                           last_request=request)

            matcher, entries = httpretty.match_uriinfo(info)

            if not entries:
                self._entry = None
                self.real_sendall(data)
                return

            self._entry = matcher.get_next_entry(method, info, request)

        def debug(self, truesock_func, *a, **kw):
            if self.is_http:
                frame = inspect.stack()[0][0]
                lines = list(map(utf8, traceback.format_stack(frame)))

                message = [
                    "HTTPretty intercepted and unexpected socket method call.",
                    ("Please open an issue at "
                     "'https://github.com/gabrielfalcao/HTTPretty/issues'"),
                    "And paste the following traceback:\n",
                    "".join(decode_utf8(lines)),
                ]
                raise RuntimeError("\n".join(message))
            if not self.truesock:
                raise UnmockedError()
            return getattr(self.truesock, truesock_func)(*a, **kw)

        def settimeout(self, new_timeout):
            self.timeout = new_timeout

        def send(self, *args, **kwargs):
            return self.debug('send', *args, **kwargs)

        def sendto(self, *args, **kwargs):
            return self.debug('sendto', *args, **kwargs)

        def recvfrom_into(self, *args, **kwargs):
            return self.debug('recvfrom_into', *args, **kwargs)

        def recv_into(self, *args, **kwargs):
            return self.debug('recv_into', *args, **kwargs)

        def recvfrom(self, *args, **kwargs):
            return self.debug('recvfrom', *args, **kwargs)

        def recv(self, *args, **kwargs):
            return self.debug('recv', *args, **kwargs)

        def __getattr__(self, name):
            if not self.truesock:
                raise UnmockedError()
            return getattr(self.truesock, name)


def fake_wrap_socket(s, *args, **kw):
    return s


def create_fake_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    s = fakesock.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
        s.settimeout(timeout)
    if source_address:
        s.bind(source_address)
    s.connect(address)
    return s


def fake_gethostbyname(host):
    return '127.0.0.1'


def fake_gethostname():
    return 'localhost'


def fake_getaddrinfo(
        host, port, family=None, socktype=None, proto=None, flags=None):
    return [(2, 1, 6, '', (host, port))]


class Entry(BaseClass):

    def __init__(self, method, uri, body,
                 adding_headers=None,
                 forcing_headers=None,
                 status=200,
                 streaming=False,
                 **headers):

        self.method = method
        self.uri = uri
        self.info = None
        self.request = None

        self.body_is_callable = False
        if hasattr(body, "__call__"):
            self.callable_body = body
            self.body = None
            self.body_is_callable = True
        elif isinstance(body, text_type):
            self.body = utf8(body)
        else:
            self.body = body

        self.streaming = streaming
        if not streaming and not self.body_is_callable:
            self.body_length = len(self.body or '')
        else:
            self.body_length = 0

        self.adding_headers = adding_headers or {}
        self.forcing_headers = forcing_headers or {}
        self.status = int(status)

        for k, v in headers.items():
            name = "-".join(k.split("_")).title()
            self.adding_headers[name] = v

        self.validate()

    def validate(self):
        content_length_keys = 'Content-Length', 'content-length'
        for key in content_length_keys:
            got = self.adding_headers.get(
                key, self.forcing_headers.get(key, None))

            if got is None:
                continue

            try:
                igot = int(got)
            except ValueError:
                warnings.warn(
                    'HTTPretty got to register the Content-Length header '
                    'with "%r" which is not a number' % got,
                )

            if igot > self.body_length:
                raise HTTPrettyError(
                    'HTTPretty got inconsistent parameters. The header '
                    'Content-Length you registered expects size "%d" but '
                    'the body you registered for that has actually length '
                    '"%d".' % (
                        igot, self.body_length,
                    )
                )

    def __str__(self):
        return r'<Entry %s %s getting %d>' % (
            self.method, self.uri, self.status)

    def normalize_headers(self, headers):
        new = {}
        for k in headers:
            new_k = '-'.join([s.lower() for s in k.split('-')])
            new[new_k] = headers[k]

        return new

    def fill_filekind(self, fk):
        now = datetime.utcnow()

        headers = {
            'status': self.status,
            'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'server': 'Python/HTTPretty',
            'connection': 'close',
        }

        if self.forcing_headers:
            headers = self.forcing_headers

        if self.adding_headers:
            headers.update(self.normalize_headers(self.adding_headers))

        headers = self.normalize_headers(headers)
        status = headers.get('status', self.status)
        if self.body_is_callable:
            status, headers, self.body = self.callable_body(
                self.request, self.info.full_url(), headers)
            headers = self.normalize_headers(headers)
            if self.request.method != "HEAD":
                headers.update({
                    'content-length': len(self.body)
                })

        string_list = [
            'HTTP/1.1 %d %s' % (status, STATUSES[status]),
        ]

        if 'date' in headers:
            string_list.append('date: %s' % headers.pop('date'))

        if not self.forcing_headers:
            content_type = headers.pop('content-type',
                                       'text/plain; charset=utf-8')

            content_length = headers.pop('content-length', self.body_length)

            string_list.append('content-type: %s' % content_type)
            if not self.streaming:
                string_list.append('content-length: %s' % content_length)

            string_list.append('server: %s' % headers.pop('server'))

        for k, v in headers.items():
            string_list.append(
                '{0}: {1}'.format(k, v),
            )

        for item in string_list:
            fk.write(utf8(item) + b'\n')

        fk.write(b'\r\n')

        if self.streaming:
            self.body, body = itertools.tee(self.body)
            for chunk in body:
                fk.write(utf8(chunk))
        else:
            fk.write(utf8(self.body))

        fk.seek(0)


def url_fix(s, charset='utf-8'):
    scheme, netloc, path, querystring, fragment = urlsplit(s)
    path = quote(path, b'/%')
    querystring = quote_plus(querystring, b':&=')
    return urlunsplit((scheme, netloc, path, querystring, fragment))


class URIInfo(BaseClass):

    def __init__(self,
                 username='',
                 password='',
                 hostname='',
                 port=80,
                 path='/',
                 query='',
                 fragment='',
                 scheme='',
                 last_request=None):

        self.username = username or ''
        self.password = password or ''
        self.hostname = hostname or ''

        if port:
            port = int(port)

        elif scheme == 'https':
            port = 443

        self.port = port or 80
        self.path = path or ''
        self.query = query or ''
        if scheme:
            self.scheme = scheme
        elif self.port in POTENTIAL_HTTPS_PORTS:
            self.scheme = 'https'
        else:
            self.scheme = 'http'
        self.fragment = fragment or ''
        self.last_request = last_request

    def __str__(self):
        attrs = (
            'username',
            'password',
            'hostname',
            'port',
            'path',
        )
        fmt = ", ".join(['%s="%s"' % (k, getattr(self, k, '')) for k in attrs])
        return r'<httpretty.URIInfo(%s)>' % fmt

    def __hash__(self):
        return hash(text_type(self))

    def __eq__(self, other):
        self_tuple = (
            self.port,
            decode_utf8(self.hostname.lower()),
            url_fix(decode_utf8(self.path)),
        )
        other_tuple = (
            other.port,
            decode_utf8(other.hostname.lower()),
            url_fix(decode_utf8(other.path)),
        )
        return self_tuple == other_tuple

    def full_url(self, use_querystring=True):
        credentials = ""
        if self.password:
            credentials = "{0}:{1}@".format(
                self.username, self.password)

        query = ""
        if use_querystring and self.query:
            query = "?{0}".format(decode_utf8(self.query))

        result = "{scheme}://{credentials}{domain}{path}{query}".format(
            scheme=self.scheme,
            credentials=credentials,
            domain=self.get_full_domain(),
            path=decode_utf8(self.path),
            query=query
        )
        return result

    def get_full_domain(self):
        hostname = decode_utf8(self.hostname)
        # Port 80/443 should not be appended to the url
        if self.port not in DEFAULT_HTTP_PORTS | DEFAULT_HTTPS_PORTS:
            return ":".join([hostname, str(self.port)])

        return hostname

    @classmethod
    def from_uri(cls, uri, entry):
        result = urlsplit(uri)
        if result.scheme == 'https':
            POTENTIAL_HTTPS_PORTS.add(int(result.port or 443))
        else:
            POTENTIAL_HTTP_PORTS.add(int(result.port or 80))
        return cls(result.username,
                   result.password,
                   result.hostname,
                   result.port,
                   result.path,
                   result.query,
                   result.fragment,
                   result.scheme,
                   entry)


class URIMatcher(object):
    regex = None
    info = None

    def __init__(self, uri, entries, match_querystring=False):
        self._match_querystring = match_querystring
        if type(uri).__name__ in ('SRE_Pattern', 'Pattern'):
            self.regex = uri
            result = urlsplit(uri.pattern)
            if result.scheme == 'https':
                POTENTIAL_HTTPS_PORTS.add(int(result.port or 443))
            else:
                POTENTIAL_HTTP_PORTS.add(int(result.port or 80))
        else:
            self.info = URIInfo.from_uri(uri, entries)

        self.entries = entries

        # hash of current_entry pointers, per method.
        self.current_entries = {}

    def matches(self, info):
        if self.info:
            return self.info == info
        else:
            return self.regex.search(info.full_url(
                use_querystring=self._match_querystring))

    def __str__(self):
        wrap = 'URLMatcher({0})'
        if self.info:
            return wrap.format(text_type(self.info))
        else:
            return wrap.format(self.regex.pattern)

    def get_next_entry(self, method, info, request):
        """Cycle through available responses, but only once.
        Any subsequent requests will receive the last response"""

        if method not in self.current_entries:
            self.current_entries[method] = 0

        # restrict selection to entries that match the requested method
        entries_for_method = [e for e in self.entries if e.method == method]

        if self.current_entries[method] >= len(entries_for_method):
            self.current_entries[method] = -1

        if not self.entries or not entries_for_method:
            raise ValueError('I have no entries for method %s: %s'
                             % (method, self))

        entry = entries_for_method[self.current_entries[method]]
        if self.current_entries[method] != -1:
            self.current_entries[method] += 1

        # Attach more info to the entry
        # So the callback can be more clever about what to do
        # This does also fix the case where the callback
        # would be handed a compiled regex as uri instead of the
        # real uri
        entry.info = info
        entry.request = request
        return entry

    def __hash__(self):
        return hash(text_type(self))

    def __eq__(self, other):
        return text_type(self) == text_type(other)


class httpretty(HttpBaseClass):
    """The URI registration class"""
    _entries = {}
    latest_requests = []

    last_request = HTTPrettyRequestEmpty()
    _is_enabled = False
    allow_net_connect = True

    @classmethod
    def match_uriinfo(cls, info):
        for matcher, value in cls._entries.items():
            if matcher.matches(info):
                return (matcher, info)

        return (None, [])

    @classmethod
    @contextlib.contextmanager
    def record(cls, filename, indentation=4, encoding='utf-8'):
        try:
            import urllib3
        except ImportError:
            raise RuntimeError(
                'HTTPretty requires urllib3 installed for recording actual requests.')

        http = urllib3.PoolManager()

        cls.enable()
        calls = []

        def record_request(request, uri, headers):
            cls.disable()

            response = http.request(request.method, uri)
            calls.append({
                'request': {
                    'uri': uri,
                    'method': request.method,
                    'headers': dict(request.headers),
                    'body': decode_utf8(request.body),
                    'querystring': request.querystring
                },
                'response': {
                    'status': response.status,
                    'body': decode_utf8(response.data),
                    'headers': dict(response.headers)
                }
            })
            cls.enable()
            return response.status, response.headers, response.data

        for method in cls.METHODS:
            cls.register_uri(method, re.compile(
                r'.*', re.M), body=record_request)

        yield
        cls.disable()
        with codecs.open(filename, 'w', encoding) as f:
            f.write(json.dumps(calls, indent=indentation))

    @classmethod
    @contextlib.contextmanager
    def playback(cls, origin):
        cls.enable()

        data = json.loads(open(origin).read())
        for item in data:
            uri = item['request']['uri']
            method = item['request']['method']
            cls.register_uri(method, uri, body=item['response'][
                             'body'], forcing_headers=item['response']['headers'])

        yield
        cls.disable()

    @classmethod
    def reset(cls):
        POTENTIAL_HTTP_PORTS.intersection_update(DEFAULT_HTTP_PORTS)
        POTENTIAL_HTTPS_PORTS.intersection_update(DEFAULT_HTTPS_PORTS)
        cls._entries.clear()
        cls.latest_requests = []
        cls.last_request = HTTPrettyRequestEmpty()

    @classmethod
    def historify_request(cls, headers, body='', append=True):
        request = HTTPrettyRequest(headers, body)
        cls.last_request = request
        if append or not cls.latest_requests:
            cls.latest_requests.append(request)
        else:
            cls.latest_requests[-1] = request
        return request

    @classmethod
    def register_uri(cls, method, uri, body='HTTPretty :)',
                     adding_headers=None,
                     forcing_headers=None,
                     status=200,
                     responses=None, match_querystring=False,
                     **headers):

        uri_is_string = isinstance(uri, basestring)

        if uri_is_string and re.search(r'^\w+://[^/]+[.]\w{2,}$', uri):
            uri += '/'

        if isinstance(responses, list) and len(responses) > 0:
            for response in responses:
                response.uri = uri
                response.method = method
            entries_for_this_uri = responses
        else:
            headers[str('body')] = body
            headers[str('adding_headers')] = adding_headers
            headers[str('forcing_headers')] = forcing_headers
            headers[str('status')] = status

            entries_for_this_uri = [
                cls.Response(method=method, uri=uri, **headers),
            ]

        matcher = URIMatcher(uri, entries_for_this_uri,
                             match_querystring)
        if matcher in cls._entries:
            matcher.entries.extend(cls._entries[matcher])
            del cls._entries[matcher]

        cls._entries[matcher] = entries_for_this_uri

    def __str__(self):
        return '<HTTPretty with %d URI entries>' % len(self._entries)

    @classmethod
    def Response(cls, body, method=None, uri=None, adding_headers=None, forcing_headers=None,
                 status=200, streaming=False, **headers):

        headers[str('body')] = body
        headers[str('adding_headers')] = adding_headers
        headers[str('forcing_headers')] = forcing_headers
        headers[str('status')] = int(status)
        headers[str('streaming')] = streaming
        return Entry(method, uri, **headers)

    @classmethod
    def disable(cls):
        cls._is_enabled = False
        socket.socket = old_socket
        if not BAD_SOCKET_SHADOW:
            socket.SocketType = old_socket
        socket._socketobject = old_socket

        socket.create_connection = old_create_connection
        socket.gethostname = old_gethostname
        socket.gethostbyname = old_gethostbyname
        socket.getaddrinfo = old_getaddrinfo

        socket.__dict__['socket'] = old_socket
        socket.__dict__['_socketobject'] = old_socket
        if not BAD_SOCKET_SHADOW:
            socket.__dict__['SocketType'] = old_socket

        socket.__dict__['create_connection'] = old_create_connection
        socket.__dict__['gethostname'] = old_gethostname
        socket.__dict__['gethostbyname'] = old_gethostbyname
        socket.__dict__['getaddrinfo'] = old_getaddrinfo

        if socks:
            socks.socksocket = old_socksocket
            socks.__dict__['socksocket'] = old_socksocket

        if ssl:
            ssl.wrap_socket = old_ssl_wrap_socket
            ssl.SSLSocket = old_sslsocket
            try:
                ssl.SSLContext.wrap_socket = old_sslcontext_wrap_socket
            except AttributeError:
                pass
            ssl.__dict__['wrap_socket'] = old_ssl_wrap_socket
            ssl.__dict__['SSLSocket'] = old_sslsocket

            if not PY3:
                ssl.sslwrap_simple = old_sslwrap_simple
                ssl.__dict__['sslwrap_simple'] = old_sslwrap_simple

        if pyopenssl_override:
            inject_into_urllib3()

    @classmethod
    def is_enabled(cls):
        return cls._is_enabled

    @classmethod
    def enable(cls):
        cls._is_enabled = True

        socket.socket = fakesock.socket
        socket._socketobject = fakesock.socket
        if not BAD_SOCKET_SHADOW:
            socket.SocketType = fakesock.socket

        socket.create_connection = create_fake_connection
        socket.gethostname = fake_gethostname
        socket.gethostbyname = fake_gethostbyname
        socket.getaddrinfo = fake_getaddrinfo

        socket.__dict__['socket'] = fakesock.socket
        socket.__dict__['_socketobject'] = fakesock.socket
        if not BAD_SOCKET_SHADOW:
            socket.__dict__['SocketType'] = fakesock.socket

        socket.__dict__['create_connection'] = create_fake_connection
        socket.__dict__['gethostname'] = fake_gethostname
        socket.__dict__['gethostbyname'] = fake_gethostbyname
        socket.__dict__['getaddrinfo'] = fake_getaddrinfo

        if socks:
            socks.socksocket = fakesock.socket
            socks.__dict__['socksocket'] = fakesock.socket

        if ssl:
            ssl.wrap_socket = fake_wrap_socket
            ssl.SSLSocket = FakeSSLSocket

            try:
                def fake_sslcontext_wrap_socket(cls, *args, **kwargs):
                    return fake_wrap_socket(*args, **kwargs)

                ssl.SSLContext.wrap_socket = fake_sslcontext_wrap_socket
            except AttributeError:
                pass

            ssl.__dict__['wrap_socket'] = fake_wrap_socket
            ssl.__dict__['SSLSocket'] = FakeSSLSocket

            if not PY3:
                ssl.sslwrap_simple = fake_wrap_socket
                ssl.__dict__['sslwrap_simple'] = fake_wrap_socket

        if pyopenssl_override:
            extract_from_urllib3()


def httprettified(test):
    "A decorator tests that use HTTPretty"
    def decorate_class(klass):
        for attr in dir(klass):
            if not attr.startswith('test_'):
                continue

            attr_value = getattr(klass, attr)
            if not hasattr(attr_value, "__call__"):
                continue

            setattr(klass, attr, decorate_callable(attr_value))
        return klass

    def decorate_callable(test):
        @functools.wraps(test)
        def wrapper(*args, **kw):
            httpretty.reset()
            httpretty.enable()
            try:
                return test(*args, **kw)
            finally:
                httpretty.disable()
        return wrapper

    if isinstance(test, ClassTypes):
        return decorate_class(test)
    return decorate_callable(test)
