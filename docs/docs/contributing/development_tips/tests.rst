.. _contributing tests:


****************
Writing tests
****************

One test should only verify a single feature/method. I.e., one test for `create_resource()`, another for `update_resource()`, etc.

Negative tests
^^^^^^^^^^^^^^^^^

When writing negative tests, try to use the following format:

.. sourcecode:: python

  with pytest.raises(botocore.exceptions.ClientError) as exc:
      client.failing_call(..)
  err = exc.value.response["Error"]
  # Use the pytest assert method, see https://docs.pytest.org/en/stable/how-to/assert.html#
  assert err["Code"] == ..
  assert err["Message"] == ..

This is the best way to ensure that exceptions are dealt with correctly by Moto.


ServerMode tests
^^^^^^^^^^^^^^^^^^^^

Our CI runs all tests twice - one normal run, and one run in ServerMode. In ServerMode, Moto is started as a stand-alone Flask server, and all tests are run against this Flask-instance.

To verify whether your tests pass in ServerMode, first follow the
:ref:`contributing installation` guide. From the repository root, start the
server in one terminal with the development virtual environment activated:

.. sourcecode:: bash

  moto_server -H 127.0.0.1 -p 5000

Keep the server running. In a second terminal, activate the same virtual
environment and run the tests from the repository root:

.. sourcecode:: bash

  export TEST_SERVER_MODE=true
  export TEST_SERVER_MODE_ENDPOINT=http://127.0.0.1:5000
  pytest -sv tests/test_sts/test_sts.py -k test_get_caller_identity_with_default_credentials

Replace the STS test path and filter with the tests for your service.
``TEST_SERVER_MODE=true`` makes ``@mock_aws`` route boto3 clients and resources
to the local server instead of using the in-memory backend.
The explicit endpoint matches the address the server is bound to.

If port 5000 is already in use, start the server with a different port, for
example ``moto_server -H 127.0.0.1 -p 5001``, and set the endpoint in the test
terminal as well:

.. sourcecode:: bash

  export TEST_SERVER_MODE_ENDPOINT=http://127.0.0.1:5001
  pytest -sv tests/test_sts/test_sts.py -k test_get_caller_identity_with_default_credentials

Stop the server with Ctrl+C when you have finished testing. Before returning
to in-memory tests in the same terminal, unset the server-mode variables:

.. sourcecode:: bash

  unset TEST_SERVER_MODE TEST_SERVER_MODE_ENDPOINT


Parallel tests
^^^^^^^^^^^^^^^^^^^^^

To speed up our CI, the tests for the `awslambda`, `batch`, `ec2` and `sqs` services will run in parallel.
This means the following:

 - Make sure you use unique names for functions/queues/etc
 - Calls to `describe_reservations()`/`list_queues()`/etc might return resources from other tests
