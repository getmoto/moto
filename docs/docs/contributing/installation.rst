.. _contributing installation:

=============================
Development Installation
=============================

This is a guide how to install Moto for contributors.

The following software is assumed to be present:

 - Python 3.x
 - Docker

It is recommended to work from some kind of virtual environment, i.e. `virtualenv`, to prevent cross-contamination with other projects.
From within such a virtualenv, run the following command to install all required dependencies:

.. code-block:: bash

  make init

With all dependencies installed, run the following command to run all the tests and verify your environment is ready:

.. code-block:: bash

  make test

Note that this may take awhile - there are many services, and each service will have a boatload of tests.

To verify all tests pass for a specific service, for example for `s3`, run these commands manually:

.. code-block:: bash

  flake8 moto/s3
  black --check moto/s3 tests/test_s3
  pylint tests/test_s3
  pytest -sv tests/test_s3

If black fails, you can run the following command to automatically format the offending files:

.. code-block:: bash

  make format

If any of these steps fail, please see our :ref:`contributing faq` or open an issue on Github.
