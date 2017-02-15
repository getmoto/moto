from __future__ import unicode_literals

import os.path

from mock import patch
import six
import sure  # noqa

from moto.core.publisher import default_publisher
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
    backend_app = dispatcher.get_application("email.us-east1.amazonaws.com")
    keys = list(backend_app.view_functions.keys())
    keys[0].should.equal('EmailResponse.dispatch')


def test_domain_without_matches():
    dispatcher = DomainDispatcherApplication(create_backend_app)
    dispatcher.get_application.when.called_with("not-matching-anything.com").should.throw(RuntimeError)


def test_xip_io_domain_dispatched():
    dispatcher = DomainDispatcherApplication(create_backend_app)
    backend_app = dispatcher.get_application("rds2.127.0.0.1.xip.io")
    keys = list(backend_app.view_functions.keys())
    keys[0].should.equal('RDS2Response.dispatch')


def test_domain_dispatched_with_service():
    # If we pass a particular service, always return that.
    dispatcher = DomainDispatcherApplication(create_backend_app, service="s3")
    backend_app = dispatcher.get_application("s3.us-east1.amazonaws.com")
    keys = set(backend_app.view_functions.keys())
    keys.should.contain('ResponseObject.key_response')


def start(publisher):
    def dummy_observer(event_type, data):
        data['answer'] = 42
        data['event_type'] = event_type
        data['module_name'] = __name__
    event_type = 123
    publisher.subscribe(dummy_observer, event_type)


@patch('moto.server.run_simple')
def test_extension_script_gets_loaded(run_simple):
    """Setting the 'script' switch results in a python file being loaded
    automatically and any 'start' function invoked with the publisher instance"""
    default_publisher.reset()
    script_file = os.path.join(os.path.dirname(__file__), '..', 'helpers.py')
    main(["--script", script_file, "s3"])

    data = {}
    event_type = 123
    default_publisher.notify(event_type, data)
    data['answer'].should.equal(42)
    data['event_type'].should.equal(event_type)
    data['module_name'].should.equal('moto.extension')

    func_call = run_simple.call_args[0]
    func_call[0].should.equal("127.0.0.1")
    func_call[1].should.equal(5000)


def test_loading_non_existent_extension_script():
    args = ["--script", '/does/not/exists.py', "s3"]
    error = FileNotFoundError if six.PY3 else IOError
    main.when.called_with(args).should.throw(error)
