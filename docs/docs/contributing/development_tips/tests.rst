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
  # These assertions use the 'sure' library, but any assertion style is accepted
  err["Code"].should.equal(..)
  err["Message"].should.equal(..)

This is the best way to ensure that exceptions are dealt with correctly by Moto.


ServerMode tests
^^^^^^^^^^^^^^^^^^^^

Our CI runs all tests twice - one normal run, and one run in ServerMode. In ServerMode, Moto is started as a stand-alone Flask server, and all tests are run against this Flask-instance.

To verify whether your tests pass in ServerMode, you can run the following commands:

.. sourcecode:: bash

  moto_server
  TEST_SERVER_MODE=true pytest -sv tests/test_service/..


Parallel tests
^^^^^^^^^^^^^^^^^^^^^

To speed up our CI, the ServerMode tests for the `awslambda`, `batch`, `ec2` and `sqs` services will run in parallel.
This means the following:

 - Make sure you use unique names for functions/queues/etc
 - Calls to `describe_reservations()`/`list_queues()`/etc might return resources from other tests

