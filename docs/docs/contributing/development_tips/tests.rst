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


Terraform tests
^^^^^^^^^^^^^^^^^^^^^^

To verify that Moto behaves correctly, we run a subset of Terraform's tests against the MotoServer to ensure it behaves the same as AWS does.

These tests will be run automatically for every PR, so you should not need to make any changes here.

A list of which tests currently pass against Moto can be found in `tests/terraformtests/terraform-tests.success.txt`.

Use the following commands to see the full list of available tests:

.. sourcecode:: bash

    cd tests/terraformtests/terraform-provider-aws
    # Choose the correct service in the next command - this example will list all tests for the ELB-service
    go test ./internal/service/elb/ -v -list TestAcc

In order to check whether MotoServer behaves correctly against a specific test, you can use the following commands:

.. sourcecode:: bash

    # Ensure you are back in the root-directory
    # Start the MotoServer on port 4566
    moto_server -p 4566
    # Run the new tests
    make terraformtests SERVICE_NAME=elb TEST_NAMES=NewTestName
