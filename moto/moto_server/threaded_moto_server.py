import time
from threading import Thread
from typing import Optional
from werkzeug.serving import make_server, BaseWSGIServer

from .werkzeug_app import DomainDispatcherApplication, create_backend_app


class ThreadedMotoServer:
    def __init__(
        self, ip_address: str = "0.0.0.0", port: int = 5000, verbose: bool = True
    ):

        self._port = port

        self._thread: Optional[Thread] = None
        self._ip_address = ip_address
        self._server: Optional[BaseWSGIServer] = None
        self._server_ready = False
        self._verbose = verbose

    def _server_entry(self) -> None:
        app = DomainDispatcherApplication(create_backend_app)

        self._server = make_server(self._ip_address, self._port, app, True)
        self._server_ready = True
        self._server.serve_forever()

    def start(self) -> None:
        if self._verbose:
            print(  # noqa
                f"Starting a new Thread with MotoServer running on {self._ip_address}:{self._port}..."
            )
        self._thread = Thread(target=self._server_entry, daemon=True)
        self._thread.start()
        while not self._server_ready:
            time.sleep(0.1)

    def stop(self) -> None:
        self._server_ready = False
        if self._server:
            self._server.shutdown()

        self._thread.join()  # type: ignore[union-attr]
