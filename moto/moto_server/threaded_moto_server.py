from threading import Event, Thread
from typing import Optional

from werkzeug.serving import BaseWSGIServer, WSGIRequestHandler, make_server

from .werkzeug_app import DomainDispatcherApplication, create_backend_app


class _MotoRequestHandler(WSGIRequestHandler):
    def handle_expect_100(self) -> bool:
        """Suppress the duplicate ``100 Continue`` from BaseHTTPRequestHandler.

        Werkzeug's ``run_wsgi()`` already sends its own ``100 Continue``
        when it sees the ``Expect`` header.  The default
        ``BaseHTTPRequestHandler.parse_request()`` sends a second one,
        resulting in two ``100 Continue`` responses on the wire.

        Returning ``True`` without writing anything prevents the duplicate
        while letting werkzeug send exactly one ``100 Continue`` later.
        """
        return True


class ThreadedMotoServer:
    def __init__(
        self, ip_address: str = "0.0.0.0", port: int = 5000, verbose: bool = True
    ):
        self._port = port

        self._thread: Optional[Thread] = None
        self._ip_address = ip_address
        self._server: Optional[BaseWSGIServer] = None
        self._server_ready_event = Event()
        self._verbose = verbose

    def _server_entry(self) -> None:
        app = DomainDispatcherApplication(create_backend_app)

        self._server = make_server(
            self._ip_address,
            self._port,
            app,
            threaded=True,
            request_handler=_MotoRequestHandler,
        )
        self._server_ready_event.set()
        self._server.serve_forever()

    def start(self) -> None:
        if self._verbose:
            print(  # noqa
                f"Starting a new Thread with MotoServer running on {self._ip_address}:{self._port}..."
            )
        self._thread = Thread(target=self._server_entry, daemon=True)
        self._thread.start()
        self._server_ready_event.wait()

    def get_host_and_port(self) -> tuple[str, int]:
        assert self._server is not None, "Make sure to call start() first"
        host, port = self._server.server_address[:2]
        return (str(host), port)

    def stop(self) -> None:
        self._server_ready_event.clear()
        if self._server:
            self._server.shutdown()

        self._thread.join()  # type: ignore[union-attr]
