from mock import patch
import sure  # noqa

from moto.server import main


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
    func_call[0].should.equal("0.0.0.0")
    func_call[1].should.equal(5000)


@patch('moto.server.run_simple')
def test_port_argument(run_simple):
    main(["s3", "--port", "8080"])
    func_call = run_simple.call_args[0]
    func_call[0].should.equal("0.0.0.0")
    func_call[1].should.equal(8080)
