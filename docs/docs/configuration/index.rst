.. _configuration:

======================
Configuration Options
======================

Moto has a variety of ways to configure the mock behaviour.

If you are using the decorators, some options are configurable within the decorator:

.. sourcecode:: python

    @mock_aws(config={
        "batch": {"use_docker": True},
        "lambda": {"use_docker": True}
    })


.. toctree::
  :maxdepth: 1

  environment_variables
  recorder/index
  state_transition/index
  state_transition/models

