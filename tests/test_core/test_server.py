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


@patch('moto.server.app.run')
def test_right_arguments(app_run):
    main(["s3"])
    app_run.assert_called_once_with(host='0.0.0.0', port=5000)


@patch('moto.server.app.run')
def test_port_argument(app_run):
    main(["s3", "--port", "8080"])
    app_run.assert_called_once_with(host='0.0.0.0', port=8080)
