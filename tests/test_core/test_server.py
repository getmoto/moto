from __future__ import unicode_literals
from mock import patch
import sure  # noqa

from moto.server import main, create_backend_app, DomainDispatcherApplication


def test_wrong_arguments():
    try:
        main(["name", "test1", "test2", "test3"])
        assert False, ("main() when called with the incorrect number of args"
                       " should raise a system exit")
    except SystemExit:
        pass


@patch('moto.server.run_simple')
def test_right_arguments(run_simple):
    main(["s3"])
    func_call = run_simple.call_args[0]
    func_call[0].should.equal("127.0.0.1")
    func_call[1].should.equal(5000)


@patch('moto.server.run_simple')
def test_port_argument(run_simple):
    main(["s3", "--port", "8080"])
    func_call = run_simple.call_args[0]
    func_call[0].should.equal("127.0.0.1")
    func_call[1].should.equal(8080)


def test_domain_dispatched():
    dispatcher = DomainDispatcherApplication(create_backend_app)
    backend_app = dispatcher.get_application(
        {"HTTP_HOST": "email.us-east1.amazonaws.com"})
    keys = list(backend_app.view_functions.keys())
    keys[0].should.equal('EmailResponse.dispatch')


def test_domain_dispatched_with_service():
    # If we pass a particular service, always return that.
    dispatcher = DomainDispatcherApplication(create_backend_app, service="s3")
    backend_app = dispatcher.get_application(
        {"HTTP_HOST": "s3.us-east1.amazonaws.com"})
    keys = set(backend_app.view_functions.keys())
    keys.should.contain('ResponseObject.key_response')
