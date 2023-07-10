from unittest.mock import patch
from moto.server import main, create_backend_app, DomainDispatcherApplication


def test_wrong_arguments():
    try:
        main(["name", "test1", "test2", "test3"])
        assert False, (
            "main() when called with the incorrect number of args"
            " should raise a system exit"
        )
    except SystemExit:
        pass


@patch("moto.server.run_simple")
def test_right_arguments(run_simple):
    main(["s3"])
    func_call = run_simple.call_args[0]
    assert func_call[0] == "127.0.0.1"
    assert func_call[1] == 5000


@patch("moto.server.run_simple")
def test_port_argument(run_simple):
    main(["s3", "--port", "8080"])
    func_call = run_simple.call_args[0]
    assert func_call[0] == "127.0.0.1"
    assert func_call[1] == 8080


def test_domain_dispatched():
    dispatcher = DomainDispatcherApplication(create_backend_app)
    backend_app = dispatcher.get_application(
        {"HTTP_HOST": "email.us-east1.amazonaws.com"}
    )
    keys = list(backend_app.view_functions.keys())
    assert keys[0] == "EmailResponse.dispatch"


def test_domain_dispatched_with_service():
    # If we pass a particular service, always return that.
    dispatcher = DomainDispatcherApplication(create_backend_app, service="s3")
    backend_app = dispatcher.get_application({"HTTP_HOST": "s3.us-east1.amazonaws.com"})
    keys = set(backend_app.view_functions.keys())
    assert "S3Response.key_response" in keys
