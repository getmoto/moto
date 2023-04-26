import argparse
import os
import signal
import sys
import warnings
from typing import Any, List, Optional

from werkzeug.serving import run_simple

from moto.moto_server.werkzeug_app import (
    DomainDispatcherApplication,
    create_backend_app,
)
from moto.moto_server.threaded_moto_server import (  # noqa # pylint: disable=unused-import
    ThreadedMotoServer,
)


def signal_handler(signum: Any, frame: Any) -> None:  # pylint: disable=unused-argument
    sys.exit(0)


def main(argv: Optional[List[str]] = None) -> None:
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser()

    # Keep this for backwards compat
    parser.add_argument(
        "service",
        type=str,
        nargs="?",  # http://stackoverflow.com/a/4480202/731592
        default=os.environ.get("MOTO_SERVICE"),
    )
    parser.add_argument(
        "-H", "--host", type=str, help="Which host to bind", default="127.0.0.1"
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        help="Port number to use for connection",
        default=int(os.environ.get("MOTO_PORT", 5000)),
    )
    parser.add_argument(
        "-r",
        "--reload",
        action="store_true",
        help="Reload server on a file change",
        default=False,
    )
    parser.add_argument(
        "-s",
        "--ssl",
        action="store_true",
        help="Enable SSL encrypted connection with auto-generated certificate (use https://... URL)",
        default=False,
    )
    parser.add_argument(
        "-c", "--ssl-cert", type=str, help="Path to SSL certificate", default=None
    )
    parser.add_argument(
        "-k", "--ssl-key", type=str, help="Path to SSL private key", default=None
    )

    args = parser.parse_args(argv)

    if "MOTO_PORT" not in os.environ:
        os.environ["MOTO_PORT"] = f"{args.port}"

    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    except Exception:
        pass  # ignore "ValueError: signal only works in main thread"

    if args.service:
        warnings.warn(
            f"The service-argument ({args.service}) is considered deprecated, and will be deprecated in a future release. Please let us know if you have any questions: https://github.com/getmoto/moto/issues"
        )

    # Wrap the main application
    main_app = DomainDispatcherApplication(create_backend_app, service=args.service)
    main_app.debug = True  # type: ignore

    ssl_context: Any = None
    if args.ssl_key and args.ssl_cert:
        ssl_context = (args.ssl_cert, args.ssl_key)
    elif args.ssl:
        ssl_context = "adhoc"

    run_simple(
        args.host,
        args.port,
        main_app,
        threaded=True,
        use_reloader=args.reload,
        ssl_context=ssl_context,
    )


if __name__ == "__main__":
    main()
