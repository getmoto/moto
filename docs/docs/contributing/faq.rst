.. _contributing developer faq:

.. role:: bash(code)
   :language: bash

.. role:: python(code)
   :language: python

=============================
FAQ for Developers
=============================

When running the linter...
#############################

Why does ruff give different results?
****************************************
Different versions of ruff produce different results.
The CI system uses the version set in `requirements-dev.txt`.
To ensure that our CI passes, please format the code using the same version.

When running a test...
#########################

Why does it take ages to run a single test?
**********************************************
There are a few reasons why this could happen.
If the test uses Docker, it could take a while to:

 - Download the appropriate Docker image
 - Run the image
 - Wait for the logs to appear


Why are my tests failing in ServerMode?
******************************************
 - Make sure that the correct url paths are present in `urls.py`
 - Make sure that you've run :bash:`scripts/update_backend_index.py` afterwards, to let MotoServer know the urls have changed.



What ...
#################

Does ServerMode refer to?
******************************
ServerMode refers to Moto running as a stand-alone server. This can be useful to:
 - Test non-Python SDK's
 - Have a semi-permanent, local AWS-like server running that multiple applications can talk to

Types of tests are there?
***********************************
There are three types of tests:

 #. decorator tests
 #. ServerMode tests
 #. server tests (located in test_server.py)

The decorator tests refer to the normal unit tests that are run against an in-memory Moto instance.

The ServerMode tests refer to the same set of tests - but run against an external MotoServer instance.
When running tests in ServerMode, each boto3-client and boto3-resource are intercepted, and enriched with the :python:`endpoint_url="http://localhost:5000"` argument. This allows us to run the same test twice, and verify that Moto behaves the same when using decorators, and in ServerMode.

The last 'server' tests are low-level tests that can be used to verify that Moto behaves exactly like the AWS HTTP API.
Each test will spin up the MotoServer in memory, and run HTTP requests directly against that server.
This allows the developer to test things like HTTP headers, the exact response/request format, etc.

Alternatives are there?
********************************
The best alternative would be `LocalStack <https://localstack.cloud//>`_.

LocalStack is Moto's bigger brother with more advanced features, such as EC2 VM's that you can SSH into and Dockerized RDS-installations that you can connect to.


Why am I getting errors...
#############################


That my new module could not be found when using the scaffold-script?
************************************************************************

.. sourcecode:: bash

  File "scripts/scaffold.py", line 499, in insert_codes
    insert_code_to_class(responses_path, BaseResponse, func_in_responses)
  File "scripts/scaffold.py", line 424, in insert_code_to_class
    mod = importlib.import_module(mod_path)
  File "/usr/lib/python3.8/importlib/__init__.py", line 127, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)

  ModuleNotFoundError: No module named 'moto.kafka'

This will happen if you've ran :bash:`pip install .` prior to running `scripts/scaffold.py`.

Instead, install Moto as an editable module instead:

.. sourcecode:: bash

  pip uninstall moto
  pip install -e .


Related to Docker when running tests?
******************************************
AWSLambda and Batch services use Docker to execute the code provided to the system, which means that Docker needs to be installed on your system in order for these tests to run.

Installing Moto using ZSH on MacOS?
******************************************
When using :bash:`pip install` on ZSH, you might see the following: :bash:`zsh: no matches found`. This is because ZSH requires the full module to be in quotes.

.. sourcecode:: bash

    pip install "moto[ssm]"


