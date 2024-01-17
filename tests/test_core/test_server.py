from unittest.mock import Mock, patch

from moto.server import main


def test_wrong_arguments() -> None:
    try:
        main(["test1", "test2", "test3"])
        assert False, (
            "main() when called with the incorrect number of args"
            " should raise a system exit"
        )
    except SystemExit:
        pass


@patch("moto.server.run_simple")
def test_right_arguments(run_simple: Mock) -> None:  # type: ignore[misc]
    main(["-r"])
    func_call = run_simple.call_args[0]
    assert func_call[0] == "127.0.0.1"
    assert func_call[1] == 5000


@patch("moto.server.run_simple")
def test_port_argument(run_simple: Mock) -> None:  # type: ignore[misc]
    main(["--port", "8080"])
    func_call = run_simple.call_args[0]
    assert func_call[0] == "127.0.0.1"
    assert func_call[1] == 8080
