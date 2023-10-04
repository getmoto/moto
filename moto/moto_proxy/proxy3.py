# -*- coding: utf-8 -*-
import socket
import ssl
import re
from http.server import BaseHTTPRequestHandler
from subprocess import check_output, CalledProcessError
from threading import Lock
from typing import Any, Dict

from botocore.awsrequest import AWSPreparedRequest
from moto.backends import get_backend
from moto.backend_index import backend_url_patterns
from moto.core import BackendDict, DEFAULT_ACCOUNT_ID
from moto.core.exceptions import RESTError
from . import debug, error, info, with_color
from .utils import get_body_from_form_data
from .certificate_creator import CertificateCreator

# Adapted from https://github.com/xxlv/proxy3


class MotoRequestHandler:
    def __init__(self, port: int):
        self.lock = Lock()
        self.port = port

    def get_backend_for_host(self, host: str) -> Any:
        if host == f"http://localhost:{self.port}":
            return "moto_api"

        for backend, pattern in backend_url_patterns:
            if pattern.match(host):
                return backend

    def get_handler_for_host(self, host: str, path: str) -> Any:
        # We do not match against URL parameters
        path = path.split("?")[0]
        backend_name = self.get_backend_for_host(host)
        backend_dict = get_backend(backend_name)

        # Get an instance of this backend.
        # We'll only use this backend to resolve the URL's, so the exact region/account_id is irrelevant
        if isinstance(backend_dict, BackendDict):
            if "us-east-1" in backend_dict[DEFAULT_ACCOUNT_ID]:
                backend = backend_dict[DEFAULT_ACCOUNT_ID]["us-east-1"]
            else:
                backend = backend_dict[DEFAULT_ACCOUNT_ID]["global"]
        else:
            backend = backend_dict["global"]

        for url_path, handler in backend.url_paths.items():
            if re.match(url_path, path):
                return handler

        return None

    def parse_request(
        self,
        method: str,
        host: str,
        path: str,
        headers: Any,
        body: bytes,
        form_data: Dict[str, Any],
    ) -> Any:
        handler = self.get_handler_for_host(host=host, path=path)
        full_url = host + path
        request = AWSPreparedRequest(
            method, full_url, headers, body, stream_output=False
        )
        request.form_data = form_data
        return handler(request, full_url, headers)


class ProxyRequestHandler(BaseHTTPRequestHandler):
    timeout = 5

    def __init__(self, *args: Any, **kwargs: Any):
        sock = [a for a in args if isinstance(a, socket.socket)][0]
        _, port = sock.getsockname()
        self.protocol_version = "HTTP/1.1"
        self.moto_request_handler = MotoRequestHandler(port)
        self.cert_creator = CertificateCreator()
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    @staticmethod
    def validate() -> None:
        debug("Starting initial validation...")
        CertificateCreator().validate()
        # Validate the openssl command is available
        try:
            debug("Verifying SSL version...")
            svn_output = check_output(["openssl", "version"])
            debug(svn_output)
        except CalledProcessError as e:
            info(e.output)
            raise

    def do_CONNECT(self) -> None:
        certpath = self.cert_creator.create(self.path)

        self.wfile.write(
            f"{self.protocol_version} 200 Connection Established\r\n".encode("utf-8")
        )
        self.send_header("k", "v")
        self.end_headers()

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(
            keyfile=CertificateCreator.certkey,
            certfile=certpath,
        )
        ssl_context.check_hostname = False
        self.connection = ssl_context.wrap_socket(
            self.connection,
            server_side=True,
        )
        self.rfile = self.connection.makefile("rb", self.rbufsize)  # type: ignore
        self.wfile = self.connection.makefile("wb", self.wbufsize)  # type: ignore

        conntype = self.headers.get("Proxy-Connection", "")
        if self.protocol_version == "HTTP/1.1" and conntype.lower() != "close":
            self.close_connection = 0  # type: ignore
        else:
            self.close_connection = 1  # type: ignore

    def do_GET(self) -> None:
        req = self
        req_body = b""
        if "Content-Length" in req.headers:
            content_length = int(req.headers["Content-Length"])
            req_body = self.rfile.read(content_length)
        elif "chunked" in self.headers.get("Transfer-Encoding", ""):
            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Transfer-Encoding
            req_body = self.read_chunked_body(self.rfile)
        if self.headers.get("Content-Type", "").startswith("multipart/form-data"):
            boundary = self.headers["Content-Type"].split("boundary=")[-1]
            req_body, form_data = get_body_from_form_data(req_body, boundary)  # type: ignore
            for key, val in form_data.items():
                self.headers[key] = [val]
        else:
            form_data = {}

        req_body = self.decode_request_body(req.headers, req_body)  # type: ignore
        if isinstance(self.connection, ssl.SSLSocket):
            host = "https://" + req.headers["Host"]
        else:
            host = "http://" + req.headers["Host"]
        path = req.path

        try:
            info(f"{with_color(33, req.command.upper())} {host}{path}")  # noqa
            if req_body is not None:
                debug("\tbody\t" + with_color(31, text=req_body))
            debug(f"\theaders\t{with_color(31, text=dict(req.headers))}")
            response = self.moto_request_handler.parse_request(
                method=req.command,
                host=host,
                path=path,
                headers=req.headers,
                body=req_body,
                form_data=form_data,
            )
            debug("\t=====RESPONSE========")
            debug("\t" + with_color(color=33, text=response))
            debug("\n")

            if isinstance(response, tuple):
                res_status, res_headers, res_body = response
            else:
                res_status, res_headers, res_body = (200, {}, response)

        except RESTError as e:
            if isinstance(e.get_headers(), list):
                res_headers = dict(e.get_headers())
            else:
                res_headers = e.get_headers()
            res_status = e.code
            res_body = e.get_body()

        except Exception as e:
            error(e)
            self.send_error(502)
            return

        res_reason = "OK"
        if isinstance(res_body, str):
            res_body = res_body.encode("utf-8")

        if "content-length" not in res_headers and res_body:
            res_headers["Content-Length"] = str(len(res_body))

        self.wfile.write(
            f"{self.protocol_version} {res_status} {res_reason}\r\n".encode("utf-8")
        )
        if res_headers:
            for k, v in res_headers.items():
                if isinstance(v, bytes):
                    self.send_header(k, v.decode("utf-8"))
                else:
                    self.send_header(k, v)
            self.end_headers()
        if res_body:
            self.wfile.write(res_body)
        self.close_connection = True

    def read_chunked_body(self, reader: Any) -> bytes:
        chunked_body = b""
        while True:
            line = reader.readline().strip()
            chunk_length = int(line, 16)
            if chunk_length != 0:
                chunked_body += reader.read(chunk_length)

            # Each chunk is followed by an additional empty newline
            reader.readline()

            # a chunk size of 0 is an end indication
            if chunk_length == 0:
                # AWS does send additional (checksum-)headers, but we can ignore them
                break
        return chunked_body

    def decode_request_body(self, headers: Dict[str, str], body: Any) -> Any:
        if body is None:
            return body
        if headers.get("Content-Type", "") in [
            "application/x-amz-json-1.1",
            "application/x-www-form-urlencoded; charset=utf-8",
        ]:
            return body.decode("utf-8")
        return body

    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT = do_GET
    do_PATCH = do_GET
    do_DELETE = do_GET
    do_OPTIONS = do_GET
