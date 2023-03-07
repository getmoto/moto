.. _contributing installation:

=============================
Development Installation
=============================

This is a guide how to install Moto for contributors.

The following software is assumed to be present:

 - Python 3.x
 - Docker
 - Git


Checking out the code
======================
Contributing to Moto involves forking the project.
GitHub has a handy guide explaining how to do this: https://docs.github.com/en/get-started/quickstart/contributing-to-projects

Installing Moto locally
========================

It is recommended to work from some kind of virtual environment, i.e. `virtualenv`, to prevent cross-contamination with other projects.
From within such a virtualenv, run the following command to install all required dependencies:

.. code-block:: bash

  make init

With all dependencies installed, run the following command to run all the tests and verify your environment is ready:

.. code-block:: bash

  make test

Note that this may take awhile - there are many services, and each service will have a boatload of tests.

To verify all tests pass for a specific service, for example for `s3`, run the following command:

.. code-block:: bash

  make test SERVICE_NAME=s3

If black fails, you can run the following command to automatically format the offending files:

.. code-block:: bash

  make format

If any of these steps fail, please see our :ref:`contributing faq` or open an issue on Github.
