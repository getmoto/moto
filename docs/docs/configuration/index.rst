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
            }
        }
    })

By default, Batch and AWSLambda will spin up a Docker image to execute the provided scripts and functions.

If you configure `use_docker: False` for either of these services, the scripts and functions will not be executed, and Moto will assume a successful invocation.

Configure `mock_credentials: False` and `passthrough` if you want to only mock some services, but allow other requests to connect to AWS.

You can either passthrough all requests to a specific service, or all URL's that match a specific pattern.


.. toctree::
  :maxdepth: 1

  environment_variables
  recorder/index
  state_transition/index
  state_transition/models

