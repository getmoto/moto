.. _configuration:

======================
Configuration Options
======================

Moto has a variety of ways to configure the mock behaviour.

If you are using the decorators, some options are configurable within the decorator:

.. sourcecode:: python

    @mock_aws(config={
        "batch": {"use_docker": True},
        "lambda": {"use_docker": True},
        "core": {
            "mock_credentials": True,
            "passthrough": {
                "urls": ["s3.amazonaws.com/bucket*"],
                "services": ["dynamodb"]
            },
            "reset_boto3_session": True,
        }
    })


Dockerless Services
--------------------

By default, Batch and AWSLambda will spin up a Docker image to execute the provided scripts and functions.

If you configure `use_docker: False` for either of these services, the scripts and functions will not be executed, and Moto will assume a successful invocation.

Passthrough Requests
--------------------

Configure `mock_credentials: False` and `passthrough` if you want to only mock some services, but allow other requests to connect to AWS.

You can either passthrough all requests to a specific service, or all URL's that match a specific pattern.

Reset Boto Session
------------------

When creating boto3-client for the first time, `boto3` will create a default session that caches all kinds of things - including credentials. Subsequent boto3-clients will reuse that `Session`.

If the first test in your test suite is mocked, the default `Session` created in that test will have fake credentials, as supplied by Moto. But if the next test is not mocked and should reach out to AWS, it would do so with the mocked credentials from our cached `Session`.

That is why Moto resets the `boto3-Session`, to make sure that it is recreated with the correct credentials (either fake or mocked) everytime. It does come at a cost though, as instantiating a new boto3-Session is an expensive operation.

If all of your tests use Moto, and you never want to reach out to AWS, you can choose to _not_ reset the `boto3-session`. New boto3-clients that are created will reuse the `boto3-Session` (with fake credentials), making Moto much more performant.

.. toctree::
  :maxdepth: 1

  environment_variables
  recorder/index
  state_transition/index
  state_transition/models

