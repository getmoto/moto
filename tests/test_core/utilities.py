from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Thread
from typing import Optional, Tuple


class SimpleServer:
    def __init__(self, handler: type[BaseHTTPRequestHandler]) -> None:
        self._port = 0
        self._handler = handler

        self._thread: Optional[Thread] = None
        self._ip_address = "0.0.0.0"
        self._server: Optional[HTTPServer] = None
        self._server_ready_event = Event()

    def _server_entry(self) -> None:
        self._server = HTTPServer(("0.0.0.0", 0), self._handler)
        self._server_ready_event.set()
        self._server.serve_forever()

    def start(self) -> None:
        self._thread = Thread(target=self._server_entry, daemon=True)
        self._thread.start()
        self._server_ready_event.wait()

    def get_host_and_port(self) -> Tuple[str, int]:
        assert self._server
        host, port = self._server.server_address[:2]
        return str(host), port

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
        if self._thread:
            self._thread.join()
