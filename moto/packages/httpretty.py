# #!/usr/bin/env python
# -*- coding: utf-8 -*-
# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2012>  Gabriel Falcão <gabriel@nacaolivre.org>
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
version = '0.5.8'

import re
import inspect
import socket
import functools
import itertools
import warnings
import logging
import sys
import traceback
import types

PY3 = sys.version_info[0] == 3
if PY3:
    text_type = str
    byte_type = bytes
    import io
    StringIO = io.StringIO

    class Py3kObject(object):
        def __repr__(self):
            return self.__str__()
else:
    text_type = unicode
    byte_type = str
    import StringIO
    StringIO = StringIO.StringIO


class Py3kObject(object):
    def __repr__(self):
        ret = self.__str__()
        if PY3:
            return ret
        else:
            ret.encode('utf-8')

from datetime import datetime
from datetime import timedelta
try:
    from urllib.parse import urlsplit, parse_qs
except ImportError:
    from urlparse import urlsplit, parse_qs

try:
    from http.server import BaseHTTPRequestHandler
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler

old_socket = socket.socket
old_create_connection = socket.create_connection
old_gethostbyname = socket.gethostbyname
old_gethostname = socket.gethostname
old_getaddrinfo = socket.getaddrinfo
old_socksocket = None
old_ssl_wrap_socket = None
old_sslwrap_simple = None
old_sslsocket = None

try:
    import socks
    old_socksocket = socks.socksocket
except ImportError:
    socks = None

try:
    import ssl
    old_ssl_wrap_socket = ssl.wrap_socket
    if not PY3:
        old_sslwrap_simple = ssl.sslwrap_simple
    old_sslsocket = ssl.SSLSocket
except ImportError:
    ssl = None


class HTTPrettyError(Exception):
    pass


def utf8(s):
    if isinstance(s, text_type):
        s = s.encode('utf-8')

    return byte_type(s)


def parse_requestline(s):
    """
    http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5

    >>> parse_requestline('GET / HTTP/1.0')
    ('GET', '/', '1.0')
    >>> parse_requestline('post /testurl htTP/1.1')
    ('POST', '/testurl', '1.1')
    >>> parse_requestline('Im not a RequestLine')
    Traceback (most recent call last):
        ...
    ValueError: Not a Request-Line
    """
    methods = '|'.join(HTTPretty.METHODS)
    m = re.match(r'('+methods+')\s+(.*)\s+HTTP/(1.[0|1])', s, re.I)
    if m:
        return m.group(1).upper(), m.group(2), m.group(3)
    else:
        raise ValueError('Not a Request-Line')


class HTTPrettyRequest(BaseHTTPRequestHandler, Py3kObject):
    def __init__(self, headers, body=''):
        self.body = utf8(body)
        self.raw_headers = utf8(headers)
        self.rfile = StringIO('\r\n\r\n'.join([headers.strip(), body]))
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()
        self.method = self.command
        self.querystring = parse_qs(self.path.split("?", 1)[-1])

    def __str__(self):
        return 'HTTPrettyRequest(headers={0}, body="{1}")'.format(
            self.headers,
            self.body,
        )


class EmptyRequestHeaders(dict):
    pass


class HTTPrettyRequestEmpty(object):
    body = ''
    headers = EmptyRequestHeaders()


class FakeSockFile(StringIO):
    def read(self, amount=None):
        amount = amount or self.len
        new_amount = amount

        if amount > self.len:
            new_amount = self.len - self.tell()

        ret = StringIO.read(self, new_amount)
        return ret


class FakeSSLSocket(object):
    def __init__(self, sock, *args, **kw):
        self._httpretty_sock = sock

    def __getattr__(self, attr):
        if attr == '_httpretty_sock':
            return super(FakeSSLSocket, self).__getattribute__(attr)

        return getattr(self._httpretty_sock, attr)


class fakesock(object):
    class socket(object):
        _entry = None
        debuglevel = 0
        _sent_data = []

        def __init__(self, family, type, protocol=6):
            self.setsockopt(family, type, protocol)
            self.truesock = old_socket(family, type, protocol)
            self._closed = True
            self.fd = FakeSockFile()
            self.timeout = socket._GLOBAL_DEFAULT_TIMEOUT
            self._sock = self

        def getpeercert(self, *a, **kw):
            now = datetime.now()
            shift = now + timedelta(days=30 * 12)
            return {
                'notAfter': shift.strftime('%b %d %H:%M:%S GMT'),
                'subjectAltName': (
                    ('DNS', '*%s' % self._host),
                    ('DNS', self._host),
                    ('DNS', '*'),
                ),
                'subject': (
                    (
                        ('organizationName', u'*.%s' % self._host),
                    ),
                    (
                        ('organizationalUnitName',
                         u'Domain Control Validated'),
                    ),
                    (
                        ('commonName', u'*.%s' % self._host),
                    ),
                ),
            }

        def ssl(self, sock, *args, **kw):
            return sock

        def setsockopt(self, family, type, protocol):
            self.family = family
            self.protocol = protocol
            self.type = type

        def connect(self, address):
            self._address = (self._host, self._port) = address
            self._closed = False

        def close(self):
            if not self._closed:
                self.truesock.close()
            self._closed = True

        def makefile(self, mode='r', bufsize=-1):
            self._mode = mode
            self._bufsize = bufsize

            if self._entry:
                self._entry.fill_filekind(self.fd, self._request)

            return self.fd

        def _true_sendall(self, data, *args, **kw):
            self.truesock.connect(self._address)
            self.truesock.sendall(data, *args, **kw)
            _d = self.truesock.recv(16)
            self.fd.seek(0)
            self.fd.write(_d)
            while _d:
                _d = self.truesock.recv(16)
                self.fd.write(_d)

            self.fd.seek(0)
            self.truesock.close()

        def sendall(self, data, *args, **kw):

            self._sent_data.append(data)
            hostnames = [getattr(i.info, 'hostname', None) for i in HTTPretty._entries.keys()]
            self.fd.seek(0)
            try:
                print("data", data)
                requestline, _ = data.split('\r\n', 1)
                method, path, version = parse_requestline(requestline)
                is_parsing_headers = True
            except ValueError:
                is_parsing_headers = False

                # This need to be reconsidered. URIMatchers with regexs don't
                # have hostnames which can cause this to return even though
                # the regex may have matched
                # if self._host not in hostnames:
                #     return self._true_sendall(data)

            import pdb;pdb.set_trace()
            if not is_parsing_headers:

                if len(self._sent_data) > 1:
                    headers, body = map(utf8, self._sent_data[-2:])

                    method, path, version = parse_requestline(headers)
                    split_url = urlsplit(path)

                    info = URIInfo(hostname=self._host, port=self._port,
                                   path=split_url.path,
                                   query=split_url.query,
                                   method=method)

                    # If we are sending more data to a dynamic response entry,
                    # we need to call the method again.
                    if self._entry and self._entry.dynamic_response:
                        self._entry.body(info, method, body, headers)

                    try:
                        return HTTPretty.historify_request(headers, body, False)
                    except Exception as e:
                        logging.error(traceback.format_exc(e))
                        return self._true_sendall(data, *args, **kw)

            # path might come with
            s = urlsplit(path)

            headers, body = map(utf8, data.split('\r\n\r\n', 1))

            request = HTTPretty.historify_request(headers, body)

            info = URIInfo(hostname=self._host, port=self._port,
                           path=s.path,
                           query=s.query,
                           last_request=request,
                           method=method)

            entries = []

            for matcher, value in HTTPretty._entries.items():
                if matcher.matches(info) and matcher.method == method:
                    entries = value
                    #info = matcher.info
                    break

            if not entries:
                self._true_sendall(data)
                return

            entry = matcher.get_next_entry()
            if entry.method == method:
                self._entry = entry
                self._request = (info, method, body, headers)
            else:
                raise ValueError("No match found for", method, entry.uri)

        def debug(*a, **kw):
            frame = inspect.stack()[0][0]
            lines = map(utf8, traceback.format_stack(frame))

            message = [
                "HTTPretty intercepted and unexpected socket method call.",
                ("Please open an issue at "
                 "'https://github.com/gabrielfalcao/HTTPretty/issues'"),
                "And paste the following traceback:\n",
                "".join(lines),
            ]
            raise RuntimeError("\n".join(message))

        def settimeout(self, new_timeout):
            self.timeout = new_timeout

        sendto = send = recvfrom_into = recv_into = recvfrom = recv = debug


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
    return host


def fake_gethostname():
    return 'localhost'


def fake_getaddrinfo(
    host, port, family=None, socktype=None, proto=None, flags=None):
    return [(2, 1, 6, '', (host, port))]


STATUSES = {
    100: "Continue",
    101: "Switching Protocols",
    102: "Processing",
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    207: "Multi-Status",
    208: "Already Reported",
    226: "IM Used",
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    306: "Switch Proxy",
    307: "Temporary Redirect",
    308: "Permanent Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request a Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Request Entity Too Large",
    414: "Request-URI Too Long",
    415: "Unsupported Media Type",
    416: "Requested Range Not Satisfiable",
    417: "Expectation Failed",
    418: "I'm a teapot",
    420: "Enhance Your Calm",
    422: "Unprocessable Entity",
    423: "Locked",
    424: "Failed Dependency",
    424: "Method Failure",
    425: "Unordered Collection",
    426: "Upgrade Required",
    428: "Precondition Required",
    429: "Too Many Requests",
    431: "Request Header Fields Too Large",
    444: "No Response",
    449: "Retry With",
    450: "Blocked by Windows Parental Controls",
    451: "Unavailable For Legal Reasons",
    451: "Redirect",
    494: "Request Header Too Large",
    495: "Cert Error",
    496: "No Cert",
    497: "HTTP to HTTPS",
    499: "Client Closed Request",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "HTTP Version Not Supported",
    506: "Variant Also Negotiates",
    507: "Insufficient Storage",
    508: "Loop Detected",
    509: "Bandwidth Limit Exceeded",
    510: "Not Extended",
    511: "Network Authentication Required",
    598: "Network read timeout error",
    599: "Network connect timeout error",
}


class Entry(Py3kObject):
    def __init__(self, method, uri, body,
                 adding_headers=None,
                 forcing_headers=None,
                 status=200,
                 streaming=False,
                 **headers):

        self.method = method
        self.uri = uri

        if callable(body):
            self.dynamic_response = True
        else:
            self.dynamic_response = False

        self.body = body
        self.streaming = streaming

        if self.dynamic_response or self.streaming:
            self.body_length = 0
        else:
            self.body_length = len(self.body or '')

        self.adding_headers = adding_headers or {}
        self.forcing_headers = forcing_headers or {}
        self.status = int(status)

        for k, v in headers.items():
            name = "-".join(k.split("_")).capitalize()
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
                    'HTTPretty got to register the Content-Length header ' \
                    'with "%r" which is not a number' % got,
                )

            if igot > self.body_length:
                raise HTTPrettyError(
                    'HTTPretty got inconsistent parameters. The header ' \
                    'Content-Length you registered expects size "%d" but ' \
                    'the body you registered for that has actually length ' \
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
            new_k = '-'.join([s.title() for s in k.split('-')])
            new[new_k] = headers[k]

        return new

    def fill_filekind(self, fk, request):
        req_info, method, req_body, req_headers = request

        now = datetime.utcnow()

        headers = {
            'Status': self.status,
            'Date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'Server': 'Python/HTTPretty',
            'Connection': 'close',
        }

        if self.dynamic_response:
            response = self.body(req_info, method, req_body, req_headers)
            if isinstance(response, basestring):
                body = response
                new_headers = {}
            else:
                body, new_headers = response
        else:
            body = self.body
            new_headers = {}


        if self.forcing_headers:
            headers = self.forcing_headers

        headers.update(new_headers)

        if self.adding_headers:
            headers.update(self.adding_headers)

        headers = self.normalize_headers(headers)

        status = headers.get('Status', self.status)
        string_list = [
            'HTTP/1.1 %d %s' % (status, STATUSES[status]),
        ]

        if 'Date' in headers:
            string_list.append('Date: %s' % headers.pop('Date'))

        if not self.forcing_headers:
            content_type = headers.pop('Content-Type',
                                       'text/plain; charset=utf-8')

            body_length = self.body_length
            if self.dynamic_response:
                body_length = len(body)
            content_length = headers.pop('Content-Length', body_length)

            string_list.append('Content-Type: %s' % content_type)
            if not self.streaming:
                string_list.append('Content-Length: %s' % content_length)

            string_list.append('Server: %s' % headers.pop('Server'))

        for k, v in headers.items():
            string_list.append(
                '%s: %s' % (k, utf8(v)),
            )

        fk.write("\n".join(string_list))
        fk.write('\n\r\n')

        if self.streaming:
            self.body, body = itertools.tee(body)
            for chunk in body:
                fk.write(utf8(chunk))
        else:
            fk.write(utf8(body))

        fk.seek(0)


def url_fix(s, charset='utf-8'):
    import urllib
    import urlparse
    """Sometimes you get an URL by a user that just isn't a real
    URL because it contains unsafe characters like ' ' and so on.  This
    function can fix some of the problems in a similar way browsers
    handle data entered by the user:

    >>> url_fix(u'http://de.wikipedia.org/wiki/Elf (Begriffsklärung)')
    'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29'

    :param charset: The target charset for the URL if the url was
                    given as unicode string.
    """
    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')
    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))


class URIInfo(Py3kObject):
    def __init__(self,
                 username='',
                 password='',
                 hostname='',
                 port=80,
                 path='/',
                 query='',
                 fragment='',
                 scheme='',
                 method=None,
                 last_request=None):

        self.username = username or ''
        self.password = password or ''
        self.hostname = hostname or ''

        if port:
            port = int(port)

        elif scheme == 'https':
            port = 443

        self.port = port or 80
        self.path = url_fix(path) or ''
        self.query = query or ''
        self.scheme = scheme or (self.port is 80 and "http" or "https")
        self.fragment = fragment or ''
        self.method = method
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
        orig_hostname = self.hostname
        orig_other = other.hostname

        self.hostname = None
        other.hostname = None
        result = text_type(self) == text_type(other)

        self.hostname = orig_hostname
        other.hostname = orig_other

        return result

    def full_url(self):
        credentials = ""
        if self.password:
            credentials = "{0}:{1}@".format(
                self.username, self.password)

        # query = ""
        # if self.query:
        #     query = "?{0}".format(self.query)

        return "{scheme}://{credentials}{host}{path}".format(
            scheme=self.scheme,
            credentials=credentials,
            host=self.hostname,
            path=self.path,
            #query=query
        )

    @classmethod
    def from_uri(cls, uri, entry):
        result = urlsplit(uri)
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

    def __init__(self, uri, method, entries):
        if type(uri).__name__ == 'SRE_Pattern':
            self.regex = uri
        else:
            self.info = URIInfo.from_uri(uri, entries)

        self.method = method
        self.entries = entries
        self.current_entry = 0

    def matches(self, info):
        if self.info:
            return self.info == info
        else:
            return self.regex.search(info.full_url())

    def __str__(self):
        wrap = 'URLMatcher({0} {1})'
        if self.info:
            return wrap.format(text_type(self.info), self.method)
        else:
            return wrap.format(self.regex.pattern, self.method)

    def get_next_entry(self):
        if self.current_entry >= len(self.entries):
            self.current_entry = -1

        if not self.entries:
            raise ValueError('I have no entries: %s' % self)

        entry = self.entries[self.current_entry]
        if self.current_entry != -1:
            self.current_entry += 1
        return entry

    def __hash__(self):
        return hash(text_type(self))

    def __eq__(self, other):
        return text_type(self) == text_type(other)


class HTTPretty(Py3kObject):
    u"""The URI registration class"""
    _entries = {}
    latest_requests = []
    GET = 'GET'
    PUT = 'PUT'
    POST = 'POST'
    DELETE = 'DELETE'
    HEAD = 'HEAD'
    PATCH = 'PATCH'
    METHODS = (GET, PUT, POST, DELETE, HEAD, PATCH)
    last_request = HTTPrettyRequestEmpty()

    @classmethod
    def reset(cls):
        cls._entries.clear()
        cls.latest_requests = []
        cls.last_request = HTTPrettyRequestEmpty()

    @classmethod
    def historify_request(cls, headers, body='', append=True):
        request = HTTPrettyRequest(headers, body)
        cls.last_request = request
        if append:
            cls.latest_requests.append(request)
        else:
            cls.latest_requests[-1] = request
        return request

    @classmethod
    def register_uri(cls, method, uri, body='HTTPretty :)',
                     adding_headers=None,
                     forcing_headers=None,
                     status=200,
                     responses=None, **headers):

        if isinstance(responses, list) and len(responses) > 0:
            entries_for_this_uri = responses
        else:
            headers['body'] = body
            headers['adding_headers'] = adding_headers
            headers['forcing_headers'] = forcing_headers
            headers['status'] = status

            entries_for_this_uri = [
                cls.Response(method=method, uri=uri, **headers),
            ]

        map(lambda e: setattr(e, 'uri', uri) or setattr(e, 'method', method),
            entries_for_this_uri)

        matcher = URIMatcher(uri, method, entries_for_this_uri)
        if matcher in cls._entries:
            del cls._entries[matcher]

        cls._entries[matcher] = entries_for_this_uri

    def __str__(self):
        return u'<HTTPretty with %d URI entries>' % len(self._entries)

    @classmethod
    def Response(cls, body, method=None, uri=None, adding_headers=None, forcing_headers=None,
                 status=200, streaming=False, **headers):

        headers['body'] = body
        headers['adding_headers'] = adding_headers
        headers['forcing_headers'] = forcing_headers
        headers['status'] = int(status)
        headers['streaming'] = streaming
        return Entry(method, uri, **headers)

    @classmethod
    def disable(cls):
        socket.socket = old_socket
        socket.SocketType = old_socket
        socket._socketobject = old_socket

        socket.create_connection = old_create_connection
        socket.gethostname = old_gethostname
        socket.gethostbyname = old_gethostbyname
        socket.getaddrinfo = old_getaddrinfo
        socket.inet_aton = old_gethostbyname

        socket.__dict__['socket'] = old_socket
        socket.__dict__['_socketobject'] = old_socket
        socket.__dict__['SocketType'] = old_socket

        socket.__dict__['create_connection'] = old_create_connection
        socket.__dict__['gethostname'] = old_gethostname
        socket.__dict__['gethostbyname'] = old_gethostbyname
        socket.__dict__['getaddrinfo'] = old_getaddrinfo
        socket.__dict__['inet_aton'] = old_gethostbyname

        if socks:
            socks.socksocket = old_socksocket
            socks.__dict__['socksocket'] = old_socksocket

        if ssl:
            ssl.wrap_socket = old_ssl_wrap_socket
            ssl.SSLSocket = old_sslsocket
            ssl.__dict__['wrap_socket'] = old_ssl_wrap_socket
            ssl.__dict__['SSLSocket'] = old_sslsocket

            if not PY3:
                ssl.sslwrap_simple = old_sslwrap_simple
                ssl.__dict__['sslwrap_simple'] = old_sslwrap_simple

    @classmethod
    def enable(cls):
        socket.socket = fakesock.socket
        socket._socketobject = fakesock.socket
        socket.SocketType = fakesock.socket

        socket.create_connection = create_fake_connection
        socket.gethostname = fake_gethostname
        socket.gethostbyname = fake_gethostbyname
        socket.getaddrinfo = fake_getaddrinfo
        socket.inet_aton = fake_gethostbyname

        socket.__dict__['socket'] = fakesock.socket
        socket.__dict__['_socketobject'] = fakesock.socket
        socket.__dict__['SocketType'] = fakesock.socket

        socket.__dict__['create_connection'] = create_fake_connection
        socket.__dict__['gethostname'] = fake_gethostname
        socket.__dict__['gethostbyname'] = fake_gethostbyname
        socket.__dict__['inet_aton'] = fake_gethostbyname
        socket.__dict__['getaddrinfo'] = fake_getaddrinfo

        if socks:
            socks.socksocket = fakesock.socket
            socks.__dict__['socksocket'] = fakesock.socket

        if ssl:
            ssl.wrap_socket = fake_wrap_socket
            ssl.SSLSocket = FakeSSLSocket

            ssl.__dict__['wrap_socket'] = fake_wrap_socket
            ssl.__dict__['SSLSocket'] = FakeSSLSocket

            if not PY3:
                ssl.sslwrap_simple = fake_wrap_socket
                ssl.__dict__['sslwrap_simple'] = fake_wrap_socket


def httprettified(test):
    "A decorator tests that use HTTPretty"
    @functools.wraps(test)
    def wrapper(*args, **kw):
        HTTPretty.reset()
        HTTPretty.enable()
        try:
            return test(*args, **kw)
        finally:
            HTTPretty.disable()
    return wrapper
